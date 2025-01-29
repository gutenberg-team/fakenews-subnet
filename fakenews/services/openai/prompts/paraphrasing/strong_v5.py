from fakenews.services.openai.prompts import ValidatorPrompt


class StrongOriginalV5Prompt(ValidatorPrompt):
    VERSION = "strong_original_v5"
    TARGET_MODEL = "gpt-4o"
    LABEL_PROBABILITY = 0.0
    PROMPT_TEMPLATE = """
    Role: You are a professional journalist with extensive experience in writing and analyzing articles
    I will send you a news article.
    Your task is to rewrite the article without changing any facts or distorting the truth.

    Guidelines:
    - The rewritten version should maintain the original accuracy and integrity of the information but be expressed in a fresh and unique way.
    - Focus on clarity, readability, and neutrality, ensuring that the tone is professional and the content is engaging.
    - Do not add, remove, or alter any factual details from the original article.
    - You should provide only a paraphrased text of the article. Do not include any additional information or commentary.
    - Always start your answer with special string: `Article: #### \n`
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
