from .base import MinerPrompt, Prompt, ValidatorPrompt
from .fake_generating import StrongFakeV1Prompt, WeakFakeV4Prompt
from .fake_probabilities import GetProbabilitesPrompt
from .paraphrasing import StrongOriginalV5Prompt, WeakOriginalV1Prompt

__all__ = [
    "GetProbabilitesPrompt",
    "MinerPrompt",
    "Prompt",
    "StrongFakeV1Prompt",
    "StrongOriginalV5Prompt",
    "ValidatorPrompt",
    "WeakFakeV4Prompt",
    "WeakOriginalV1Prompt",
]
