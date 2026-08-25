"""Setuptools configuration for the perception package."""

from setuptools import find_packages, setup

package_name = "perception"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="jbkwizera",
    maintainer_email="jeanbaptistekwi@gmail.com",
    description="Perception nodes: sensor processing and detection.",
    license="TODO: License declaration",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [],
    },
)
