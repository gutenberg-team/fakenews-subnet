from bittensor import logging
from openai import APIStatusError, AsyncOpenAI, InternalServerError

from fakenews.exceptions import OpenAIClientError, OpenAIInternalError

from .prompts import Prompt


class OpenAIClient(AsyncOpenAI):
    def __init__(self, *args, **kwargs):
        if not kwargs.get("api_key"):
            raise ValueError("OpenAI API key is required.")
        super().__init__(*args, **kwargs)

    async def get_prompt_completions_async(self, prompt: Prompt) -> str:
        result = await self._get_completions_async(prompt.generate_messages(), prompt.TARGET_MODEL)
        return prompt.normalize_result(result)

    async def _get_completions_async(self, messages: list[dict], model: str) -> str:
        logging.debug(f"Prompt: {messages}")
        try:
            completions = await self.chat.completions.create(
                model=model,
                messages=messages,
            )
            response = completions.choices[0].message.content
        except InternalServerError as e:
            logging.error(f"Open AI is unavailable: {e}")
            raise OpenAIInternalError from e

        except APIStatusError as e:
            logging.error(f"Failed to access OpenAI API. Check your API key balance or permission: {e}")
            raise OpenAIClientError from e

        except BaseException as e:
            logging.error(f"Failed to get completions from OpenAI: {e}")
            raise e

        logging.debug(f"Response: {response}")
        return response
