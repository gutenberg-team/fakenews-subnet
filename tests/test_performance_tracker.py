import os
from collections import deque
from unittest import mock

from joblib import dump, load
from sklearn.metrics import accuracy_score

from fakenews.validator.performance_tracker import PerformanceTracker


def test_initialization():
    tracker = PerformanceTracker()
    assert tracker.store_last_n_predictions == PerformanceTracker.STORE_LAST_N_PREDICTIONS_DEFAULT
    assert tracker.prediction_history == {}
    assert tracker.label_history == {}
    assert tracker.miner_hotkeys == {}


def test_reset_miner_history():
    tracker = PerformanceTracker()
    tracker.reset_miner_history(1, "hotkey_1")
    assert isinstance(tracker.prediction_history[1], deque)
    assert isinstance(tracker.label_history[1], deque)
    assert tracker.miner_hotkeys[1] == "hotkey_1"


def test_update_new_miner():
    tracker = PerformanceTracker()
    tracker.update(1, 1, 1, "hotkey_1")
    assert list(tracker.prediction_history[1]) == [1]
    assert list(tracker.label_history[1]) == [1]


def test_update_existing_miner():
    tracker = PerformanceTracker()
    tracker.update(1, 1, 1, "hotkey_1")
    tracker.update(1, 0, 1, "hotkey_1")
    assert list(tracker.prediction_history[1]) == [1, 0]
    assert list(tracker.label_history[1]) == [1, 1]


def test_update_miner_hotkey_change():
    tracker = PerformanceTracker()
    tracker.update(1, 1, 1, "hotkey_1")
    tracker.update(1, 0, 1, "hotkey_2")  # Hotkey change should reset history
    assert list(tracker.prediction_history[1]) == [0]
    assert list(tracker.label_history[1]) == [1]


def test_validate_storage_predictions_count():
    initial_count = PerformanceTracker.STORE_LAST_N_PREDICTIONS_DEFAULT * 2
    tracker = PerformanceTracker(store_last_n_predictions=initial_count)
    for i in range(initial_count):
        tracker.update(1, i, i, "hotkey_1")
    expected_predictions = list(tracker.prediction_history[1])[PerformanceTracker.STORE_LAST_N_PREDICTIONS_DEFAULT :]
    expected_labels = list(tracker.label_history[1])[PerformanceTracker.STORE_LAST_N_PREDICTIONS_DEFAULT :]

    assert len(tracker.prediction_history[1]) == initial_count

    tracker.validate_storage_predictions_count()
    assert len(tracker.prediction_history[1]) == PerformanceTracker.STORE_LAST_N_PREDICTIONS_DEFAULT
    assert len(tracker.label_history[1]) == PerformanceTracker.STORE_LAST_N_PREDICTIONS_DEFAULT
    assert list(tracker.prediction_history[1]) == list(expected_predictions)
    assert list(tracker.label_history[1]) == list(expected_labels)


def test_get_metrics_no_data():
    tracker = PerformanceTracker()
    assert tracker.get_metrics(1) == {"accuracy": 0}


def test_get_metrics_with_data():
    tracker = PerformanceTracker()
    tracker.update(1, 1, 1, "hotkey_1")
    tracker.update(1, 0, 0, "hotkey_1")
    metrics = tracker.get_metrics(1)
    assert "accuracy" in metrics
    assert metrics["accuracy"] == accuracy_score([1, 0], [1, 0])


def test_get_metrics_with_window():
    tracker = PerformanceTracker()
    for _ in range(10):
        tracker.update(1, 1, 1, "hotkey_1")
        tracker.update(1, 0, 0, "hotkey_1")
    metrics = tracker.get_metrics(1, window=5)
    assert metrics["accuracy"] == 1.0  # Since last 5 predictions were all correct


def test_get_metrics_invalid_window():
    tracker = PerformanceTracker()
    tracker.update(1, 1, 1, "hotkey_1")
    with mock.patch("bittensor.logging.error") as mocked_log:
        assert tracker.get_metrics(1, window=-1) == {"accuracy": 0}
        mocked_log.assert_called_once()


def test_get_metrics_large_window():
    tracker = PerformanceTracker()
    tracker.update(1, 1, 1, "hotkey_1")
    tracker.update(1, 0, 1, "hotkey_1")
    with mock.patch("bittensor.logging.warning") as mocked_log:
        metrics = tracker.get_metrics(1, window=1000)
        assert mocked_log.called
        assert "accuracy" in metrics


def test_ignore_invalid_predictions():
    tracker = PerformanceTracker()
    tracker.update(1, -1, 1, "hotkey_1")  # Invalid prediction
    tracker.update(1, 1, 1, "hotkey_1")
    metrics = tracker.get_metrics(1)
    assert metrics["accuracy"] == 1.0  # Only valid prediction considered


def test_large_data_storage():
    tracker = PerformanceTracker(store_last_n_predictions=5)
    for i in range(10):
        tracker.update(1, i % 2, i % 2, "hotkey_1")
    assert len(tracker.prediction_history[1]) == 5  # Should retain last 5 entries


def test_huge_performance_history():
    tracker = PerformanceTracker()
    for i in range(10000):
        tracker.update(1, i % 2, i % 2, "hotkey_1")
    assert len(tracker.prediction_history[1]) == tracker.STORE_LAST_N_PREDICTIONS_DEFAULT


def test_multiple_miners():
    tracker = PerformanceTracker()
    tracker.update(1, 1, 1, "hotkey_1")
    tracker.update(2, 0, 1, "hotkey_2")
    assert len(tracker.prediction_history) == 2


def test_validate_storage_predictions_count_with_override():
    tracker = PerformanceTracker(store_last_n_predictions=10)
    tracker.update(1, 1, 1, "hotkey_1")
    tracker.update(1, 0, 0, "hotkey_1")
    tracker.validate_storage_predictions_count()
    assert tracker.store_last_n_predictions == PerformanceTracker.STORE_LAST_N_PREDICTIONS_DEFAULT


def test_dump_and_load():
    if not os.path.exists("tmp"):
        os.mkdir("tmp")
    tracker = PerformanceTracker()
    tracker.update(1, 1, 1, "hotkey_1")
    tracker.update(1, 0, 0, "hotkey_1")
    dump(tracker, "tmp/test.pkl")
    loaded_tracker = load("tmp/test.pkl")
    assert loaded_tracker.prediction_history == tracker.prediction_history
    assert loaded_tracker.label_history == tracker.label_history
    assert loaded_tracker.miner_hotkeys == tracker.miner_hotkeys
    assert loaded_tracker.store_last_n_predictions == tracker.store_last_n_predictions
    assert loaded_tracker.get_metrics(1) == tracker.get_metrics(1)
    assert loaded_tracker.get_metrics(1, window=1) == tracker.get_metrics(1, window=1)
    assert loaded_tracker.get_metrics(1, window=2) == tracker.get_metrics(1, window=2)
    assert loaded_tracker.get_metrics(1, window=1000) == tracker.get_metrics(1, window=1000)
    assert loaded_tracker.get_metrics(2) == tracker.get_metrics(2)
    assert loaded_tracker.get_metrics(2, window=1) == tracker.get_metrics(2, window=1)
    assert loaded_tracker.get_metrics(2, window=2) == tracker.get_metrics(2, window=2)
    assert loaded_tracker.get_metrics(2, window=1000) == tracker.get_metrics(2, window=1000)
    os.remove("tmp/test.pkl")
