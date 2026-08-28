"""Bring up the ROS-side stack: uXRCE-DDS agent, drone_agent, and station.

PX4 SITL is launched separately, e.g.:
    PX4_GZ_WORLD=park make px4_sitl gz_x500
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Build the launch description for the agent and both nodes."""
    drone_id = LaunchConfiguration("drone_id")

    drone_id_arg = DeclareLaunchArgument(
        "drone_id",
        default_value="0",
        description="Drone id passed to both drone_agent and station.",
    )

    # uXRCE-DDS agent: the PX4 <-> ROS 2 bridge. Must be up before PX4
    # connects; starting it here means it is ready as the stack comes up.
    agent = ExecuteProcess(
        cmd=["MicroXRCEAgent", "udp4", "-p", "8888"],
        output="screen",
    )

    drone_agent = Node(
        package="drone_agent",
        executable="agent",
        name="drone_agent",
        output="screen",
        parameters=[{"drone_id": drone_id}],
    )

    station = Node(
        package="station",
        executable="station",
        name="station",
        output="screen",
        parameters=[{"drone_id": drone_id}],
    )

    return LaunchDescription([drone_id_arg, agent, drone_agent, station])
