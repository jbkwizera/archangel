from setuptools import find_packages, setup

package_name = 'coordination'

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
    description='Multi-drone coordination logic (centralized in phase one, decentralized later).',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)
