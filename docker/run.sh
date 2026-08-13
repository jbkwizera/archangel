#!/usr/bin/env bash
# Launches the Archangel development container with:
#   - the repo mounted as a volume at ~/ws/src (inside the container)
#   - X11 forwarding for GUI apps (Gazebo, RViz, etc.)
#   - GPU passthrough (if an NVIDIA GPU is available on the host)
#   - the host user's UID/GID, for clean file ownership on mounted files
#
# Usage: ./docker/run.sh

set -euo pipefail

IMAGE_NAME="archangel-dev"
CONTAINER_NAME="archangel-dev"

# Resolve repo root (parent of this script's directory) so this works
# regardless of the caller's current working directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# PX4-Autopilot is expected as a sibling directory to this repo, e.g.:
#   ~/dev/Archangel/        <- REPO_ROOT
#   ~/dev/PX4-Autopilot/    <- PX4_ROOT
# It's a large, independently-versioned external codebase (built from
# source, not installed as a package), so it lives outside this repo's
# git history and is mounted in rather than vendored - see docs/host_setup.md.
PX4_ROOT="$(dirname "$REPO_ROOT")/PX4-Autopilot"

# Always (re)build. Docker's own layer cache makes a no-op rebuild fast —
# only layers whose instructions or context actually changed get re-run —
# so this is cheap in the common case, and it avoids silently running a
# stale image after the Dockerfile has been edited (bit us once already:
# gz wasn't found because a prior image was reused instead of rebuilt).
docker build \
    --build-arg USER_UID="$(id -u)" \
    --build-arg USER_GID="$(id -g)" \
    --build-arg USERNAME="$(whoami)" \
    -t "$IMAGE_NAME" \
    -f "$SCRIPT_DIR/Dockerfile" \
    "$SCRIPT_DIR"

# Allow the container to draw on the host's X server.
xhost +local:docker > /dev/null 2>&1 || true

GPU_FLAGS=()
if command -v nvidia-smi > /dev/null 2>&1; then
    GPU_FLAGS=(--gpus all)
fi

docker run -it --rm \
    --name "$CONTAINER_NAME" \
    "${GPU_FLAGS[@]}" \
    --network host \
    -e DISPLAY="$DISPLAY" \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v "$REPO_ROOT":/home/"$(whoami)"/ws/src \
    -v "$PX4_ROOT":/home/"$(whoami)"/PX4-Autopilot \
    -w /home/"$(whoami)"/ws \
    "$IMAGE_NAME" \
    /bin/bash
