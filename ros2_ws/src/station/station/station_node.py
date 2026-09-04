"""Station node: publishes a hardcoded lawnmower patrol mission to a drone."""

import rclpy
from geometry_msgs.msg import Point
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from archangel_msgs.msg import Detection, MissionCommand, Waypoint

# Latching QoS so a drone_agent that subscribes after the mission is
# published still receives the last mission (robust to launch order).
LATCHING_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)

CRUISE_ALTITUDE = 10.0  # meters; z carried in each waypoint

# Lawnmower sweep over the central park area: travel in x, step in y, repeat.
# Kept within the terrain and clear of the tree ring, and passes over the
# middle where a target may be placed.
SWEEP_WAYPOINTS = [
    (-30.0, -30.0),
    (30.0, -30.0),
    (30.0, -10.0),
    (-30.0, -10.0),
    (-30.0, 10.0),
    (30.0, 10.0),
    (30.0, 30.0),
    (-30.0, 30.0),
]


class Station(Node):
    """Publishes a fixed lawnmower patrol mission to a target drone on startup."""

    def __init__(self):
        """Set up the drone_id parameter and the latched mission publisher."""
        super().__init__("station")

        self.declare_parameter("drone_id", 0)
        self.drone_id = self.get_parameter("drone_id").value

        self._pub = self.create_publisher(
            MissionCommand,
            f"/drone_{self.drone_id}/mission",
            LATCHING_QOS,
        )

        # Publish shortly after startup so discovery can settle first.
        self._timer = self.create_timer(2.0, self._publish_mission)
        self._sent = False

        # Detections received from perception, kept in memory for later use
        # (dedup, reporting, or triggering a response in the coordination phase).
        self._detections = []
        self.create_subscription(
            Detection, f"/drone_{self.drone_id}/detections", self._on_detection, 10
        )

        self.get_logger().info(f"Station started, with task drone_id={self.drone_id}")

    def _publish_mission(self):
        """Publish a hardcoded lawnmower patrol mission to the target drone."""
        if self._sent:
            return

        msg = MissionCommand()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        msg.mission_id = 1
        msg.drone_id = self.drone_id
        msg.waypoints = [self._waypoint(x, y) for x, y in SWEEP_WAYPOINTS]
        self._pub.publish(msg)
        self._sent = True
        self.get_logger().info(
            f"Published patrol: {len(msg.waypoints)} waypoints to drone_{self.drone_id}"
        )

    def _waypoint(self, x: float, y: float) -> Waypoint:
        """Build a Waypoint at the given x, y at cruise altitude."""
        wp = Waypoint()
        wp.position = Point(x=float(x), y=float(y), z=CRUISE_ALTITUDE)
        wp.hold_time = 0.0
        return wp

    def _on_detection(self, msg: Detection):
        """Record and log a detection reported by a drone."""
        self._detections.append(msg)
        p = msg.position
        stamp = msg.header.stamp
        self.get_logger().info(
            f"Detection #{len(self._detections)} from drone_{msg.drone_id}: "
            f"pos=({p.x:.1f}, {p.y:.1f}, {p.z:.1f}) "
            f"confidence={msg.confidence:.2f} "
            f"t={stamp.sec}.{stamp.nanosec:09d}"
        )


def main(args=None):
    """Start the station node and spin until interrupted."""
    rclpy.init(args=args)
    node = Station()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
