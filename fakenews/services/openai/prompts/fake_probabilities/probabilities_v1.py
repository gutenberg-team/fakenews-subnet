import json

from fakenews.services.openai.prompts import MinerPrompt


class GetProbabilitesPrompt(MinerPrompt):
    VERSION = "probabilities_v1"
    TARGET_MODEL = "gpt-4o-mini"
    PROMPT_TEMPLATE = """
    Role: You are a professional journalist with extensive experience in writing and analyzing articles.
    Your press office frequently uses quotations from various sources, so you are skilled at determining whether an article is fabricated or credible.

    Task:
    I will provide the original news article as well as several rewritten articles. They may have fabricated facts.
    You need to score how closely each article matches the original article.
    Here's text of original article:
    ```
    {original_article}
    ```

    Scoring Guidelines:
    You will evaluate each article based on the following criteria:
    - Factual Accuracy: Assess whether the claims in the article are supported by verifiable facts.
    - Logical Consistency: Determine if the sequence of events or arguments presented in the article is logical and plausible.
    - Writing Style: Evaluate the tone and intent of the article—whether it leans towards sensationalism or maintains a professional, credible tone.

    Scoring System:
    - 0: The article is completely truthful, supported by credible evidence, and can be fully trusted.
    - 0.5 and less: The article contains inaccuracies or errors but retains enough truth to be cited cautiously.
    - 0.6 and more: The article is mostly fabricated and should not be trusted or referenced.
    - 1: The article is entirely false or fabricated, with no factual basis.

    Instructions:
    Focus solely on the explicit claims within each article.
    Provide a score for each article based on the reliability of its content.
    If an article lacks sufficient information for verification, base the score on the plausibility and reliability of its claims.

    Output requirements:
    Avoid adding explanations or context — return only the final scores as a JSON array (should be JSON serializable).
    For a set of articles, your response should look like this example:
    [
        0.4,
        0.7
    ]
    """

    __slots__ = ["articles_to_review", "original_article"]

    def __init__(self, original_article: str, articles_to_review: list[str]):
        self.original_article = original_article
        self.articles_to_review = articles_to_review

    def normalize_result(self, response: str) -> list[float]:
        cleaned_response = response.strip("\n").strip("`").strip()
        if cleaned_response.startswith("json"):
            cleaned_response = cleaned_response[len("json") :].strip()

        try:
            probs = json.loads(cleaned_response)
            if isinstance(probs, list) and all(isinstance(prop, (int, float)) for prop in probs):
                return probs
            raise ValueError("The response did not return a valid list of floats.")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from response: {cleaned_response}") from e

    def generate_messages(self) -> list[dict[str, str]]:
        articles_text = "\n".join([f"```{n}. \n{a}\n```" for n, a in enumerate(self.articles_to_review, start=1)])
        return [
            {"role": "system", "content": self.PROMPT_TEMPLATE.format(original_article=self.original_article)},
            {"role": "user", "content": articles_text},
        ]
