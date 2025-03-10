from fakenews.services.openai.prompts import ValidatorPrompt


class StrongFakeV1Prompt(ValidatorPrompt):
    VERSION = "strong_fake_v1"
    TARGET_MODEL = "gpt-4o-mini"
    LABEL_PROBABILITY = 1.0
    PROMPT_TEMPLATE = """
    Role: You are an experienced journalist tasked with modifying a news article.
    Guidelines:
    You will receive a news article. Your task is to rewrite the article to shift its underlying perspective while maintaining its original tone and length.

    Step 1:
    Identify key objects, events, relationships, assumptions, and opinions in the article, listing each with a '*'.

    Step 2:
    Modify one of the key objects (date, event name, relationship type, etc).

    Step 3:
    Present the modified article with the amendment. Ensure that it is first-reported and logically consistent. Maintain a professional tone and engaging style, ensuring readability and clarity. Avoid stylistic shifts in the article The article should be of the similar length as the original article. Do not add title for the article.

    Always start your step 3 answer with: Article: #### \n

    Be verbal about the steps.
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
