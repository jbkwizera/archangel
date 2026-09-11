#!/usr/bin/env bash
# Kill all simulation processes (PX4, Gazebo, DDS agent) and
# confirm a clean slate.
set -u

echo "Stopping simulation processes..."
pkill -9 -f "gz sim"         2>/dev/null
pkill -9 -f "px4"            2>/dev/null
pkill -9 -f "MicroXRCEAgent" 2>/dev/null
sleep 3

leftover=$(ps aux | grep -E 'gz sim|px4|MicroXRCE' | grep -v grep)
if [ -z "$leftover" ]; then
    echo "Clean: no simulation processes running."
else
    echo "WARNING: processes still alive:"
    echo "$leftover"
    exit 1
fi

