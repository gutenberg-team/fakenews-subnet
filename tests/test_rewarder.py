import numpy as np
from pytest import mark
from substrateinterface import Keypair

from fakenews.validator import PerformanceTracker, RewardCalculator
from fakenews.validator.task import FakenewsDetectionWithOriginal, ValidatorTask


class AxonMock:
    def __init__(self, hotkey):
        self.hotkey = hotkey


class TestTask(ValidatorTask):
    def prepare_synapse(self, *args, **kwargs): ...
    async def save_dataset(self, *args, **kwargs): ...


class TestRewardCalculator:
    @mark.parametrize(
        "responses, expected",
        [
            ([[0.0, 1.0], [1.0, 0.0]], [1.0, 0.0]),
            (
                [[0.0, 1.1], [1.0, -0.1], [1.0, float("-inf")], [0.5, float("+inf")], [0.1, float("NaN")]],
                [0.5, 0.0, 0.0, 0.5, 0.5],
            ),
            (
                [["123", None], [object(), object], [False, True]],
                [0.0, 0.0, 1.0],
            ),
            ([[0.0, 0.9], [0.0000001, 0.96], [0.5, 0.51]], [1.0, 1.0, 1.0]),
        ],
    )
    def test_get_rewards(self, responses, expected):
        labels = [0, 1]
        uids = list(range(len(responses)))
        axons = [AxonMock(str(uid)) for uid in uids]

        task = TestTask()
        performance_trackers = {task: PerformanceTracker()}

        rewards, _ = RewardCalculator.get_rewards(labels, responses, uids, axons, performance_trackers, task)

        expected = np.array(expected)
        assert np.array_equal(rewards, expected)

    def test_get_rewards_negative_retrospective_correct_response(self):
        labels = [0, 1]
        uids = [1]
        axons = [AxonMock(str(uid)) for uid in uids]

        task = TestTask()
        performance_tracker = PerformanceTracker()

        for _ in range(RewardCalculator._LONG_TERM_WINDOW):  # noqa: SLF001
            performance_tracker.update(1, 1, 0, "1")

        performance_trackers = {task: performance_tracker}

        rewards, _ = RewardCalculator.get_rewards(labels, [labels], uids, axons, performance_trackers, task)

        assert np.allclose(rewards, np.array([0.05]), atol=0.01)

    def test_get_rewards_positive_retrospective_wrong_response(self):
        labels = [0, 1]
        uids = [1]
        axons = [AxonMock(str(uid)) for uid in uids]

        task = TestTask()
        performance_tracker = PerformanceTracker()

        for _ in range(RewardCalculator._LONG_TERM_WINDOW):  # noqa: SLF001
            performance_tracker.update(1, 1, 1, "1")

        performance_trackers = {task: performance_tracker}

        rewards, _ = RewardCalculator.get_rewards(labels, [labels[::-1]], uids, axons, performance_trackers, task)

        assert np.allclose(rewards, np.array([0.95]), atol=0.01)
