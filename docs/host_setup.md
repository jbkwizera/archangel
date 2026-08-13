# Host Setup — Docker on Ubuntu 26.04

This document covers the one-time host setup required before any container-based
work in this repo (ROS 2 Jazzy, Gazebo Harmonic, PX4 SITL, all of which run
inside an Ubuntu 24.04 container).

## Host environment

- Host OS: Ubuntu 26.04
- GPU: NVIDIA GeForce MX250 (2 GB VRAM)
- Driver version: 580.173.02
- CUDA version (driver-reported): 13.0

## 1. Install Docker Engine

Installed from Docker's official apt repository (not the Ubuntu-maintained
`docker.io` package).

```bash
# Remove any conflicting packages
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
  sudo apt-get remove $pkg
done

# Add Docker's official GPG key and apt repo
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

# Install Docker Engine
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify
sudo docker run hello-world
```

Docker's apt repo did not need any codename pinning — Ubuntu 26.04's
`VERSION_CODENAME` resolved and the install succeeded normally.

## 2. Enable non-root Docker access

```bash
sudo usermod -aG docker $USER
newgrp docker   # applies the new group to the current shell without logout

# Verify — should succeed with no sudo and no permission error
docker run hello-world
```

**Note:** membership in the `docker` group is equivalent to passwordless root
on the host (a container can mount and modify the host filesystem as root).
Acceptable for this single-user dev machine; would need reconsideration on a
shared or production host.

## 3. Install the NVIDIA Container Toolkit (GPU passthrough)

```bash
# Add the NVIDIA Container Toolkit apt repo
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update

# Install
sudo apt-get install -y nvidia-container-toolkit

# Wire it into Docker's runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Installed version: `nvidia-container-toolkit 1.20.0-1`.

### Verify GPU passthrough

```bash
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi
```

The `12.6.0-base-ubuntu24.04` tag pulled and ran successfully on the first
attempt — no substitution needed despite the host driver reporting CUDA 13.0.
Container output matched the host's `nvidia-smi` (same MX250, same driver
version), confirming passthrough works.

## 4. Verify X11 (GUI) passthrough

```bash
xhost +local:docker
docker run --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix \
  ubuntu:24.04 bash -c "apt-get update && apt-get install -y x11-apps && xeyes"
```

Confirmed working — the `xeyes` window appeared on the host desktop.

**Notes on the output of this command:**
- Verbose `apt-get install` output (~40 packages) is expected on a bare
  `ubuntu:24.04` image, which ships with nothing preinstalled.
- `debconf: unable to initialize frontend...` warnings are harmless — the
  container has no `TERM` set, so `debconf` falls back to non-interactive
  mode automatically.
- `invoke-rc.d: policy-rc.d denied execution of start` is also harmless and
  expected — Ubuntu container images deliberately block services from
  auto-starting during package installs.

This confirms the mechanism that Gazebo will later use to render its window
from inside the ROS 2 development container.

## Result

All setup steps verified successfully:

- [x] Docker Engine installed via official apt repo
- [x] Non-root Docker access (`docker run hello-world` without `sudo`)
- [x] NVIDIA Container Toolkit installed; GPU passthrough verified
- [x] X11 passthrough verified (`xeyes` rendered on host display)
- [x] Setup documented (this file)
