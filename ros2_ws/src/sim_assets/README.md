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
