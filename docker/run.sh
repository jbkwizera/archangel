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

# Build the image if it doesn't exist yet, passing host UID/GID so files
# created in the container are owned by the host user, not root.
if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
    echo "Image '$IMAGE_NAME' not found locally — building it now..."
    docker build \
        --build-arg USER_UID="$(id -u)" \
        --build-arg USER_GID="$(id -g)" \
        --build-arg USERNAME="$(whoami)" \
        -t "$IMAGE_NAME" \
        -f "$SCRIPT_DIR/Dockerfile" \
        "$SCRIPT_DIR"
fi

# Allow the container to draw on the host's X server.
xhost +local:docker > /dev/null 2>&1 || true

GPU_FLAGS=()
if command -v nvidia-smi > /dev/null 2>&1; then
    GPU_FLAGS=(--gpus all)
fi

docker run -it --rm \
    --name "$CONTAINER_NAME" \
    "${GPU_FLAGS[@]}" \
    -e DISPLAY="$DISPLAY" \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v "$REPO_ROOT":/home/"$(whoami)"/ws/src \
    -w /home/"$(whoami)"/ws \
    "$IMAGE_NAME" \
    /bin/bash
