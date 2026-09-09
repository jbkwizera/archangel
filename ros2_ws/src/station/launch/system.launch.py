"""Bring up the ROS-side stack against a running PX4/Gazebo simulation.

Starts the uXRCE-DDS agent, spawns the intruder marker, bridges its ground-truth
pose, and runs drone_agent, perception and station.

PX4 SITL is launched separately and must be up first:
    PX4_GZ_WORLD=park make px4_sitl gz_x500

Launch arguments (all optional):
    drone_id                    Drine id shared by all nodes.       (default 0)
    world                       Running Gazebo world to spawn into. (default park)
    intruder_x/y/z              Intruder spawn position, meters.    (from intruder.yaml)
    fov_half_angle_deg          Perception camera cone half-angle.  (default 30)
    min_detection_intervals_s   Min seconds between detections.     (default 2.0)

Example:
    ros2 launch station system.launch.py drone_id:=0 fov_half_angle_deg:=45
"""

import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Intruder model: a red cube that also publishes its own pose on
# /model/intruder/pose, which stands in for real perception.
INTRUDER_SDF = (
    '<sdf version="1.9">'
    '<model name="intruder">'
    "<static>false</static>"
    '<link name="link">'
    '<visual name="visual">'
    "<geometry><box><size>1 1 1</size></box></geometry>"
    "<material>"
    "<ambient>1 0 0 1</ambient>"
    "<diffuse>1 0 0 1</diffuse>"
    "<emissive>0.3 0 0 1</emissive>"
    "</material>"
    "</visual>"
    '<collision name="collision">'
    "<geometry><box><size>1 1 1</size></box></geometry>"
    "</collision>"
    "</link>"
    '<plugin filename="gz-sim-pose-publisher-system" '
    'name="gz::sim::systems::PosePublisher">'
    "<publish_link_pose>false</publish_link_pose>"
    "<publish_model_pose>true</publish_model_pose>"
    "<update_frequency>10</update_frequency>"
    "</plugin>"
    "</model>"
    "</sdf>"
)


def generate_launch_description():
    """Build the full launch description for the ROS-side stack."""
    drone_id = LaunchConfiguration("drone_id")
    world = LaunchConfiguration("world")

    # --- Simulation bridge and world setup ---
    # uXRCE-DDS agent: the PX4 <-> ROS 2 bridge. Must be up before PX4
    # connects; starting it here means it is ready as the stack comes up.
    agent = ExecuteProcess(
        cmd=["MicroXRCEAgent", "udp4", "-p", "8888"],
        output="screen",
    )

    spawn_intruder = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-world",
            world,
            "-name",
            "intruder",
            "-x",
            LaunchConfiguration("intruder_x"),
            "-y",
            LaunchConfiguration("intruder_y"),
            "-z",
            LaunchConfiguration("intruder_z"),
            "-string",
            INTRUDER_SDF,
        ],
    )

    # Ground-truth intruder pose on its own named topic.
    pose_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="intruder_pose_bridge",
        output="screen",
        arguments=["/model/intruder/pose@geometry_msgs/msg/PoseStamped[gz.msgs.Pose"],
    )

    # --- Application nodes ---
    drone_agent = Node(
        package="drone_agent",
        executable="agent",
        name="drone_agent",
        output="screen",
        parameters=[{"drone_id": drone_id}],
    )

    perception = Node(
        package="perception",
        executable="perception",
        name="perception",
        output="screen",
        parameters=[
            {
                "drone_id": drone_id,
                "fov_half_angle_deg": LaunchConfiguration("fov_half_angle_deg"),
                "min_detection_interval_s": LaunchConfiguration("min_detection_interval_s"),
            }
        ],
    )

    station = Node(
        package="station",
        executable="station",
        name="station",
        output="screen",
        parameters=[{"drone_id": drone_id}],
    )

    return LaunchDescription(
        [
            *_declare_arguments(),
            agent,
            spawn_intruder,
            pose_bridge,
            drone_agent,
            perception,
            station,
        ]
    )


def _declare_arguments():
    """Declare all launch arguments, reading intruder defaults from config."""
    sim_assets_share = get_package_share_directory("sim_assets")
    config_path = os.path.join(sim_assets_share, "config", "intruder.yaml")
    with open(config_path) as f:
        intruder = yaml.safe_load(f)["intruder"]

    return [
        DeclareLaunchArgument(
            "drone_id",
            default_value="0",
            description="Drone id shared by all nodes.",
        ),
        DeclareLaunchArgument(
            "world",
            default_value="park",
            description="Name of the running Gazebo world to spawn into.",
        ),
        DeclareLaunchArgument(
            "intruder_x",
            default_value=str(intruder["x"]),
            description="Intruder X spawn position (m).",
        ),
        DeclareLaunchArgument(
            "intruder_y",
            default_value=str(intruder["y"]),
            description="Intruder Y spawn position (m).",
        ),
        DeclareLaunchArgument(
            "intruder_z",
            default_value=str(intruder["z"]),
            description="Intruder Z spawn position (m).",
        ),
        DeclareLaunchArgument(
            "fov_half_angle_deg",
            default_value="30.0",
            description="Perception downward-camera cone half-angle (deg).",
        ),
        DeclareLaunchArgument(
            "min_detection_interval_s",
            default_value="2.0",
            description="Minimum seconds between published detections.",
        ),
    ]
