# Validator Guide

- [Validator Guide](#validator-guide)
  - [Introduction](#introduction)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
      - [OS dependencies](#os-dependencies)
      - [Rust](#rust)
      - [PM2](#pm2)
    - [Clone the repository](#clone-the-repository)
    - [Install dependencies](#install-dependencies)
  - [Validating](#validating)
    - [Environment Variables](#environment-variables)
    - [Running](#running)
  - [Monitoring](#monitoring)
  - [Troubleshooting | Support](#troubleshooting--support)

## Introduction

The Validator is responsible for generating challenges for the Miner to solve. It evaluates solutions submitted by Miners and rewards them based on the quality and correctness of their answers.

## Installation

### Prerequisites

* Ubuntu 20.04
* Python 3.10 [see](#os-dependencies)
* Rust [see](#rust)
* PM2 [see](#pm2)
* OpenAI API key. You should provide your own paid key with access to gpt-4o-mini model. [see](#environment-variables)
* Registered wallet with more than 4096 Stake Weight [see](#environment-variables)
* No GPU required

#### OS dependencies
```bash
sudo apt-get update
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get install -y python3.10 python3.10-venv curl gcc pkg-config make git npm
```

#### Rust
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
export PATH="/root/.cargo/bin:$PATH"
rustup update stable
```

#### PM2
Install [PM2](https://pm2.io/docs/runtime/guide/installation/):

```bash
npm install pm2 -g && pm2 update
```

### Clone the repository
Clone the repository and navigate to the folder.
 
```bash
git clone https://github.com/gutenberg-team/fakenews-subnet.git && cd fakenews-subnet
```

### Install dependencies
Install the necessary dependencies:

```bash 
bash scripts/install_env.sh
```
This step is also included in the validator [running](#running) script. You can perform this step manually to ensure that all dependencies are installed and no errors occur.

## Validating

### Environment Variables

First, create and configure `validator.env` file.
Provide all necessary environment variables as follows:

Bittensor Configuration:
* `NETUID` - Bittensor subnet ID.
* `SUBTENSOR_NETWORK` - Bittensor network name. Options: `finney`, `test`, `local`.
* `SUBTENSOR_CHAIN_ENDPOINT` - Bittensor chain endpoint.

Wallet Configuration:
* `WALLET_NAME` - Coldkey name.
* `WALLET_HOTKEY` - Hotkey name. 
**NOTE:** To act as a validator in this subnet, you must stake more than 4096 TAO.

API Keys:
* `OPENAI_API_KEY` - OpenAI API key. You should provide your own paid key with access to "gpt-4o-mini" model.
* `WANDB_API_KEY` - Optional - Wandb API key for logging.

W&B configuration (Optional):
* `WANDB_ENTITY` - The entity to log to. Default value is `gutenberg-fakenews`. Don't specify this parameter if you want to log to the default entity.
* `WANDB_PROJECT` - The project within entity to log to. Default value is `SN66_Validator`. Don't specify this parameter if you want to log to the default project.

If you don't have a W&B API key, please reach out to the Gutenberg team via Discord in subnet chat and we can provide one. 

Example:
```bash
NETUID=60
SUBTENSOR_NETWORK=finney
SUBTENSOR_CHAIN_ENDPOINT=wss://entrypoint-finney.opentensor.ai:443
WALLET_NAME=default
WALLET_HOTKEY=default
OPENAI_API_KEY=your_openai_api_key
WANDB_API_KEY=your_wandb_api_key
WANDB_ENTITY=gutenberg-fakenews
WANDB_PROJECT=SN66_Validator
```

### Running

You can run your validator with `start_validator.sh`:

```bash
bash scripts/start_validator.sh
```

The signal of successful start is the following message:
```
  ┌────┬────────────────────────┬─────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┬──────────┬──────────┬──────────┬──────────┐
  │ id │ name                   │ namespace   │ version │ mode    │ pid      │ uptime │ ↺    │ status    │ cpu      │ mem      │ user     │ watching │
  ├────┼────────────────────────┼─────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┼──────────┼──────────┼──────────┼──────────┤
  │ 1  │ auto_update_monitor    │ default     │ N/A     │ fork    │ 35908    │ 7m     │ 0    │ online    │ 0%       │ 1.4mb    │ root     │ disabled │
  │ 2  │ fakenews_validator     │ default     │ N/A     │ fork    │ 43644    │ 0s     │ 0    │ online    │ 0%       │ 2.6mb    │ root     │ disabled │
  └────┴────────────────────────┴─────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┴──────────┴──────────┴──────────┴──────────┘
```

**NOTE**: `auto_update_monitor` process is crucial for the validator’s proper operation. Do not stop or remove this process.
It ensures the validator is automatically updated and restarted when a new version is released.

**NOTE**: Some updates may not be applied automatically. Major or breaking changes might require manual actions.
Stay informed by checking the release notes and following the provided instructions.

## Monitoring

You can monitor your validator with PM2:

```bash
pm2 monit
```

or check the logs:

```bash
pm2 logs fakenews-validator
```

## Troubleshooting | Support

- **Logs**:
  - Please see the logs for more details using the following command.
  ```bash
  pm2 logs fakenews-validator
  ```
- **Common Issues**:
  - Missing environment variables.
  - Provided openai api key is invalid or has no access to target model.
  - Connectivity problems.
  - Incorrect wallet configuration | Low wallet stake.

- **Contact Support**:
- [Discord](https://discord.com/channels/799672011265015819/1334536801922060360)
