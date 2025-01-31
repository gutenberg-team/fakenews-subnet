from fakenews.services.openai.prompts import ValidatorPrompt


class WeakFakeV4Prompt(ValidatorPrompt):
    VERSION = "weak_fake_v4"
    TARGET_MODEL = "gpt-4o-mini"
    LABEL_PROBABILITY = 1.0
    PROMPT_TEMPLATE = """
    Follow these steps to analyze the news article. The contents of the article will be delimited with special string: `####`.
    Step 1: #### List the critical objects, events, relations, assumptions, and opinions
    provided by the article. You should with each item of the list starting with '*'.
    Step 2: #### Choose the best suiting role below to modify the news article adding inaccurate information. The
    selection of role should be based on the degree of confidences you think the example scenario of the role aligns with the article.

    1. Financial Gain: This guy works for a hostile organizbation of interests. Criticizing and misrepresenting the
    product/service mentioned in the article can make more customers turn to other
    product/service.

    2. Political Agenda: This guy modifies articles supports a particular political ideology or
    candidate to make the public opinions turn against them  (e.g. fail to vote for them) by cleverly falsifying data.

    3. Social Media Attention: This guy rewrites articles by stressing the over exaggerating negative effects and
    ignoring positive aspects of things to get others' attention.

    4. Mischievous Intent: This persona crafts narratives that pokes fun at insignificant details by means of representation and meaning manipulation.

    5. Promotion of Hate: This persona hates an agenda or ideology and wants to sway public's opinion by manipulating facts and claiming that the agenda/ideology is false if it contradicts to his views.

    6. Competing with Legitimate Sources: This personal does not trust legitimate news sources and wants to convince the others by diverting attention away from accurate reporting.

    7. Personal Vendettas: This persona hates someone interviewed in the article and tries to make his/her claim look wrong.

    8. Ideological Manipulation: This persona is overly religious and believes that some unexplained events are done by gods.This persona may claim some shocking discovery or disaster are of supernatural nature.

    Step 3: #### Consider that you are the selected role, and you want to modify the critical
    factors to achieve your goal. There are some rules to follow during modification:

    The modifications have to change the meaning of the factors.

    You should not directly cite/question/negate the content of the original article. Rewrite
    the modified factor as if you are the first to report it.

    All the modifications should serve the same conclusion, however, they must falsify some parts. The conclusion should express a clear opinion which is different from the original article's conclusion.

    The objectives of the modifications should be logically consisted.
    Let's think step by step, what would you do to modify the article?
    Step 4: #### write an article with the modified factors in the writing style of the original article.
    The article should be of the similar length as the original article. Do not add title for the article.
    Always start your answer with special string: `Article: #### \n`
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
