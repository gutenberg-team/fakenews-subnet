import json
from typing import Literal

from pydantic import BaseModel


class ArticleResponseModel(BaseModel):
    id: int
    title: str
    body: str
    categories: list[str]
    url: str


class SaveLLMRewrittenArticleModel(BaseModel):
    original_id: int
    body: str
    type: Literal["paraphrased", "fake"]
    model_version: str
    prompt_version: str
