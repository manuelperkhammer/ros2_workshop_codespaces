#!/usr/bin/env python3
"""Drive the turtle towards whatever goal is currently published.

This is the *output* half of the workshop example, and the first node that
subscribes to anything. It listens to two topics and publishes one:

    /goal_pose     (geometry_msgs/Point)  <- where we want to be
    /turtle1/pose  (turtlesim/Pose)       <- where we actually are
    /turtle1/cmd_vel (geometry_msgs/Twist) -> how to move

Note that it has no idea a keyboard exists. That is the point of topics: the
goal could come from a keyboard, a planner, or a rosbag and this node would
not know the difference.
"""

import math

from geometry_msgs.msg import Point, Twist
import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose


def normalize_angle(angle):
    """Wrap an angle into [-pi, pi].

    Without this the turtle happily spins the long way round: an error of
    +350 degrees is really -10 degrees.
    """
    return math.atan2(math.sin(angle), math.cos(angle))


class TurtleController(Node):

    def __init__(self):
        super().__init__('turtle_controller')

        # Gains and limits as parameters, so they can be tuned live with
        #   ros2 param set /turtle_controller linear_gain 3.0
        self.declare_parameter('linear_gain', 1.5)
        self.declare_parameter('angular_gain', 6.0)
        self.declare_parameter('max_linear_speed', 2.0)
        self.declare_parameter('max_angular_speed', 4.0)
        self.declare_parameter('goal_tolerance', 0.1)
        self.declare_parameter('control_rate', 20.0)

        # Two subscriptions. Each one hands incoming messages to a callback.
        self.goal_sub = self.create_subscription(
            Point, '/goal_pose', self.on_goal, 10)
        self.pose_sub = self.create_subscription(
            Pose, '/turtle1/pose', self.on_pose, 10)

        self.cmd_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)

        # Latest message from each topic. None means "nothing received yet",
        # which is a state the control loop has to handle.
        self.goal = None
        self.pose = None
        self.at_goal = False

        rate = self.get_parameter('control_rate').value
        self.timer = self.create_timer(1.0 / rate, self.control_loop)

        self.get_logger().info('turtle_controller ready, waiting for /goal_pose')

    # -- callbacks: keep them short, just store the data -------------------

    def on_goal(self, msg):
        self.goal = msg

    def on_pose(self, msg):
        self.pose = msg

    # -- the control loop, on its own timer --------------------------------

    def control_loop(self):
        """Compute and publish one velocity command.

        Runs at a fixed rate regardless of how fast messages arrive.

        Doing the maths here rather than inside a callback means the turtle
        gets a steady stream of commands even if the goal only changes when
        somebody presses a key.
        """
        if self.goal is None or self.pose is None:
            return

        dx = self.goal.x - self.pose.x
        dy = self.goal.y - self.pose.y
        distance = math.hypot(dx, dy)

        cmd = Twist()

        if distance < self.get_parameter('goal_tolerance').value:
            # Close enough: publishing an all-zero Twist stops the turtle.
            self.cmd_pub.publish(cmd)
            if not self.at_goal:
                self.get_logger().info('goal reached')
                self.at_goal = True
            return

        self.at_goal = False

        heading_error = normalize_angle(math.atan2(dy, dx) - self.pose.theta)

        # Proportional control: command a speed in proportion to the error.
        angular = self.get_parameter('angular_gain').value * heading_error
        linear = self.get_parameter('linear_gain').value * distance

        # Turn first, drive second. Scaling the forward speed down while the
        # turtle is badly aimed stops it driving big loops around the goal.
        linear *= max(0.0, math.cos(heading_error))

        cmd.linear.x = self.clamp(linear, self.get_parameter('max_linear_speed').value)
        cmd.angular.z = self.clamp(angular, self.get_parameter('max_angular_speed').value)
        self.cmd_pub.publish(cmd)

    @staticmethod
    def clamp(value, limit):
        return min(max(value, -limit), limit)


def main(args=None):
    rclpy.init(args=args)     # open this process's connection to the ROS graph
    node = TurtleController()  # __init__ does all the setup; nothing runs yet

    try:
        # Hand control to ROS. From here on, rclpy calls our subscription
        # callbacks and timer itself -- this line does not return until the
        # node is told to stop.
        rclpy.spin(node)
    except KeyboardInterrupt:
        # Ctrl-C is the normal way to stop a node, not an error condition.
        # Without this except, spin() lets the interrupt turn into a
        # traceback instead of a clean exit.
        pass
    finally:
        # Runs on both a clean stop and Ctrl-C, so cleanup always happens.
        node.destroy_node()  # release the node's publisher, subscriptions, timer
        if rclpy.ok():
            # Ctrl-C may already have shut the context down by this point;
            # calling shutdown() a second time raises, hence the guard.
            rclpy.shutdown()


if __name__ == '__main__':
    main()
