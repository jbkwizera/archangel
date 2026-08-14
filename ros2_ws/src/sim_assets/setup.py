from setuptools import find_packages, setup

package_name = 'sim_assets'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='jbkwizera',
    maintainer_email='jeanbaptistekwi@gmail.com',
    description='Gazebo simulation worlds, models, and launch assets for the Archangel project.',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)
