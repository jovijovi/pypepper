#!/usr/bin/env bash

set -euo pipefail

COMMAND=${1:-}
SERVICE_NAME=${2:-}
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DEV_FILE="${SCRIPT_DIR}/dev.yaml"


function detectComposeCmd() {
  # Prefer the modern plugin command.
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "docker compose"
    return 0
  fi

  # Fallback for legacy Docker Compose v1.
  if command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
    return 0
  fi

  echo ""
}

# Print the usage message
function printHelp() {
  echo "Setting up a development environment out-of-the-box."
  echo
  echo "Usage: "
  echo "  ./dev.sh COMMAND"
  echo
  echo "Commands:"
  echo "  up        Setting up a development environment or a service"
  echo "  down      Shut down the development environment"
  echo "  stop      Stop a service in the development environment"
  echo
  echo "Examples:"
  echo "  ./dev.sh up"
  echo "  ./dev.sh down"
  echo "  ./dev.sh up mysql"
  echo "  ./dev.sh stop mysql"
  echo
  echo "This script auto-detects compose command:"
  echo "  1) docker compose"
  echo "  2) docker-compose"
}

COMPOSE_CMD=$(detectComposeCmd)
if [[ -z "${COMPOSE_CMD}" ]]; then
  echo "Error: neither 'docker compose' nor 'docker-compose' is available." >&2
  exit 1
fi

function compose() {
  ${COMPOSE_CMD} -f "${DEV_FILE}" "$@"
}

echo "## Using compose command: ${COMPOSE_CMD}"

if [[ "${COMMAND}" == "up" ]]; then
  echo "## Creating dev env..."
  if [[ -n "${SERVICE_NAME}" ]]; then
    compose up -d "${SERVICE_NAME}"
  else
    compose up -d
  fi
elif [[ "${COMMAND}" == "down" ]]; then
  echo "## Shutting down dev env..."
  compose down
elif [[ "${COMMAND}" == "stop" ]]; then
  echo "## Stopping service..."
  if [[ -n "${SERVICE_NAME}" ]]; then
    compose stop "${SERVICE_NAME}"
  else
    compose stop
  fi
else
  printHelp
  exit 1
fi

echo "## Done."

if command -v docker >/dev/null 2>&1; then
  docker ps
fi
