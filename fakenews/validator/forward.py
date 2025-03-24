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

import time
from contextlib import suppress

import bittensor as bt
import wandb

from fakenews.base.validator import BaseValidatorNeuron
from fakenews.utils import uids
from fakenews.validator.reward import RewardCalculator
from fakenews.validator.task import ValidatorTask, select_task


async def forward(self: BaseValidatorNeuron):
    miner_uids = uids.get_random_uids(self, k=self.config.neuron.sample_size)
    bt.logging.info(f"Miners: {miner_uids.tolist()}")
    axons = [self.metagraph.axons[uid] for uid in miner_uids]

    if len(miner_uids) == 0:
        bt.logging.info("No miners available")
        return

    task: ValidatorTask = select_task(self.tasks)
    bt.logging.info(f"Selected task: {task.TASK_NAME}")

    try:
        synapse, labels = await task.prepare_synapse()
    except BaseException as e:
        bt.logging.error(f"Failed to prepare synapse: {e}")
        return

    start = time.perf_counter()
    responses = await self.dendrite(
        axons=axons,
        synapse=synapse,
        deserialize=True,
        timeout=task.TIMEOUT,
    )

    # Log the results for monitoring purposes.
    bt.logging.info(f"Received responses in {time.perf_counter() - start:.2f} seconds: {responses}")

    # Adjust the scores based on responses from miners.
    rewards, calculating_metadata = RewardCalculator.get_rewards(
        labels=labels,
        axons=axons,
        uids=miner_uids,
        responses=responses,
        performance_trackers=self.performance_trackers,
        current_task=task,
    )

    bt.logging.info(f"Scored responses: {rewards.tolist()}")

    self.update_scores(rewards, miner_uids)
    self.save_miner_history()

    if not self.config.wandb.off:
        wandb_logging_context = {
            "rewards": rewards.tolist(),
            "rewards_calculating_metadata": calculating_metadata,
            "miner_uids": miner_uids.tolist(),
            "scores": self.scores.tolist(),
            "responses": responses,
            "labels": labels,
            "task_metadata": task.metadata(),
        }
        with suppress(Exception):
            wandb.log(wandb_logging_context)

    await task.save_dataset()
