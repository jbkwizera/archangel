"""Integration test: the perception -> detections topic path is wired correctly.

Launches the perception and station nodes, injects a synthetic drone-state and
intruder-pose placing the drone over the intruder (no PX4/Gazebo), and asserts a
Detection is published on the drone's detections topic. This checks node wiring;
the field-of-view geometry itself is unit-tested in archangel_common.
"""

import time
import unittest

import launch
import launch_ros
import launch_testing
import pytest
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node

from archangel_msgs.msg import Detection, DroneState

DRONE_ID = 0
INTRUDER_XY = (30.0, -20.0)
CRUISE_ALT = 10.0


@pytest.mark.launch_test
def generate_test_description():
    """Launch perception and station for the test."""
    perception = launch_ros.actions.Node(
        package="perception",
        executable="perception",
        name="perception",
        parameters=[{"drone_id": DRONE_ID, "min_detection_interval_s": 0.0}],
    )
    station = launch_ros.actions.Node(
        package="station",
        executable="station",
        name="station",
        parameters=[{"drone_id": DRONE_ID}],
    )
    return (
        launch.LaunchDescription([perception, station, launch_testing.actions.ReadyToTest()]),
        {},
    )


class InjectorNode(Node):
    """Publishes synthetic drone state and intruder pose; collects detections."""

    def __init__(self):
        """Set up the injector's publishers, subscription, and publish timer."""
        super().__init__("test_injector")
        self.detections = []

        self._state_pub = self.create_publisher(
            DroneState,
            f"/drone_{DRONE_ID}/state",
            10,
        )
        self._intruder_pub = self.create_publisher(
            PoseStamped,
            "/model/intruder/pose",
            10,
        )
        self.create_subscription(
            Detection,
            f"/drone_{DRONE_ID}/detections",
            self._on_detection,
            10,
        )
        self.create_timer(0.1, self._publish_inputs)

    def _publish_inputs(self):
        # Drone hovering at cruise altitude directly over the intruder.
        state = DroneState()
        state.header.stamp = self.get_clock().now().to_msg()
        state.drone_id = DRONE_ID
        state.position.x = INTRUDER_XY[0]
        state.position.y = INTRUDER_XY[1]
        state.position.z = CRUISE_ALT
        state.status = DroneState.LOITERING
        self._state_pub.publish(state)

        intruder = PoseStamped()
        intruder.header.stamp = self.get_clock().now().to_msg()
        intruder.header.frame_id = "park"
        intruder.pose.position.x = INTRUDER_XY[0]
        intruder.pose.position.y = INTRUDER_XY[1]
        intruder.pose.position.z = 0.5
        self._intruder_pub.publish(intruder)

    def _on_detection(self, msg: Detection):
        self.detections.append(msg)


class TestDetectionIntegration(unittest.TestCase):
    """Assert a detection is produced when the drone is over the intruder."""

    @classmethod
    def setUpClass(cls):
        """Initialize the ROS client library for the test class."""
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        """Shut down the ROS client library after the test class completes."""
        rclpy.shutdown()

    def setUp(self):
        """Create the synthetic injector node."""
        self.node = InjectorNode()

    def tearDown(self):
        """Destroy the synthetic injector node after each test."""
        self.node.destroy_node()

    def test_detection_when_overhead(self):
        """Injecting an overhead drone position produces a Detection on the detections topic."""
        deadline = time.time() + 10.0
        while time.time() < deadline and not self.node.detections:
            rclpy.spin_once(self.node, timeout_sec=0.1)

        self.assertTrue(self.node.detections, "no Detection was published within the timeout")
        det = self.node.detections[0]
        self.assertEqual(det.drone_id, DRONE_ID)
        self.assertAlmostEqual(det.position.x, INTRUDER_XY[0], delta=0.1)
        self.assertAlmostEqual(det.position.y, INTRUDER_XY[1], delta=0.1)
