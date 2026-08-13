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

## 5. PX4 Autopilot (SITL)

PX4 is a large, independently-versioned codebase built from source (not
installed as an apt package), so it's cloned as a **sibling directory** next
to this repo rather than vendored into it:

```
~/dev/Archangel/          <- this repo
~/dev/PX4-Autopilot/      <- PX4 source, sibling directory
```

### Clone (pinned commit)

```bash
cd ..   # from the repo root, up to its parent directory
git clone https://github.com/PX4/PX4-Autopilot.git --recursive
cd PX4-Autopilot
git log -1 --oneline
```

`--recursive` is required — PX4 depends on several git submodules, and a
non-recursive clone produces a build that fails in confusing ways later.

**Pinned commit:** `bb59c637cd` — "fix(mavlink): synchronize radio status
access (#28194)", `origin/main` at time of cloning.

### Container wiring

`docker/run.sh` mounts the sibling `PX4-Autopilot/` directory into the
container at `~/PX4-Autopilot`, and runs the container with `--network host`
so QGroundControl (running on the host) can reach PX4 SITL's MAVLink stream
(UDP) inside the container without manual port mapping.

### Install PX4 build dependencies

Run once, inside the container, against the mounted PX4 source:

```bash
cd ~/PX4-Autopilot
bash Tools/setup/ubuntu.sh
```

**Known gap:** `ubuntu.sh` did not reliably install `ninja` in this
environment, which caused the build step below to fail with
`ninja: command not found`. This is now fixed permanently by installing
`ninja-build` directly in `docker/Dockerfile`, so it's present in every
container without needing a manual install. (If you're troubleshooting an
older image built before this fix, `sudo apt-get install -y ninja-build`
resolves it for the current container session.)

**Also expected, harmless:** near the end of `ubuntu.sh`, a line installing
the optional Xtensa (ESP32) toolchain fails with
`Tools/setup/ubuntu.sh: line 183: /home//.bashrc: Permission denied`. This
is a bug in the script's `$USER` handling for an unrelated embedded-hardware
toolchain that this project doesn't use (not needed for SITL or the
`gz_x500` target) — safe to ignore.

### Build and run SITL with Gazebo

```bash
make px4_sitl gz_x500
```

This builds PX4 for the `gz_x500` quadcopter target and launches Gazebo with
PX4 SITL attached in one command. On success, PX4 reaches a `pxh>` shell
prompt and a Gazebo window opens showing the x500 quadcopter.

### QGroundControl (host)

QGroundControl runs on the **host**, not the container — it represents the
operator's ground station, separate from the "drone" (PX4 SITL) running
inside the container.

**One-time host prep** (Ubuntu's serial modem manager conflicts with
robotics use of serial/USB ports):

```bash
sudo usermod -aG dialout $USER
sudo systemctl mask --now ModemManager.service
```

Log out and back in (or run `newgrp dialout` in the current shell) for the
new group membership to take effect.

**Download and run** (AppImage, current stable v5.0.8 at time of writing):

```bash
wget https://github.com/mavlink/qgroundcontrol/releases/latest/download/QGroundControl-x86_64.AppImage
chmod +x QGroundControl-x86_64.AppImage
./QGroundControl-x86_64.AppImage
```

**Verified:** with PX4 SITL running in the container (`--network host`
lets QGroundControl reach its MAVLink stream with no manual port mapping),
QGroundControl auto-detected the vehicle within a few seconds — confirmed by
`[commander] Ready for takeoff!` appearing in the PX4 shell once QGC
connected, and by `partner IP: 127.0.0.1` in the PX4 log.

**Flight test**, from the PX4 shell (`pxh>` prompt):

```bash
commander takeoff
# wait for altitude to climb and hold steady in both Gazebo and QGroundControl
commander land
# altitude returns to zero
```

Confirmed: quadcopter took off, held a stable hover (altitude visibly level
in QGroundControl's telemetry), and landed cleanly on command.

## Useful commands for inspecting Docker state

A few commands worth knowing, since containers and their "wiring" (mounts,
network, GPU access) aren't always obvious at a glance:

```bash
docker ps -a                        # every container on this machine, running or stopped
docker top archangel-dev            # processes running inside a specific container
docker inspect archangel-dev        # full config: mounts, network, devices, etc.
docker port archangel-dev           # published port mappings, if any
```

`docker/run.sh` always rebuilds the image before launching (relying on
Docker's layer cache to keep this fast) rather than reusing whatever image
happens to exist locally — this avoids a class of bug where a stale image
gets silently reused after the Dockerfile has changed.

## Result

All setup steps verified successfully:

- [x] Docker Engine installed via official apt repo
- [x] Non-root Docker access (`docker run hello-world` without `sudo`)
- [x] NVIDIA Container Toolkit installed; GPU passthrough verified
- [x] X11 passthrough verified (`xeyes` rendered on host display)
- [x] PX4 Autopilot cloned as a pinned-commit sibling directory
- [x] PX4 SITL builds and runs the `gz_x500` quadcopter in Gazebo
- [x] QGroundControl installed on host and connects to PX4 SITL
- [x] Quadcopter takeoff, hover, and land verified via PX4 shell + QGroundControl telemetry
- [x] Setup documented (this file)
