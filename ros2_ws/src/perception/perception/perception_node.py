"""Perception node: emits a Detection when the intruder is within the drone's FOV.

Stands in for a real detector by degrading ground-truth pose: the intruder is
only "seen" when it falls inside a downward-facing camera cone under the drone,
and confidence falls off toward the edge of that cone.
"""

import math

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node

from archangel_msgs.msg import Detection, DroneState

# Ground-truth pose bridged from Gazebo is latched/reliable on the Gazebo side;
# a small reliable buffer is a safe match for both inputs.
DEFAULT_QOS = 10


class Perception(Node):
    """Reports the intruder as a Detection when it is inside the drone's camera cone."""

    def __init__(self):
        """Set up parameters, subscriptions, the detection publisher, and timer."""
        super().__init__("perception")

        self.declare_parameter("drone_id", 0)
        self.declare_parameter("fov_half_angle_deg", 30.0)
        self.declare_parameter("rate_hz", 5.0)

        self.drone_id = self.get_parameter("drone_id").value
        self.fov_half_angle = math.radians(self.get_parameter("fov_half_angle_deg").value)
        rate = self.get_parameter("rate_hz").value

        self._drone_pos = None  # (x, y, z) ENU meters
        self._intruder_pos = None  # (x, y, z) ENU meters

        self.create_subscription(
            DroneState, f"/drone_{self.drone_id}/state", self._on_state, DEFAULT_QOS
        )

        self.create_subscription(
            PoseStamped, "/model/intruder/pose", self._on_intruder, DEFAULT_QOS
        )

        self._pub = self.create_publisher(
            Detection, f"/drone_{self.drone_id}/detections", DEFAULT_QOS
        )

        self.create_timer(1.0 / rate, self._check)

        self.get_logger().info(
            f"Perception started for drone_id={self.drone_id}, "
            f"fov_half_angle={math.degrees(self.fov_half_angle):.0f} deg"
        )

    def _on_state(self, msg: DroneState):
        self._drone_pos = (msg.position.x, msg.position.y, msg.position.z)

    def _on_intruder(self, msg: PoseStamped):
        p = msg.pose.position
        self._intruder_pos = (p.x, p.y, p.z)

    def _check(self):
        if self._drone_pos is None or self._intruder_pos is None:
            return

        dx = self._intruder_pos[0] - self._drone_pos[0]
        dy = self._intruder_pos[1] - self._drone_pos[1]
        horizontal = math.hypot(dx, dy)

        altitude = self._drone_pos[2]
        if altitude <= 0.0:
            return  # on/under the ground: nothing to see

        # Ground radius of the downward cone at this altitude.
        fov_radius = altitude * math.tan(self.fov_half_angle)
        if horizontal > fov_radius:
            return  # intruder outside the field of view

        # Confidence falls off linearly from center (1.0) to the edge (0.0) of the FOV cone.
        confidence = 1.0 - (horizontal / fov_radius) if fov_radius > 0.0 else 0.0

        det = Detection()
        det.header.stamp = self.get_clock().now().to_msg()
        det.header.frame_id = "map"
        det.drone_id = self.drone_id
        det.position.x = self._intruder_pos[0]
        det.position.y = self._intruder_pos[1]
        det.position.z = self._intruder_pos[2]
        det.confidence = float(confidence)
        self._pub.publish(det)


def main(args=None):
    """Start the perception node and spin until interrupted."""
    rclpy.init(args=args)
    node = Perception()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
