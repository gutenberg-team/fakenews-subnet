from abc import ABC, abstractmethod
from typing import Any


class Prompt(ABC):
    VERSION: str
    PROMPT_TEMPLATE: str
    TARGET_MODEL: str

    @abstractmethod
    def normalize_result(self) -> Any: ...

    @abstractmethod
    def generate_messages(self, *arg, **kwargs) -> list[dict[str, str]]: ...


class ValidatorPrompt(Prompt):
    LABEL_PROBABILITY: float


class MinerPrompt(Prompt): ...
