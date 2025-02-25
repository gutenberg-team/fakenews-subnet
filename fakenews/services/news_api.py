import traceback
from http import HTTPStatus
from typing import TYPE_CHECKING

import bittensor as bt
from aiohttp import BasicAuth, ClientSession, ClientTimeout

from fakenews.schemas import ArticleResponseModel

if TYPE_CHECKING:
    from substrateinterface import Keypair


class NewsAPIClient:
    __slots__ = ["_auth"]

    BASE_URL = "http://84.32.185.173:8000"
    GET_ARTICLE_URL = f"{BASE_URL}/articles/random"
    SAVE_ARTICLES_DATASET_URL = f"{BASE_URL}/articles/dataset/create"

    def __init__(self, keypair: "Keypair"):
        hotkey = keypair.ss58_address
        signature = f"0x{keypair.sign(hotkey).hex()}"
        self._auth = BasicAuth(hotkey, signature)

    async def fetch_article(self) -> ArticleResponseModel | None:
        try:
            async with (
                ClientSession() as session,
                session.get(
                    self.GET_ARTICLE_URL,
                    auth=self._auth,
                ) as response,
            ):
                if response.status == HTTPStatus.UNAUTHORIZED:
                    details = await response.json()
                    raise Exception(f"Unauthorized: {details}")

                response.raise_for_status()
                article: ArticleResponseModel = await response.json(loads=ArticleResponseModel.model_validate_json)
                return article

        except BaseException as e:
            bt.logging.warning(f"Error while getting article: {e}")
            traceback.print_exc()
            raise e

    async def save_articles_dataset(self, dataset: dict) -> None:
        try:
            async with (
                ClientSession() as session,
                session.post(
                    self.SAVE_ARTICLES_DATASET_URL, auth=self._auth, json=dataset, timeout=ClientTimeout(3)
                ) as response,
            ):
                response.raise_for_status()
        except BaseException as e:
            bt.logging.warning(f"Error while saving dataset: {e}")
            traceback.print_exc()
