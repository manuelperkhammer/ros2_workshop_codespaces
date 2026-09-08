from glob import glob

from setuptools import find_packages, setup

package_name = 'turtle_goal'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Without this line the launch file is not installed and
        # `ros2 launch turtle_goal ...` cannot find it.
        ('share/' + package_name + '/launch', glob('launch/*.launch.xml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Manuel Perkhammer',
    maintainer_email='manuel.perkhammer@tum.de',
    description='ROS 2 intro workshop: steer a goal by keyboard, '
                'let a controller drive the turtle there.',
    license='Apache-2.0',
    entry_points={
        # Each line here becomes a `ros2 run turtle_goal <name>` command.
        'console_scripts': [
            'goal_publisher = turtle_goal.goal_publisher:main',
            'turtle_controller = turtle_goal.turtle_controller:main',
            'goal_marker = turtle_goal.goal_marker:main',
        ],
    },
)
