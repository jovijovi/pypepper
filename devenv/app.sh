#!/usr/bin/env bash

set -e

COMMAND=${1}

# Print the usage message
function printHelp() {
  echo "Run/Stop the app"
  echo
  echo "Usage: "
  echo "  ./app.sh COMMAND"
  echo
  echo "Commands:"
  echo "  up        Run the app"
  echo "  down      Stop the app"
  echo
  echo "Examples:"
  echo "  ./app.sh up"
  echo "  ./app.sh down"
}

if [[ "${COMMAND}" == "up" ]]; then
  echo "## Starting app..."
  docker compose -f app.yaml up -d
elif [[ "${COMMAND}" == "down" ]]; then
  echo "## Stopping app..."
  docker compose -f app.yaml down
else
  printHelp
  exit 1
fi

echo "## Done."

docker ps|grep pypepper
