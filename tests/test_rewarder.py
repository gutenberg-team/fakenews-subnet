import numpy as np
import pytest

from fakenews.validator import PerformanceTracker, RewardCalculator
from fakenews.validator.task import ValidatorTask


class AxonMock:
    def __init__(self, hotkey):
        self.hotkey = hotkey


class TestTask(ValidatorTask):
    def prepare_synapse(self, *args, **kwargs): ...
    async def save_dataset(self, *args, **kwargs): ...


@pytest.fixture
def axons():
    return lambda uids: [AxonMock(str(uid)) for uid in uids]


@pytest.fixture
def task():
    return TestTask()


@pytest.fixture
def performance_tracker():
    return PerformanceTracker()


@pytest.fixture
def performance_trackers(task, performance_tracker):
    return {task: performance_tracker}


@pytest.mark.parametrize(
    "responses, expected",
    [
        ([[0.0, 1.0], [1.0, 0.0]], [0.05, 0.0]),
        (
            [[0.0, 1.1], [1.0, -0.1], [1.0, float("-inf")], [0.5, float("+inf")], [0.1, float("NaN")]],
            [0.02, 0.0, 0.0, 0.02, 0.02],
        ),
        (
            [["123", None], [object(), object], [False, True]],
            [0.0, 0.0, 0.05],
        ),
        ([[0.0, 0.9], [0.0000001, 0.96], [0.5, 0.51]], [.05, .05, .05]),
    ],
)
def test_get_rewards_no_retrospective_data(task, axons, responses, expected):
    labels = [0, 1]
    uids = list(range(len(responses)))
    rewards, _ = RewardCalculator.get_rewards(
        labels, responses, uids, axons(uids), {task: PerformanceTracker()}, task
    )
    assert np.allclose(rewards, np.array(expected), atol=0.01)


def test_get_rewards_full_negative_retrospective_correct_response(
    task, axons, performance_tracker, performance_trackers
):
    labels = [0, 1]
    uids = [1]
    for _ in range(RewardCalculator._LONG_TERM_WINDOW):
        performance_tracker.update(1, 1, 0, "1")
    rewards, _ = RewardCalculator.get_rewards(labels, [labels], uids, axons(uids), performance_trackers, task)
    assert np.allclose(rewards, np.array([0.05]), atol=0.01)


def test_get_rewards_full_positive_retrospective_wrong_response(
    task, axons, performance_tracker, performance_trackers
):
    labels = [0, 1]
    uids = [1]
    for _ in range(RewardCalculator._LONG_TERM_WINDOW):
        performance_tracker.update(1, 1, 1, "1")
    rewards, _ = RewardCalculator.get_rewards(labels, [labels[::-1]], uids, axons(uids), performance_trackers, task)
    assert np.allclose(rewards, np.array([0.95]), atol=0.01)


def test_get_rewards_short_period_positive_retrospective_half_reward(
    task, axons, performance_tracker, performance_trackers
):
    labels = [0, 1]
    uids = [1]
    for _ in range(RewardCalculator._SHORT_TERM_WINDOW):
        performance_tracker.update(1, 1, 1, "1")
    rewards, _ = RewardCalculator.get_rewards(labels, [labels], uids, axons(uids), performance_trackers, task)
    assert np.greater_equal(rewards, np.array([0.5])).all()


def test_get_rewards_full_positive_retrospective_last_negative_half_reward(
    task, axons, performance_tracker, performance_trackers
):
    labels = [0, 1]
    uids = [1]
    for _ in range(RewardCalculator._LONG_TERM_WINDOW - RewardCalculator._SHORT_TERM_WINDOW):
        performance_tracker.update(1, 1, 1, "1")
    for _ in range(RewardCalculator._SHORT_TERM_WINDOW):
        performance_tracker.update(1, 0, 1, "1")
    rewards, _ = RewardCalculator.get_rewards(labels, [labels[::-1]], uids, axons(uids), performance_trackers, task)
    assert np.less_equal(rewards, np.array([0.5])).all()

@pytest.mark.parametrize(
    "response",
    [
        [0.0, 1.0],
        [1.0, 0.0],
        [0.0, 1.1],
        [1.0, -0.1],
        [1.0, float("-inf")],
        [0.5, float("+inf")],
        [0.1, float("NaN")],
        ["123", None],
        [object(), object],
    ])
def test_rewards_full_negative_and_empty_retrospective_are_equal(
    task, axons, performance_tracker, performance_trackers, response
):
    labels = [0, 1]
    uids = [0, 1]
    for _ in range(RewardCalculator._LONG_TERM_WINDOW):
        performance_tracker.update(1, 1, 0, "1")
    responses = [response, response]
    rewards, _ = RewardCalculator.get_rewards(labels, responses, uids, axons(uids), performance_trackers, task)
    assert rewards[0] == rewards[1]
