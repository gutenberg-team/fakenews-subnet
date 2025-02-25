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


import argparse
import asyncio
import copy
import datetime as dt
import os
import sys
import threading
import time
from traceback import print_exception
from typing import List, Union

import bittensor as bt
import joblib
import numpy as np
import wandb

import fakenews
from fakenews.base.neuron import BaseNeuron
from fakenews.base.utils.weight_utils import convert_weights_and_uids_for_emit, process_weights_for_netuid
from fakenews.exceptions import TaskDefinitionError
from fakenews.mock import MockDendrite
from fakenews.utils.config import add_validator_args
from fakenews.validator import task as tasks
from fakenews.validator.performance_tracker import PerformanceTracker

# Temporary solution to getting rid of annoying bittensor trace logs
original_trace = bt.logging.trace


def filtered_trace(message, *args, **kwargs):
    if "Unexpected header key encountered" not in message:
        original_trace(message, *args, **kwargs)


bt.logging.trace = filtered_trace


class BaseValidatorNeuron(BaseNeuron):
    """
    Base class for Bittensor validators. Your validator should inherit from this class.
    """

    neuron_type: str = "ValidatorNeuron"
    FORWARD_DELAY_SECONDS: int = 60

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser):
        super().add_args(parser)
        add_validator_args(cls, parser)

    def __init__(self, config=None):
        super().__init__(config=config)

        # Save a copy of the hotkeys to local memory.
        self.hotkeys = copy.deepcopy(self.metagraph.hotkeys)

        # Dendrite lets us send messages to other nodes (axons) in the network.
        if self.config.mock:
            self.dendrite = MockDendrite(wallet=self.wallet)
        else:
            self.dendrite = bt.dendrite(wallet=self.wallet)
        bt.logging.info(f"Dendrite: {self.dendrite}")

        # Set up initial scoring weights for validation
        bt.logging.info("Building validation weights.")
        self.scores = np.zeros(self.metagraph.n, dtype=np.float32)

        self.tasks = [
            tasks.FakenewsDetectionWithOriginal(openai_api_key=self.config.openai_api_key, keypair=self.dendrite.keypair),
        ]

        self._validate_tasks()

        self.performance_trackers = {t: None for t in self.tasks}
        self.load_miner_history()

        self.init_wandb()

        # Init sync with the network. Updates the metagraph.
        self.sync()

        # Serve axon to enable external connections.
        if not self.config.neuron.axon_off:
            self.serve_axon()
        else:
            bt.logging.warning("axon off, not serving ip to chain.")

        # Create asyncio event loop to manage async tasks.
        self.loop = asyncio.get_event_loop()

        # Instantiate runners
        self.should_exit: bool = False
        self.is_running: bool = False
        self.thread: Union[threading.Thread, None] = None
        self.lock = asyncio.Lock()

    def serve_axon(self):
        """Serve axon to enable external connections."""

        bt.logging.info("serving ip to chain...")
        try:
            self.axon = bt.axon(wallet=self.wallet, config=self.config)

            try:
                self.subtensor.serve_axon(
                    netuid=self.config.netuid,
                    axon=self.axon,
                )
                bt.logging.info(
                    f"Running validator {self.axon} on network: {self.config.subtensor.chain_endpoint} with netuid: {self.config.netuid}"
                )
            except Exception as e:
                bt.logging.error(f"Failed to serve Axon with exception: {e}")

        except Exception as e:
            bt.logging.error(f"Failed to create Axon initialize with exception: {e}")

    async def concurrent_forward(self):
        coroutines = [self.forward() for _ in range(self.config.neuron.num_concurrent_forwards)]
        await asyncio.gather(*coroutines)

    def run(self):
        """
        Initiates and manages the main loop for the miner on the Bittensor network.
        The main loop handles graceful shutdown on keyboard interrupts and logs unforeseen errors.

        This function performs the following primary tasks:
        1. Check for registration on the Bittensor network.
        2. Continuously forwards queries to the miners on the network, rewarding their responses and updating the scores accordingly.
        3. Periodically resynchronizes with the chain; updating the metagraph with the latest network state and setting weights.

        The essence of the validator's operations is in the forward function, which is called every step.
        The forward function is responsible for querying the network and scoring the responses.

        Note:
            - The function leverages the global configurations set during the initialization of the miner.
            - The miner's axon serves as its interface to the Bittensor network, handling incoming and outgoing requests.

        Raises:
            KeyboardInterrupt: If the miner is stopped by a manual interruption.
            Exception: For unforeseen errors during the miner's operation, which are logged for diagnosis.
        """

        # Check that validator is registered on the network.
        self.sync()

        bt.logging.info(f"Validator starting at block: {self.block}")

        # This loop maintains the validator's operations until intentionally stopped.
        while True:
            try:
                bt.logging.info(f"step({self.step}) block({self.block})")

                # Run multiple forwards concurrently.
                self.loop.run_until_complete(self.concurrent_forward())

                if not self.config.wandb.off:
                    if (dt.datetime.now() - self.wandb_run_start) >= dt.timedelta(hours=12):
                        bt.logging.info("Current wandb run is more than 1 day old. Starting a new run.")
                        self.wandb_run.finish()
                        self.init_wandb()

                # Check if we should exit.
                if self.should_exit:
                    if not self.config.wandb.off:
                        self.wandb_run.finish()
                    break

                # Sync metagraph and potentially set weights.
                self.sync()
                self.step += 1

                # Wait for the next step.
                time.sleep(self.FORWARD_DELAY_SECONDS)

            # If someone intentionally stops the validator, it'll safely terminate operations.
            except KeyboardInterrupt:
                self.axon.stop()
                bt.logging.success("Validator killed by keyboard interrupt.")
                if not self.config.wandb.off:
                    self.wandb_run.finish()
                sys.exit()

            # In case of unforeseen errors, the validator will log the error and continue operations.
            except Exception as err:
                bt.logging.error(f"Error during validation: {err!s}")
                bt.logging.debug(str(print_exception(type(err), err, err.__traceback__)))
                time.sleep(60)

    def run_in_background_thread(self):
        """
        Starts the validator's operations in a background thread upon entering the context.
        This method facilitates the use of the validator in a 'with' statement.
        """
        if not self.is_running:
            bt.logging.debug("Starting validator in background thread.")
            self.should_exit = False
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            self.is_running = True
            bt.logging.debug("Started")

    def stop_run_thread(self):
        """
        Stops the validator's operations that are running in the background thread.
        """
        if self.is_running:
            bt.logging.debug("Stopping validator in background thread.")
            self.should_exit = True
            self.thread.join(5)
            self.is_running = False
            bt.logging.debug("Stopped")

    def __enter__(self):
        self.run_in_background_thread()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Stops the validator's background operations upon exiting the context.
        This method facilitates the use of the validator in a 'with' statement.

        Args:
            exc_type: The type of the exception that caused the context to be exited.
                      None if the context was exited without an exception.
            exc_value: The instance of the exception that caused the context to be exited.
                       None if the context was exited without an exception.
            traceback: A traceback object encoding the stack trace.
                       None if the context was exited without an exception.
        """
        if self.is_running:
            bt.logging.debug("Stopping validator in background thread.")
            self.should_exit = True
            self.thread.join(5)
            self.is_running = False
            bt.logging.debug("Stopped")

    def set_weights(self):
        """
        Sets the validator weights to the metagraph hotkeys based on the scores it has received from the miners.
        The weights determine the trust and incentive level the validator assigns to miner nodes on the network.
        """

        # Check if self.scores contains any NaN values and log a warning if it does.
        if np.isnan(self.scores).any():
            bt.logging.warning(
                "Scores contain NaN values."
                "This may be due to a lack of responses from miners, or a bug in your reward functions."
            )

        # Calculate the average reward for each uid across non-zero values.
        # Replace any NaN values with 0.
        # Compute the norm of the scores
        norm = np.linalg.norm(self.scores, ord=1, axis=0, keepdims=True)

        # Check if the norm is zero or contains NaN values
        if np.any(norm == 0) or np.isnan(norm).any():
            norm = np.ones_like(norm)  # Avoid division by zero or NaN

        # Compute raw_weights safely
        raw_weights = self.scores / norm

        bt.logging.debug("raw_weights", raw_weights.tolist())
        bt.logging.debug("raw_weight_uids", str(self.metagraph.uids.tolist()))
        # Process the raw weights to final_weights via subtensor limitations.
        (
            processed_weight_uids,
            processed_weights,
        ) = process_weights_for_netuid(
            uids=self.metagraph.uids,
            weights=raw_weights,
            netuid=self.config.netuid,
            subtensor=self.subtensor,
            metagraph=self.metagraph,
        )
        bt.logging.debug("processed_weights", processed_weights.tolist())
        bt.logging.debug("processed_weight_uids", processed_weight_uids.tolist())

        # Convert to uint16 weights and uids.
        (
            uint_uids,
            uint_weights,
        ) = convert_weights_and_uids_for_emit(uids=processed_weight_uids, weights=processed_weights)
        bt.logging.debug("uint_weights", uint_weights)
        bt.logging.debug("uint_uids", uint_uids)

        # Set the weights on chain via our subtensor connection.
        result, msg = self.subtensor.set_weights(
            wallet=self.wallet,
            netuid=self.config.netuid,
            uids=uint_uids,
            weights=uint_weights,
            wait_for_finalization=False,
            wait_for_inclusion=False,
            version_key=self.spec_version,
        )
        if result is True:
            bt.logging.info("set_weights on chain successfully!")
        else:
            bt.logging.error("set_weights failed", msg)

    def resync_metagraph(self):
        """Resyncs the metagraph and updates the hotkeys and moving averages based on the new metagraph."""
        bt.logging.info("resync_metagraph()")

        # Copies state of metagraph before syncing.
        previous_metagraph = copy.deepcopy(self.metagraph)

        # Sync the metagraph.
        self.metagraph.sync(subtensor=self.subtensor)

        # Check if the metagraph axon info has changed.
        if previous_metagraph.axons == self.metagraph.axons:
            return

        bt.logging.info("Metagraph updated, re-syncing hotkeys, dendrite pool and moving averages")
        # Zero out all hotkeys that have been replaced.
        for uid, hotkey in enumerate(self.hotkeys):
            if hotkey != self.metagraph.hotkeys[uid]:
                self.scores[uid] = 0  # hotkey has been replaced

        # Check to see if the metagraph has changed size.
        # If so, we need to add new hotkeys and moving averages.
        if len(self.hotkeys) < len(self.metagraph.hotkeys):
            # Update the size of the moving average scores.
            new_moving_average = np.zeros((self.metagraph.n))
            min_len = min(len(self.hotkeys), len(self.scores))
            new_moving_average[:min_len] = self.scores[:min_len]
            self.scores = new_moving_average

        # Update the hotkeys.
        self.hotkeys = copy.deepcopy(self.metagraph.hotkeys)

    def update_scores(self, rewards: np.ndarray, uids: List[int]):
        """Performs exponential moving average on the scores based on the rewards received from the miners."""

        # Check if rewards contains NaN values.
        if np.isnan(rewards).any():
            bt.logging.warning(f"NaN values detected in rewards: {rewards}")
            # Replace any NaN values in rewards with 0.
            rewards = np.nan_to_num(rewards, nan=0)

        # Ensure rewards is a numpy array.
        rewards = np.asarray(rewards)

        # Check if `uids` is already a numpy array and copy it to avoid the warning.
        uids_array = uids.copy() if isinstance(uids, np.ndarray) else np.array(uids)

        # Handle edge case: If either rewards or uids_array is empty.
        if rewards.size == 0 or uids_array.size == 0:
            bt.logging.info(f"rewards: {rewards.tolist()}, uids_array: {uids_array.tolist()}")
            bt.logging.warning("Either rewards or uids_array is empty. No updates will be performed.")
            return

        # Check if sizes of rewards and uids_array match.
        if rewards.size != uids_array.size:
            raise ValueError(
                f"Shape mismatch: rewards array of shape {rewards.shape} "
                f"cannot be broadcast to uids array of shape {uids_array.shape}"
            )

        # Compute forward pass rewards, assumes uids are mutually exclusive.
        scattered_rewards: np.ndarray = np.zeros_like(self.scores)
        scattered_rewards[uids_array] = rewards
        bt.logging.debug(f"Scattered rewards: {rewards.tolist()}")

        # Update scores with rewards produced by this step.
        alpha: float = self.config.neuron.moving_average_alpha
        self.scores: np.ndarray = alpha * scattered_rewards + (1 - alpha) * self.scores
        bt.logging.debug(f"Updated moving avg scores: {self.scores.tolist()}")

    def save_state(self):
        """Saves the state of the validator to a file."""
        bt.logging.info("Saving validator state.")

        # Save the state of the validator to file.
        np.savez(
            self.config.neuron.full_path + "/state.npz",
            step=self.step,
            scores=self.scores,
            hotkeys=self.hotkeys,
        )
        self.save_miner_history()

    def load_state(self):
        """Loads the state of the validator from a file."""
        bt.logging.info("Loading validator state.")

        # Load the state of the validator from file.
        state = np.load(self.config.neuron.full_path + "/state.npz")
        self.step = state["step"]
        self.scores = state["scores"]
        self.hotkeys = state["hotkeys"]
        self.load_miner_history()

    def save_miner_history(self):
        for task, tracker in self.performance_trackers.items():
            path = os.path.join(self.config.neuron.full_path, f"{task.TASK_NAME}_performance_history.pkl")
            joblib.dump(tracker, path)

    def load_miner_history(self):
        def load(path):
            if os.path.exists(path):
                bt.logging.info(f"Loading miner performance history from {path}")
                try:
                    tracker: PerformanceTracker = joblib.load(path)
                    tracker.validate_storage_predictions_count()
                    num_miners_history = len(
                        [
                            uid
                            for uid in tracker.prediction_history
                            if len([p for p in tracker.prediction_history[uid] if p != -1]) > 0
                        ]
                    )
                    bt.logging.info(f"Loaded history for {num_miners_history} miners")
                except Exception as e:
                    bt.logging.error(f"Error loading miner performance tracker: {e}")
                    tracker = PerformanceTracker()
            else:
                bt.logging.info(f"No miner performance history found at {path} - starting fresh!")
                tracker = PerformanceTracker()
            return tracker

        for task in self.tasks:
            path = os.path.join(self.config.neuron.full_path, f"{task.TASK_NAME}_performance_history.pkl")
            self.performance_trackers[task] = load(path)

    def init_wandb(self):
        if self.config.wandb.off:
            return

        now = dt.datetime.now()
        self.wandb_run_start = now
        run_id = now.strftime("%Y-%m-%d_%H-%M-%S")
        run_name = f"validator-{self.uid}-{run_id}"
        self.config.run_name = run_name
        self.config.uid = self.uid
        self.config.hotkey = self.wallet.hotkey.ss58_address
        self.config.version = fakenews.__version__
        self.config.type = self.neuron_type

        # Initialize the wandb run for the single project
        bt.logging.info(f"Initializing W&B run")
        try:
            self.wandb_run = wandb.init(
                name=run_name,
                project=self.config.wandb.project,
                entity=self.config.wandb.entity,
                config=self.config,
                dir=self.config.full_path,
            )
        except wandb.Error as e:
            bt.logging.warning(e)
            bt.logging.warning("An error occured while W&B initializing. W&B is disabled.")
            self.config.wandb.off = True
            return

        # Sign the run to ensure it's from the correct hotkey
        signature = self.wallet.hotkey.sign(self.wandb_run.id.encode()).hex()
        self.config.signature = signature
        wandb.config.update(self.config, allow_val_change=True)

        bt.logging.success(f"Started wandb run {run_name}")

    def _validate_tasks(self):
        """
        Validates the tasks provided to the validator.
        """
        if not self.tasks:
            raise ValueError("No tasks provided to the validator.")

        overall_probability = 0.0
        overall_reward_weight = 0.0

        for task in self.tasks:
            overall_reward_weight += task.REWARD_WEIGHT
            overall_probability += task.FORWARD_PROBABILTY

        if overall_probability != 1.0:
            raise TaskDefinitionError(f"Overall probability of tasks should be 1.0, but got {overall_probability}")

        if overall_reward_weight != 1.0:
            raise TaskDefinitionError(f"Overall reward weight of tasks should be 1.0, but got {overall_reward_weight}")
