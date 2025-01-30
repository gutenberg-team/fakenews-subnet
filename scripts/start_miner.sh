#!/bin/bash

set -e

bash scripts/install_env.sh

# Load environment variables from .env file & set defaults
set -a
source miner.env
set +a

REQUIRED_ENV_VARS=(
  "NETUID"
  "SUBTENSOR_NETWORK"
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

PROCESS_NAME="fakenews_miner"

if pm2 list | grep -q "$PROCESS_NAME"; then
  echo "Process '$PROCESS_NAME' is already running. Deleting it..."
  pm2 delete $PROCESS_NAME
fi

source .venv/bin/activate

echo "Starting miner process"

CMD="pm2 start neurons/miner.py --name $PROCESS_NAME --"

# Add mandatory arguments
CMD+=" --netuid $NETUID"
CMD+=" --subtensor.network $SUBTENSOR_NETWORK"
[ -n "$SUBTENSOR_CHAIN_ENDPOINT" ] && CMD+=" --subtensor.chain_endpoint $SUBTENSOR_CHAIN_ENDPOINT"
CMD+=" --wallet.name $WALLET_NAME"
CMD+=" --wallet.hotkey $WALLET_HOTKEY"
CMD+=" --openai_api_key $OPENAI_API_KEY"
CMD+=" --logging.trace"

# Conditionally add optional arguments
[ -n "$AXON_PORT" ] && CMD+=" --axon.port $AXON_PORT"

# Execute the constructed command
eval "$CMD"
