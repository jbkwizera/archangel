"""Setuptools configuration for the station package."""

import os
from glob import glob

from setuptools import find_packages, setup

package_name = "station"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="jbkwizera",
    maintainer_email="jeanbaptistekwi@gmail.com",
    description="Ground station node: mission coordination and drone tasking.",
    license="TODO: License declaration",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "station = station.station_node:main",
        ],
    },
)
