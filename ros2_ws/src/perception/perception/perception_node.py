"""Perception node: emits a Detection when the intruder is within the drone's FOV.

Stands in for a real detector by degrading ground-truth pose: the intruder is
only "seen" when it falls inside a downward-facing camera cone under the drone,
and confidence falls off toward the edge of that cone.
"""

import math

import rclpy
from archangel_common.fov import check_fov
from archangel_common.logging import event_str
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
        self.declare_parameter("min_detection_interval_s", 2.0)

        self.drone_id = self.get_parameter("drone_id").value
        self.fov_half_angle = math.radians(self.get_parameter("fov_half_angle_deg").value)
        rate = self.get_parameter("rate_hz").value
        self._min_interval = self.get_parameter("min_detection_interval_s").value

        self._last_publish = None

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
            event_str(
                "perception_start",
                drone_id=self.drone_id,
                fov_half_angle_deg=math.degrees(self.fov_half_angle),
            )
        )

    def _on_state(self, msg: DroneState):
        self._drone_pos = (msg.position.x, msg.position.y, msg.position.z)

    def _on_intruder(self, msg: PoseStamped):
        p = msg.pose.position
        self._intruder_pos = (p.x, p.y, p.z)

    def _check(self):
        if self._drone_pos is None or self._intruder_pos is None:
            return

        result = check_fov(self._drone_pos, self._intruder_pos, self.fov_half_angle)
        if not result.in_view:
            return
        confidence = result.confidence

        # Throttle: cap the rate while a target stays in view, so continuous
        # visibility doesn't flood downstream. Once the intruder can move and
        # Detection carries more state, prefer emitting on meaningful change
        # (position/appearance delta) rather than a fixed time cap.
        now = self.get_clock().now()
        if self._last_publish is not None:
            elapsed = (now - self._last_publish).nanoseconds * 1e-9
            if elapsed < self._min_interval:
                return
        self._last_publish = now

        det = Detection()
        det.header.stamp = self.get_clock().now().to_msg()
        det.header.frame_id = "map"
        det.drone_id = self.drone_id
        det.position.x = self._intruder_pos[0]
        det.position.y = self._intruder_pos[1]
        det.position.z = self._intruder_pos[2]
        det.confidence = float(confidence)
        self._pub.publish(det)

        self.get_logger().info(
            event_str(
                "detection_published",
                drone_id=self.drone_id,
                x=det.position.x,
                y=det.position.y,
                z=det.position.z,
                confidence=det.confidence,
            )
        )


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
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
