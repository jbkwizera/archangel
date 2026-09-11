# Multi-Vehicle SITL: Findings

How to run multiple PX4 SITL instances in one Gazebo world, each reachable
from ROS 2 under its own namespace. Verified on this project's stack
(PX4 v1.18, ROS 2 Jazzy, Gazebo Harmonic) with two x500 quadrotors.

## Mechanism

PX4 has a built-in instance system. The `-i <N>` flag on the PX4 binary
gives each vehicle a unique instance number, which drives its MAVLink system
ID, UDP port offsets, and — the key part for ROS 2 — its DDS namespace.

One instance hosts the Gazebo server; the rest connect to it in standalone
mode. A single uXRCE-DDS agent bridges all instances.

## Resetting between runs

Multi-instance runs leave several processes alive (PX4 instances, the Gazebo
server, the DDS agent). A leftover Gazebo server is especially disruptive: a
new launch attaches to the stale world instead of starting fresh. Always
reset to a clean slate before a new run.

`scripts/reset.sh` does this and verifies it worked:

```bash
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
```

Make it executable once (`chmod +x scripts/reset.sh`), then run it before
each session:

```bash
~/ws/src/scripts/reset.sh
```

It exits non-zero and lists survivors if anything refuses to die, so a clean
exit is a real confirmation, not an assumption.

## Running two vehicles

Reset first (see above):

```bash
~/ws/src/scripts/reset.sh
```

The PX4 binary must be built (`make px4_sitl` once, no target, if needed).
Run each command in its own terminal.

**Terminal 1 — DDS agent (start first):**

```bash
MicroXRCEAgent udp4 -p 8888
```

**Terminal 2 — instance 1 (hosts Gazebo and the world):**

```bash
cd ~/PX4-Autopilot
PX4_SYS_AUTOSTART=4001 PX4_GZ_WORLD=park PX4_SIM_MODEL=gz_x500 \
  ./build/px4_sitl_default/bin/px4 -i 1
```

Wait for the drone to spawn and the `pxh>` prompt.

**Terminal 3 — instance 2 (standalone, joins the existing Gazebo):**

```bash
cd ~/PX4-Autopilot
PX4_GZ_STANDALONE=1 PX4_GZ_WORLD=park PX4_SYS_AUTOSTART=4001 \
  PX4_GZ_MODEL_POSE="5,0" PX4_SIM_MODEL=gz_x500 \
  ./build/px4_sitl_default/bin/px4 -i 2
```

Key points:
- Only instance 1 starts Gazebo. Instances 2+ set `PX4_GZ_STANDALONE=1` to
  connect to the running server instead of starting their own.
- Every instance still needs `PX4_GZ_WORLD=park` so the standalone instances
  join the correct world. Omitting it on instance 2 leaves it stuck at
  "Waiting for Gazebo world...".
- `PX4_GZ_MODEL_POSE="x,y"` spawns each vehicle at a distinct spot so they do
  not overlap.

## Namespaced topics

Each instance publishes under `/px4_<N>/`. The message-type suffixes (`_v1`,
etc.) match this project's firmware. Confirm from a sourced terminal:

```bash
source ~/ws/src/ros2_ws/install/setup.bash
ros2 topic list | grep vehicle_local_position
# /px4_1/fmu/out/vehicle_local_position_v1
# /px4_2/fmu/out/vehicle_local_position_v1
```

A single agent bridges all instances — no per-instance agent needed.

## What this means for drone_agent

`drone_agent` currently subscribes and publishes to un-namespaced
`/fmu/in/...` and `/fmu/out/...` paths, which only works for one vehicle. For
multi-vehicle, every `/fmu/...` path becomes `/px4_<N>/fmu/...`, keyed by the
vehicle's instance number. The node needs a parameter for that namespace (or
derives it from its drone id).

## Quirks worth knowing

- **QGC vehicle numbering is offset.** PX4 skips MAVLink system ID 1, so
  instance 1 gets system ID 2 and shows in QGroundControl as "Vehicle 2",
  instance 2 as "Vehicle 3", and so on. Instance number and QGC label differ
  by one.
- **"Preflight Fail: no heading reference"** on a freshly spawned instance is
  a transient estimator-startup state. It clears once the EKF converges (a
  few seconds); the vehicle then arms normally. Only a concern if it
  persists, in which case give the vehicle more settle time before arming.
- **Vehicles look stacked in QGroundControl's map** even when separated in
  Gazebo. SITL instances share a GPS home reference, so the map overlays
  them; their local positions (the `vehicle_local_position` topics) are
  correctly distinct. Work in local ENU coordinates, not the QGC map, to see
  the separation. Distinct `PX4_HOME_LAT`/`PX4_HOME_LON` per instance would
  separate them on the map if ever needed.
- **`ros2 topic echo` reports "message type is invalid"** until the workspace
  is sourced (`source install/setup.bash`), because decoding needs the
  px4_msgs definitions. `ros2 topic list` works without sourcing because it
  only needs topic names, not types — so a working list plus a failing echo
  is the signature of an unsourced shell, not a build problem.

## Verified

- Two instances spawn and run in one shared world.
- Topics namespace cleanly to `/px4_1/` and `/px4_2/`.
- One agent bridges both.
- Both vehicles arm and take off independently (confirmed at ~2.5 m each,
  read from their own `/px4_<N>/.../vehicle_local_position_v1` topics).
