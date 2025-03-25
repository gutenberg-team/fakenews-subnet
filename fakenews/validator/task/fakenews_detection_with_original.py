import asyncio
import traceback
from random import choices, shuffle
from typing import TYPE_CHECKING, ClassVar

import bittensor as bt
from pydantic import BaseModel, PrivateAttr

from fakenews.exceptions import OpenAIInternalError
from fakenews.protocol import ArticleSynapse
from fakenews.schemas import SaveLLMRewrittenArticleModel
from fakenews.services.news_api import NewsAPIClient
from fakenews.services.openai.client import OpenAIClient
from fakenews.services.openai.prompts import (
    StrongFakeV1Prompt,
    StrongOriginalV5Prompt,
    ValidatorPrompt,
    WeakFakeV4Prompt,
    WeakOriginalV1Prompt,
)

from . import ValidatorTask

if TYPE_CHECKING:
    from substrateinterface import Keypair


class OriginalArticleMetadata(BaseModel):
    body: str
    _id: int = PrivateAttr()
    url: str
    categories: list[str]

    def __init__(self, **data):
        super().__init__(**data)
        self._id = data.get("_id")


class GeneratedArticleMetadata(BaseModel):
    body: str
    label: float
    model_version: str
    prompt_version: str


class Metadata(BaseModel):
    """
    Metadata for the task.
    """

    generated_articles_metadata: list[GeneratedArticleMetadata]
    original_article_metadata: OriginalArticleMetadata


class FakenewsDetectionWithOriginal(ValidatorTask):
    """
    Task for generating paraphrased article and fakenews article using LLMs.
    Original article is attached to the synapse.
    """

    __slots__ = ["__metadata", "_news_api_client", "_openai_client"]

    TASK_NAME: str = "FakenewsDetectionWithOriginal"
    REWARD_WEIGHT: float = 0.5
    FORWARD_PROBABILTY: float = 0.5
    TIMEOUT: int = 15
    FAKE_SAMPLING_PROBABILITIES: ClassVar[list[tuple[ValidatorPrompt, float]]] = [
        (WeakFakeV4Prompt, 0.6),
        (StrongFakeV1Prompt, 0.4),
    ]
    PARAPHRASE_SAMPLING_PROBABILITIES: ClassVar[list[tuple[ValidatorPrompt, float]]] = [
        (WeakOriginalV1Prompt, 0.4),
        (StrongOriginalV5Prompt, 0.6),
    ]
    PROMPT_SAMPLING_PROBABILITIES: ClassVar[list[tuple[ValidatorPrompt, float]]] = [
        (WeakFakeV4Prompt, 0.25),
        (StrongFakeV1Prompt, 0.25),
        (StrongOriginalV5Prompt, 0.25),
        (WeakOriginalV1Prompt, 0.25),
    ]
    ALLOW_PROMPTS_REPEAT: bool = True
    PROMPTS_SAMPLE_SIZE: int = 2

    def __init__(self, openai_api_key: str, keypair: "Keypair"):
        """
        Initialize the task object with neccessary dependencies.

        Args:
            openai_api_key (str): OpenAI API key.
            keypair (Keypair): Hotkey keypair.
        """
        self._openai_client = OpenAIClient(api_key=openai_api_key)
        self._news_api_client = NewsAPIClient(keypair=keypair)

    async def prepare_synapse(self) -> ArticleSynapse | None:
        """
        Creates an ArticleSynapse.
        1. Fetches an real news article from the specific news API.
        2. Generates a fake article and a paraphrased article using LLMs.
        3. Randomly shuffles the articles and returns the synapse.

        Returns:
            ArticleSynapse: An instance of ArticleSynapse.
        """
        self.__metadata = None

        original_article = await self._news_api_client.fetch_article()

        article_text = original_article.body
        log_article = article_text.replace("\n", " ")
        bt.logging.debug(f"Original article title: {original_article.title}")

        prompts = [p(article_text) for p in self._select_sampled_prompts()]

        try:
            results = await asyncio.gather(*(self._openai_client.get_prompt_completions_async(p) for p in prompts))
        except BaseException as e:
            bt.logging.error("Failed to fetch articles from LLM: %s", e)
            traceback.print_exc()
            raise e

        generated_articles_metadata = []
        for prompt, result in zip(prompts, results):
            prompt: ValidatorPrompt
            label = prompt.LABEL_PROBABILITY
            generated_articles_metadata.append(
                GeneratedArticleMetadata(
                    body=result,
                    label=label,
                    model_version=prompt.TARGET_MODEL,
                    prompt_version=prompt.VERSION,
                )
            )

        shuffle(generated_articles_metadata)
        labels = [a.label for a in generated_articles_metadata]
        articles_to_review = [a.body for a in generated_articles_metadata]

        self.__metadata = Metadata(
            generated_articles_metadata=generated_articles_metadata,
            original_article_metadata=OriginalArticleMetadata(
                body=article_text,
                _id=original_article.id,
                url=original_article.url,
                categories=original_article.categories,
            ),
        )

        return ArticleSynapse(
            articles_to_review=articles_to_review,
            original_article=article_text,
            fake_probabilities=[-1.0] * len(prompts),
        ), labels

    def metadata(self):
        return {
            **self.__metadata.model_dump(),
            **super().metadata(),
        }

    async def save_dataset(self) -> None:
        """
        Saves the dataset to the database.
        """
        dataset = []
        original_id = self.__metadata.original_article_metadata._id  # noqa: SLF001
        for generated_article in self.__metadata.generated_articles_metadata:
            dataset.append(
                SaveLLMRewrittenArticleModel(
                    original_id=original_id,
                    body=generated_article.body,
                    model_version=generated_article.model_version,
                    prompt_version=generated_article.prompt_version,
                    type="fake" if generated_article.label == 1.0 else "paraphrased",
                ).model_dump()
            )
        await self._news_api_client.save_articles_dataset(dataset)

    def _select_sampled_prompts(self) -> list[ValidatorPrompt]:
        sampled_prompts = []

        prompts = [p for p, _ in self.PROMPT_SAMPLING_PROBABILITIES]
        sample_rates = [r for _, r in self.PROMPT_SAMPLING_PROBABILITIES]

        for _ in range(self.PROMPTS_SAMPLE_SIZE):
            prompt = choices(prompts, weights=sample_rates, k=1)[0]  # noqa: S311
            sampled_prompts.append(prompt)

            if not self.ALLOW_PROMPTS_REPEAT:
                index = prompts.index(prompt)
                prompts.pop(index)
                sample_rates.pop(index)

        return sampled_prompts

    def _select_sampled_prompts_1_fake_1_original(self) -> list[ValidatorPrompt]:
        sampled_prompts = []

        fake_prompts = [p for p, _ in self.FAKE_SAMPLING_PROBABILITIES]
        fake_sample_rates = [r for _, r in self.FAKE_SAMPLING_PROBABILITIES]

        paraphrase_prompts = [p for p, _ in self.PARAPHRASE_SAMPLING_PROBABILITIES]
        paraphrase_sample_rates = [r for _, r in self.PARAPHRASE_SAMPLING_PROBABILITIES]

        sampled_prompts.append(choices(fake_prompts, weights=fake_sample_rates, k=1)[0])  # noqa: S311
        sampled_prompts.append(choices(paraphrase_prompts, weights=paraphrase_sample_rates, k=1)[0])  # noqa: S311

        shuffle(sampled_prompts)
        return sampled_prompts
