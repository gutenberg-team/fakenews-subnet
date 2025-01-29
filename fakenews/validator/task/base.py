from abc import ABC, abstractmethod
from random import choices
from typing import Optional

from fakenews.protocol import ArticleSynapse


class ValidatorTask(ABC):
    """Abstract base class representing a validator task for generating an synapse."""

    TASK_NAME: str = "Base"
    REWARD_WEIGHT: float = 1.0
    FORWARD_PROBABILTY: float = 1.0

    @abstractmethod
    async def prepare_synapse(self, *args, **kwargs) -> Optional[ArticleSynapse]:
        """Abstract method to prepare an ArticleSynapse."""
        ...

    @abstractmethod
    async def save_dataset(self, *args, **kwargs) -> None:
        """Abstract method to save the dataset."""
        ...

    def metadata(self) -> dict:
        """Returns metadata about the task."""
        return {
            "task_name": self.TASK_NAME,
            "reward_weight": self.REWARD_WEIGHT,
            "forward_probability": self.FORWARD_PROBABILTY,
        }

    def __hash__(self):
        return hash(self.TASK_NAME)

    def __eq__(self, other: "ValidatorTask"):
        return self.TASK_NAME == other.TASK_NAME


def select_task(tasks: list[ValidatorTask]) -> ValidatorTask:
    """
    Picks a task based on the FORWARD_PROBABILTY property of each task.

    Args:
        tasks (list[ValidatorTask]): List of tasks to choose from.
    Returns:
        ValidatorTask: The selected task
    """
    return choices(tasks, weights=[task.FORWARD_PROBABILTY for task in tasks], k=1)[0]  # noqa: S311
