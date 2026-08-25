"""Launch park.sdf and spawn the intruder marker at a configurable pose."""

import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Build the launch description for the park simulation with an intruder.

    Starts Gazebo with the ``park.sdf`` world and spawns a static-free box
    model named ``intruder`` at a configurable pose. The spawn pose defaults
    to the values in ``config/intruder.yaml`` and can be overridden at launch
    time via the ``intruder_x``, ``intruder_y``, and ``intruder_z`` launch
    arguments, e.g.::

        ros2 launch sim_assets park_with_intruder.launch.py intruder_x:=5.0

    Returns:
        launch.LaunchDescription: The launch description declaring the pose
        arguments, the Gazebo process, and the intruder spawn node.
    """
    pkg_share = get_package_share_directory("sim_assets")
    world_path = os.path.join(pkg_share, "worlds", "park.sdf")
    config_path = os.path.join(pkg_share, "config", "intruder.yaml")

    with open(config_path) as f:
        defaults = yaml.safe_load(f)["intruder"]

    x_arg = DeclareLaunchArgument(
        "intruder_x", default_value=str(defaults["x"]), description="Intruder X position (m)"
    )
    y_arg = DeclareLaunchArgument(
        "intruder_y", default_value=str(defaults["y"]), description="Intruder Y position (m)"
    )
    z_arg = DeclareLaunchArgument(
        "intruder_z", default_value=str(defaults["z"]), description="Intruder Z position (m)"
    )

    gz_sim = ExecuteProcess(
        cmd=["gz", "sim", world_path],
        output="screen",
    )

    spawn_intruder = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name",
            "intruder",
            "-x",
            LaunchConfiguration("intruder_x"),
            "-y",
            LaunchConfiguration("intruder_y"),
            "-z",
            LaunchConfiguration("intruder_z"),
            "-string",
            (
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
                "</model>"
                "</sdf>"
            ),
        ],
        output="screen",
    )

    return LaunchDescription(
        [
            x_arg,
            y_arg,
            z_arg,
            gz_sim,
            spawn_intruder,
        ]
    )
