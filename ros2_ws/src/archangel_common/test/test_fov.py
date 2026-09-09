"""Unit tests for the pure field-of-view geometry."""

import math

from archangel_common.fov import check_fov

HALF_ANGLE = math.radians(30.0)
ALT = 10.0
# Cone ground radius at ALT with HALF_ANGLE, ~5.77 m.
RADIUS = ALT * math.tan(HALF_ANGLE)


def test_directly_overhead_is_full_confidence():
    """Target directly beneath the drone is in view with confidence 1.0."""
    result = check_fov((30.0, -20.0, ALT), (30.0, -20.0, -0.5), HALF_ANGLE)
    assert result.in_view
    assert result.confidence == 1.0


def test_far_outside_cone_not_in_view():
    """Target well beyond the cone radius is not in view."""
    result = check_fov((80.0, -20.0, ALT), (30.0, -20.0, 0.5), HALF_ANGLE)
    assert not result.in_view
    assert result.confidence == 0.0


def test_just_inside_edge_low_confidence():
    """Target near the cone edge is in view with low confidence."""
    offset = RADIUS * 0.95
    result = check_fov((30.0 + offset, -20, ALT), (30.0, -20.0, 0.5), HALF_ANGLE)
    assert result.in_view
    assert 0.0 < result.confidence < 0.1


def test_just_outside_edge_not_in_view():
    """Target just beyond the cone edge is not in view."""
    offset = RADIUS * 1.05
    result = check_fov((30.0 + offset, -20.0, ALT), (30.0, -20.0, 0.5), HALF_ANGLE)
    assert not result.in_view


def test_confidence_falls_with_distance():
    """Confidence decreases as the target moves from center toward the edge."""
    center = check_fov((30.0, -20.0, ALT), (30.0, -20.0, 0.5), HALF_ANGLE)
    offset = RADIUS * 0.5
    mid = check_fov((30.0 + offset, -20.0, ALT), (30.0, -20, 0.5), HALF_ANGLE)
    assert center.confidence > mid.confidence > 0.0


def test_cone_grows_with_altitude():
    """A target out of view at low altitude comes into view when higher up."""
    # 8 m horizontal offset: outside the ~5.8 m radius at 10 m,
    # inside the ~11.5 m radius at 20 m.
    low = check_fov((38.0, -20.0, 10.0), (30.0, -20, 0.5), HALF_ANGLE)
    high = check_fov((38.0, -20.0, 20.0), (30.0, -20.0, 0.5), HALF_ANGLE)
    assert not low.in_view
    assert high.in_view


def test_on_ground_sees_nothing():
    """Zero or negative altitude yields no detection."""
    result = check_fov((30.0, -20.0, 0.0), (30.0, -20.0, 0.5), HALF_ANGLE)
    assert not result.in_view
