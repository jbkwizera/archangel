"""drone_agent node: reports drone state from PX4 telemetry as DroneState."""

import rclpy
from px4_msgs.msg import BatteryStatus, VehicleLocalPosition, VehicleStatus
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from archangel_msgs.msg import DroneState

# PX4 publishes /fmu/out/* topics with BEST_EFFORT reliability, VOLATILE
# durability, and a small KEEP_LAST history. A subscriber whose QoS doesn't
# match (e.g. default RELIABLE, or TRANSIENT_LOCAL durability) silently pairs
# with nothing, so these must match PX4's publisher profile exactly.
PX4_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)


class DroneAgent(Node):
    """Subscribes to PX4 telemetry and republishes a unified DroneState at 2 Hz."""

    def __init__(self):
        """Set up parameters, PX4 subscriptions, publisher, and publish timer."""
        super().__init__("drone_agent")

        # drone_id parameter, default 0
        self.declare_parameter("drone_id", 0)
        self.drone_id = self.get_parameter("drone_id").value

        # Latest values cached on receipt; published on a fixed timer.
        self._position = None  # (x, y, z) in ENU metres
        self._battery = 0.0  # fraction 0.0-1.0
        self._status = DroneState.IDLE

        # PX4 subscriptions (BEST_EFFORT QoS required). Topic names use the
        # _v1 suffix that current PX4 firmware publishes.
        self.create_subscription(
            VehicleLocalPosition, "/fmu/out/vehicle_local_position_v1", self._on_position, PX4_QOS
        )
        self.create_subscription(
            VehicleStatus, "/fmu/out/vehicle_status_v1", self._on_status, PX4_QOS
        )
        self.create_subscription(
            BatteryStatus,
            "/fmu/out/battery_status_v1",
            self._on_battery,
            PX4_QOS,
        )

        # Publisher on a drone-specific topic.
        self._pub = self.create_publisher(DroneState, f"/drone_{self.drone_id}/state", 10)

        # 2 Hz publish timer (decoupled from PX4 message arrival rate).
        self.create_timer(0.5, self._publish_state)

        self.get_logger().info(f"drone_agent started for drone_id={self.drone_id}")

    def _on_position(self, msg: VehicleLocalPosition):
        # PX4 is NED (z down); flip z so our DroneState reads altitude-up (ENU).
        self._position = (msg.x, msg.y, -msg.z)

    def _on_battery(self, msg: BatteryStatus):
        # remaining is already a 0.0-1.0 fraction in PX4.
        self._battery = float(msg.remaining)

    def _on_status(self, msg: VehicleStatus):
        self._status = self._map_status(msg)

    def _map_status(self, msg: VehicleStatus) -> int:
        """Map PX4 arming_state / nav_state onto our DroneState status enum."""
        # If not armed, the drone is idle regardless of nav_state.
        if msg.arming_state != VehicleStatus.ARMING_STATE_ARMED:
            return DroneState.IDLE

        ns = msg.nav_state
        if ns == VehicleStatus.NAVIGATION_STATE_AUTO_TAKEOFF:
            return DroneState.TAKING_OFF
        if ns == VehicleStatus.NAVIGATION_STATE_AUTO_LAND:
            return DroneState.LANDING
        if ns == VehicleStatus.NAVIGATION_STATE_AUTO_RTL:
            return DroneState.RETURNING
        if ns == VehicleStatus.NAVIGATION_STATE_AUTO_LOITER:
            return DroneState.LOITERING
        if ns in (
            VehicleStatus.NAVIGATION_STATE_AUTO_MISSION,
            VehicleStatus.NAVIGATION_STATE_OFFBOARD,
        ):
            return DroneState.EN_ROUTE
        # Armed but in some other mode (e.g. manual/position hold on ground).
        return DroneState.LOITERING

    def _publish_state(self):
        msg = DroneState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        msg.drone_id = self.drone_id
        if self._position is not None:
            msg.position.x = float(self._position[0])
            msg.position.y = float(self._position[1])
            msg.position.z = float(self._position[2])
        msg.battery = self._battery
        msg.status = self._status
        self._pub.publish(msg)


def main(args=None):
    """Start the drone_agent node and spin until interrupted."""
    rclpy.init(args=args)
    node = DroneAgent()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
