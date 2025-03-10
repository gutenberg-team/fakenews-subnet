from fakenews.services.openai.prompts import ValidatorPrompt


class WeakOriginalV1Prompt(ValidatorPrompt):
    VERSION = "weak_original_v1"
    TARGET_MODEL = "gpt-4o-mini"
    LABEL_PROBABILITY = 0.0
    PROMPT_TEMPLATE = """
    Guidelines:
    - Rewrite the news article using dramatic and emotionally charged language to amplify the intensity of the events.
    - Shift the focus away from the primary issue by highlighting less critical but potentially controversial details.
    - Frame key points as loaded questions to create doubt or encourage skepticism, even if the original content presented them as facts.
    - Always start your answer with: Article: #### \n
    """

    __slots__ = ["article"]

    def __init__(self, original_article: str):
        self.article = original_article

    def normalize_result(self, response: str) -> str:
        article_anchor = "Article: ####"
        target_start = response.find(article_anchor)
        if target_start == -1:
            raise ValueError(f"Failed to find the article anchor in the response: {response}")
        return response[target_start + len(article_anchor) :].replace("####", "").strip()

    def generate_messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.PROMPT_TEMPLATE},
            {"role": "user", "content": self.article},
        ]
