# sim_assets

Gazebo simulation worlds, models, and launch assets for the Archangel
project.

## Worlds

### `worlds/park.sdf`

A 200m × 200m flat park environment used for early simulation and testing.

**Contents:**
- Flat terrain plane, 200m × 200m
- Sun (directional light) and sky
- 10 tree obstacles (Oak/Pine mix) and 2 rock obstacles (Falling Rock 1),
  from OpenRobotics' Fuel model library, spread across the terrain
- Station marker: a 4m × 4m orange pad

**Station coordinate:** `(0, 0, 0)` — the world origin. Also the drone's
default spawn point. A ~30m radius around it is kept clear of trees/rocks.

## Intruder

Launch: `ros2 launch sim_assets park_with_intruder.launch.py`

Spawns a red 1m cube named `intruder`, position set by `config/intruder.yaml`
(default `x=30.0, y=-20.0, z=0.0`). Override per-run:

## Flying PX4 in the park world

PX4 loads worlds by name from `PX4-Autopilot/Tools/simulation/gz/worlds/`.
Symlink `park.sdf` there once (repo stays the source of truth):

```bash
ln -sf ~/ws/src/ros2_ws/src/sim_assets/worlds/park.sdf \
  ~/PX4-Autopilot/Tools/simulation/gz/worlds/park.sdf
```

Then launch PX4 SITL in it:

```bash
PX4_GZ_WORLD=park make px4_sitl gz_x500
```

