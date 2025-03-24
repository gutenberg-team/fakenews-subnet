from .base import ValidatorTask, select_task
from .fakenews_detection_no_original import FakenewsDetectionNoOriginal
from .fakenews_detection_with_original import FakenewsDetectionWithOriginal

__all__ = [
    "FakenewsDetectionNoOriginal",
    "FakenewsDetectionWithOriginal",
    "ValidatorTask",
    "select_task",
]
