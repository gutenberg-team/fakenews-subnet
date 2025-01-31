# The MIT License (MIT)
# Copyright © 2023 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
import math
from typing import Final

import bittensor as bt
import numpy as np

from fakenews.validator.performance_tracker import PerformanceTracker
from fakenews.validator.task import ValidatorTask


class RewardCalculator:
    _LONG_ALPHA: Final[float] = (
        0.5  # Weight for long term performance, 1 - _LONG_ALPHA is the weight for short term performance
    )
    _LONG_TERM_WINDOW: Final[int] = 300
    _SHORT_TERM_WINDOW: Final[int] = 20

    @classmethod
    def get_rewards(
        cls,
        labels: list[float],
        responses: list[list[float]],
        uids: list[int],
        axons: list[bt.axon],
        performance_trackers: dict[ValidatorTask, PerformanceTracker],
        current_task: ValidatorTask,
    ) -> tuple[np.ndarray, dict]:
        """
        Calculate rewards for the validators based on the responses from the miners.

        Args:
            labels (list[float]): Ground truth labels for comparison.
            responses (list[list[float]]): Miner responses in the range [0.0, 1.0].
            uids (list[int]): Miner UIDs.
            axons (list[bt.axon]): Miner axons.
            performance_trackers (dict[ValidatorTask, PerformanceTracker]): Task-specific performance trackers.
            current_task (ValidatorTask): The current validation task.

        Returns:
            np.ndarray: Calculated rewards for each miner.
        """
        miner_rewards = []
        miner_rewards_calculating_metadata = []

        bt.logging.debug(
            f"Calculating rewards for task {current_task.TASK_NAME}. Long alpha: {cls._LONG_ALPHA}, "
            f"long term window: {cls._LONG_TERM_WINDOW}, short term window: {cls._SHORT_TERM_WINDOW}"
        )

        for axon, uid, probs in zip(axons, uids, responses):
            metadata = {}
            hotkey = axon.hotkey
            final_reward = 0

            bt.logging.debug(f"Calculating reward for miner {uid} with hotkey {hotkey}. Probabilities: {probs}")

            normalized_probs = cls._normalize_miner_probs(probs, labels)

            if probs != normalized_probs:
                bt.logging.warning(f"Normalized probabilities: {normalized_probs}")

            for task, performance_tracker in performance_trackers.items():
                bt.logging.debug(f"Calculating reward for task {task.TASK_NAME}")

                if task == current_task:
                    for normalized_score, label in zip(normalized_probs, labels):
                        performance_tracker.update(uid, normalized_score, label, hotkey)

                tracked_hotkeys = performance_tracker.miner_hotkeys
                if tracked_hotkeys.get(uid) != hotkey:
                    bt.logging.info(f"Miner hotkey changed for UID {uid}. Resetting performance metrics.")
                    performance_tracker.reset_miner_history(uid, hotkey)

                reward = 0
                metrics_long = metrics_short = None

                try:
                    metrics_long = performance_tracker.get_metrics(uid, window=cls._LONG_TERM_WINDOW)
                    metrics_short = performance_tracker.get_metrics(uid, window=cls._SHORT_TERM_WINDOW)
                    reward = cls._evaluate_task_based_reward(metrics_long, metrics_short)
                except Exception as e:
                    bt.logging.error(f"Couldn't calculate reward for miner {uid}, score: {probs}, label: {labels}")
                    bt.logging.exception(e)

                weighted_reward = task.REWARD_WEIGHT * reward

                metadata[task.TASK_NAME] = {
                    "probabilities": probs,
                    "normalized_probabilities": normalized_probs,
                    "metrics_long": metrics_long,
                    "metrics_short": metrics_short,
                    "reward": reward,
                    "reward_weight": task.REWARD_WEIGHT,
                    "weighted_reward": weighted_reward,
                }
                bt.logging.debug(f"Calculated reward: {reward}. Task weighted reward: {weighted_reward}")

                final_reward += weighted_reward

            miner_rewards.append(final_reward)
            miner_rewards_calculating_metadata.append(metadata)

        calculating_metadata = {
            "by_miner_details": miner_rewards_calculating_metadata,
            "long_alpha": cls._LONG_ALPHA,
            "long_term_window": cls._LONG_TERM_WINDOW,
            "short_term_window": cls._SHORT_TERM_WINDOW,
        }

        return np.array(miner_rewards), calculating_metadata

    @classmethod
    def _evaluate_task_based_reward(
        cls,
        metrics_long: dict[str, float],
        metrics_short: dict[str, float],
    ) -> float:
        bt.logging.debug(f"Metrics long: {metrics_long}, metrics short: {metrics_short}")
        return cls._LONG_ALPHA * metrics_long["accuracy"] + (1 - cls._LONG_ALPHA) * metrics_short["accuracy"]

    @staticmethod
    def _normalize_miner_probs(probs: list[float], labels: list[float]) -> list[float]:
        """
        Normalize the miner probabilities.
        At this step, we should check did the miner return the correct probabilities in target format.
        If not, we should set the probabilities to be in the range [0.0, 1.0] and this value should be opposite from
        label values.
        So, if miner miss the output format, we'll store his answer as wrong.
        """
        normalized_probs = []

        if len(probs) != len(labels):
            probs = [-1.0] * len(labels)

        for prob, label in zip(probs, labels):
            _prob = prob
            if not isinstance(prob, (float, int)) or math.isnan(prob) or math.isinf(prob):
                _prob = -1.0
            elif isinstance(prob, (int, bool)):
                _prob = float(prob)

            normalized_prob = float(_prob) if _prob >= 0.0 and _prob <= 1.0 else abs(label - 1)
            normalized_probs.append(normalized_prob)

        return normalized_probs
