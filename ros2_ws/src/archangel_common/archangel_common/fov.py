"""Pure field-of-view geometry for the downward-facing detection camera.

Kept free of ROS types so it can be unit-tested directly: given the drone and
target positions and the camera cone half-angle, decide whether the target is
in view and with what confidence.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class FovResult:
    """Outcome of a field-of-view check."""

    in_view: bool
    confidence: float


def check_fov(
    drone_xyz: tuple[float, float, float],
    target_xyz: tuple[float, float, float],
    half_angle_rad: float,
) -> FovResult:
    """Check whether target is inside the drone's downward camera cone.

    The cone's ground radius grows with altitude: radius = altitude *
    tan(half_angle). A target within that radius (measured horizontally) is in
    view, with confidence falling linearly from 1.0 at the center to 0.0 at the
    edge. A non-positive altitude sees nothing.
    """
    altitude = drone_xyz[2]
    if altitude <= 0.0:
        return FovResult(in_view=False, confidence=0.0)

    dx = target_xyz[0] - drone_xyz[0]
    dy = target_xyz[1] - drone_xyz[1]
    horizontal = math.hypot(dx, dy)

    fov_radius = altitude * math.tan(half_angle_rad)
    if fov_radius <= 0.0 or horizontal > fov_radius:
        return FovResult(in_view=False, confidence=0.0)

    confidence = 1.0 - (horizontal / fov_radius)
    return FovResult(in_view=True, confidence=confidence)
