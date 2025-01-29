#!/bin/bash

set -e

bash scripts/install_env.sh

# Load environment variables from .env file & set defaults
set -a
source validator.env
set +a


REQUIRED_ENV_VARS=(
  "NETUID"
  "SUBTENSOR_NETWORK"
  "SUBTENSOR_CHAIN_ENDPOINT"
  "WALLET_NAME"
  "WALLET_HOTKEY"
  "OPENAI_API_KEY"
)

MISSING_VARS=0
for VAR in "${REQUIRED_ENV_VARS[@]}"; do
  if [ -z "${!VAR}" ]; then
    echo "Missing required environment variable: $VAR"
    MISSING_VARS=1
  fi
done

if [ "$MISSING_VARS" = 1 ]; then
  exit 1
fi

PROCESS_NAME="fakenews_validator"

if pm2 list | grep -q "$PROCESS_NAME"; then
  echo "Process '$PROCESS_NAME' is already running. Deleting it..."
  pm2 delete $PROCESS_NAME
fi

source .venv/bin/activate

# if WANDB_API_KEY is set, then we will use wandb for logging
if [ -n "$WANDB_API_KEY" ]; then
  echo "Logging to wandb"
  wandb login $WANDB_API_KEY --relogin
fi

echo "Starting validator process"

#!/bin/bash

# Initialize the base command
CMD="pm2 start neurons/validator.py --name $PROCESS_NAME --"

# Add mandatory arguments
CMD+=" --netuid $NETUID"
CMD+=" --subtensor.network $SUBTENSOR_NETWORK"
CMD+=" --subtensor.chain_endpoint $SUBTENSOR_CHAIN_ENDPOINT"
CMD+=" --wallet.name $WALLET_NAME"
CMD+=" --wallet.hotkey $WALLET_HOTKEY"
CMD+=" --openai_api_key $OPENAI_API_KEY"
CMD+=" --logging.debug"

# Conditionally add optional arguments
[ -n "$WANDB_PROJECT" ] && CMD+=" --wandb.project $WANDB_PROJECT"
[ -n "$WANDB_ENTITY" ] && CMD+=" --wandb.entity $WANDB_ENTITY"

# Execute the constructed command
eval "$CMD"

AUTO_UPDATE_PROCESS_NAME="auto_update_monitor"

if ! pm2 list | grep -q "$AUTO_UPDATE_PROCESS_NAME"; then
  echo "Starting auto-updater process"
  pm2 start scripts/auto_update.sh --name $AUTO_UPDATE_PROCESS_NAME
else
  echo "Auto-updater process is already running"
fi
