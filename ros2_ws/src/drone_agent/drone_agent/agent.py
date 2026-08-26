"""drone_agent node: PX4 telemetry reporting plus offboard waypoint following."""

import math

import rclpy
from px4_msgs.msg import (
    BatteryStatus,
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleCommand,
    VehicleLocalPosition,
    VehicleStatus,
)
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from archangel_msgs.msg import DroneState, MissionCommand

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

# Mission-following tuning.
CRUISE_ALTITUDE = 10.0  # meters above launch
REACHED_RADIUS = 2.0  # meters; within this of a waypoint counts as reached
CONTROL_RATE_HZ = 10.0  # offboard heartbeat + setpoint stream rate

# Internal mission phases (distinct from the DroneState status enum).
PHASE_IDLE = 0
PHASE_ARM = 1
PHASE_TAKEOFF = 2
PHASE_ENROUTE = 3
PHASE_LOITER = 4


class DroneAgent(Node):
    """Reports PX4 telemetry as DroneState and flies missions via offboard control."""

    def __init__(self):
        """Set up parameters, PX4 pub/sub, and the state and control timers."""
        super().__init__("drone_agent")

        self.declare_parameter("drone_id", 0)
        self.drone_id = self.get_parameter("drone_id").value

        # Cached telemetry.
        self._position = None  # (x, y, z) ENU meters
        self._position_ned = None  # (x, y, z) NED meters, as PX4 reports
        self._battery = 0.0
        self._px4_status = DroneState.IDLE

        # Mission state.
        self._waypoints = []  # list of (x, y) ENU targets
        self._wp_index = 0
        self._phase = PHASE_IDLE
        self._offboard_ticks = 0  # setpoints streamed before mode switch

        # --- PX4 telemetry subscriptions (out) ---
        self.create_subscription(
            VehicleLocalPosition, "/fmu/out/vehicle_local_position_v1", self._on_position, PX4_QOS
        )
        self.create_subscription(
            VehicleStatus, "/fmu/out/vehicle_status_v1", self._on_status, PX4_QOS
        )
        self.create_subscription(
            BatteryStatus, "/fmu/out/battery_status_v1", self._on_battery, PX4_QOS
        )

        # --- Mission input ---
        self.create_subscription(
            MissionCommand, f"/drone_{self.drone_id}/mission", self._on_mission, 10
        )

        # --- PX4 command publishers (in) ---
        self._offboard_pub = self.create_publisher(
            OffboardControlMode, "/fmu/in/offboard_control_mode", PX4_QOS
        )
        self._setpoint_pub = self.create_publisher(
            TrajectorySetpoint, "/fmu/in/trajectory_setpoint", PX4_QOS
        )
        self._command_pub = self.create_publisher(
            VehicleCommand, "/fmu/in/vehicle_command", PX4_QOS
        )

        # --- DroneState output ---
        self._state_pub = self.create_publisher(DroneState, f"/drone_{self.drone_id}/state", 10)

        # Timers: state at 2 Hz, offboard control loop at 10 Hz.
        self.create_timer(0.5, self._publish_state)
        self.create_timer(1.0 / CONTROL_RATE_HZ, self._control_loop)

        self.get_logger().info(f"drone_agent started for drone_id={self.drone_id}")

    # ------------------------------------------------------------------
    # Telemetry callbacks
    # ------------------------------------------------------------------
    def _on_position(self, msg: VehicleLocalPosition):
        # PX4 is NED; keep both frames (NED for setpoints, ENU for reporting).
        self._position_ned = (msg.x, msg.y, msg.z)
        self._position = (msg.x, msg.y, -msg.z)

    def _on_battery(self, msg: BatteryStatus):
        # remaining is already a 0.0-1.0 fraction in PX4.
        self._battery = float(msg.remaining)

    def _on_status(self, msg: VehicleStatus):
        self._px4_status = self._map_status(msg)

    def _on_mission(self, msg: MissionCommand):
        if msg.drone_id != self.drone_id:
            return
        self._waypoints = [(wp.position.x, wp.position.y) for wp in msg.waypoints]
        self._wp_index = 0
        self._offboard_ticks = 0
        self._phase = PHASE_ARM if self._waypoints else PHASE_IDLE
        self.get_logger().info(f"mission {msg.mission_id}: {len(self._waypoints)} waypoints")

    def _map_status(self, msg: VehicleStatus) -> int:
        """Map PX4 arming_state / nav_state onto the DroneState status enum."""
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
        return DroneState.LOITERING

    # ------------------------------------------------------------------
    # Offboard control loop (runs continuously at CONTROL_RATE_HZ)
    # ------------------------------------------------------------------
    def _control_loop(self):
        if self._phase == PHASE_IDLE or self._position_ned is None:
            return

        # Always stream the heartbeat + a setpoint while a mission is active,
        # or PX4 rejects/drops offboard mode.
        self._publish_offboard_heartbeat()

        if self._phase == PHASE_ARM:
            # Stream setpoints briefly before commanding the mode switch.
            self._publish_setpoint(self._current_target_ned())
            self._offboard_ticks += 1
            if self._offboard_ticks >= 10:
                self._engage_offboard()
                self._arm()
                self._phase = PHASE_TAKEOFF
            return

        if self._phase == PHASE_TAKEOFF:
            # Climb to cruise altitude above the launch point.
            self._publish_setpoint(
                (self._position_ned[0], self._position_ned[1], -CRUISE_ALTITUDE)
            )
            if abs(-self._position_ned[2] - CRUISE_ALTITUDE) < REACHED_RADIUS:
                self._phase = PHASE_ENROUTE
            return

        if self._phase == PHASE_ENROUTE:
            self._publish_setpoint(self._current_target_ned())
            if self._reached_current_waypoint():
                self._wp_index += 1
                if self._wp_index >= len(self._waypoints):
                    self._phase = PHASE_LOITER
            return

        if self._phase == PHASE_LOITER:
            # Hold at the final waypoint indefinitely.
            self._publish_setpoint(self._current_target_ned(final=True))
            return

    def _current_target_ned(self, final=False):
        """Return the current waypoint as an NED setpoint at cruise altitude."""
        idx = len(self._waypoints) - 1 if final else self._wp_index
        idx = max(0, min(idx, len(self._waypoints) - 1))
        x_enu, y_enu = self._waypoints[idx]
        # ENU (x=E, y=N, z=Up) -> PX4 NED (x=N, y=E, z=Down).
        return (y_enu, x_enu, -CRUISE_ALTITUDE)

    def _reached_current_waypoint(self) -> bool:
        tx, ty, _ = self._current_target_ned()
        px, py, _ = self._position_ned
        return math.hypot(tx - px, ty - py) < REACHED_RADIUS

    # ------------------------------------------------------------------
    # PX4 command helpers
    # ------------------------------------------------------------------
    def _publish_offboard_heartbeat(self):
        msg = OffboardControlMode()
        msg.timestamp = self._now_us()
        msg.position = True
        msg.velocity = False
        msg.acceleration = False
        msg.attitude = False
        msg.body_rate = False
        self._offboard_pub.publish(msg)

    def _publish_setpoint(self, ned):
        msg = TrajectorySetpoint()
        msg.timestamp = self._now_us()
        msg.position = [float(ned[0]), float(ned[1]), float(ned[2])]
        msg.yaw = 0.0
        self._setpoint_pub.publish(msg)

    def _engage_offboard(self):
        self._send_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, param1=1.0, param2=6.0)

    def _arm(self):
        self._send_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=1.0)

    def _send_command(self, command, param1=0.0, param2=0.0):
        msg = VehicleCommand()
        msg.timestamp = self._now_us()
        msg.command = command
        msg.param1 = param1
        msg.param2 = param2
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        self._command_pub.publish(msg)

    def _now_us(self) -> int:
        return int(self.get_clock().now().nanoseconds / 1000)

    # ------------------------------------------------------------------
    # DroneState output
    # ------------------------------------------------------------------
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
        msg.status = self._mission_status()
        self._state_pub.publish(msg)

    def _mission_status(self) -> int:
        """Report status from the mission phase, falling back to PX4 telemetry."""
        if self._phase in (PHASE_ARM, PHASE_TAKEOFF):
            return DroneState.TAKING_OFF
        if self._phase == PHASE_ENROUTE:
            return DroneState.EN_ROUTE
        if self._phase == PHASE_LOITER:
            return DroneState.LOITERING
        return self._px4_status


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
