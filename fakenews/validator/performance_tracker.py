from collections import deque

import bittensor as bt
import numpy as np
from sklearn.metrics import accuracy_score


class PerformanceTracker:
    """
    Tracks all recent miner performance to facilitate reward computation.
    """

    def __init__(self, store_last_n_predictions: int = 500):
        self.prediction_history: dict[int, deque] = {}
        self.label_history: dict[int, deque] = {}
        self.miner_hotkeys: dict[int, str] = {}
        self.store_last_n_predictions: int = store_last_n_predictions

    def reset_miner_history(self, uid: int, miner_hotkey: str):
        """
        Reset the history for a miner.
        """
        self.prediction_history[uid] = deque(maxlen=self.store_last_n_predictions)
        self.label_history[uid] = deque(maxlen=self.store_last_n_predictions)
        self.miner_hotkeys[uid] = miner_hotkey

    def update(self, uid: int, prediction: int, label: int, miner_hotkey: str):
        """
        Update the miner prediction history
        """
        # Reset histories if miner is new or miner address has changed
        if uid not in self.prediction_history or self.miner_hotkeys.get(uid) != miner_hotkey:
            self.reset_miner_history(uid, miner_hotkey)

        # Update histories
        self.prediction_history[uid].append(prediction)
        self.label_history[uid].append(label)

    def get_metrics(self, uid: int, window: int | None = None, target_metrics: list[str] | None = None):
        """
        Get the performance metrics for a miner based on their last n predictions

        Args:
        - uid (int): Miner UID key
        - window (int, optional): The number of recent predictions to consider. If None, all stored predictions are used.

        Returns:
        - dict:
            [accuracy] (float): The accuracy of the miner's predictions
        """
        available_metrics = {
            "accuracy": 0,
        }

        if uid not in self.prediction_history:
            return available_metrics

        recent_preds = list(self.prediction_history[uid])
        recent_labels = list(self.label_history[uid])

        window_k = 1

        # If window is larger than available data, use all available data
        if window is not None:
            _window = min(window, len(recent_preds))
            recent_preds = recent_preds[-_window:]
            recent_labels = recent_labels[-_window:]
            window_k = _window / window

        keep_idx = [i for i, p in enumerate(recent_preds) if p != -1]
        pred_probs = np.array([recent_preds[i] for i in keep_idx])
        predictions = np.round(pred_probs)
        labels = np.array([recent_labels[i] for i in keep_idx])

        if len(labels) == 0 or len(predictions) == 0:
            return available_metrics

        try:
            accuracy = accuracy_score(labels, predictions) * window_k
            available_metrics.update(
                {
                    "accuracy": accuracy,
                }
            )

        except Exception as e:
            bt.logging.warning(f"Error in reward computation: {e}")
            return available_metrics

        return available_metrics
