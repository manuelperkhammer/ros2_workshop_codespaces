#!/usr/bin/env python3
"""Show the goal in the turtlesim window as a second, non-drawing turtle.

Bonus node for the last part of the workshop. Topics are one-way broadcasts;
*services* are request/response calls, and this node uses three of them:

    /spawn                          create a second turtle
    /<marker>/set_pen               lift its pen so it leaves no trail
    /<marker>/teleport_absolute     move it to the current goal

It is purely cosmetic -- the controller works fine without it.
"""

from geometry_msgs.msg import Point
import rclpy
from rclpy.node import Node
from turtlesim.srv import SetPen, Spawn, TeleportAbsolute


class GoalMarker(Node):

    def __init__(self):
        super().__init__('goal_marker')

        self.declare_parameter('marker_name', 'goal')
        self.name = self.get_parameter('marker_name').value

        # A service client is typed by the service type *and* the service name,
        # exactly like a publisher is typed by message type and topic.
        self.spawn_client = self.create_client(Spawn, '/spawn')
        self.pen_client = self.create_client(SetPen, f'/{self.name}/set_pen')
        self.teleport_client = self.create_client(
            TeleportAbsolute, f'/{self.name}/teleport_absolute')

        self.create_subscription(Point, '/goal_pose', self.on_goal, 10)
        self.last_goal = None

    def setup(self):
        """Spawn the marker turtle and lift its pen. Blocking, runs once."""
        if not self.spawn_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('/spawn not available -- is turtlesim running?')
            return False

        request = Spawn.Request()
        request.x, request.y, request.theta = 5.5, 5.5, 0.0
        request.name = self.name
        if self.call(self.spawn_client, request) is None:
            # Most likely cause: a turtle with this name is already there,
            # because turtlesim was left running from a previous attempt.
            self.get_logger().warning(
                f'could not spawn "{self.name}"; assuming it already exists')

        pen = SetPen.Request()
        pen.off = 1  # 1 = pen up, so the marker draws no trail
        self.pen_client.wait_for_service(timeout_sec=5.0)
        self.call(self.pen_client, pen)

        self.get_logger().info(f'marker turtle "{self.name}" ready')
        return True

    def call(self, client, request):
        """Send a request and wait for the response.

        Fine during one-off setup. Never do this inside a subscription
        callback -- the node cannot spin while it is blocked here, so the
        response it is waiting for can never arrive.
        """
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        return future.result() if future.done() else None

    def on_goal(self, msg):
        goal = (round(msg.x, 3), round(msg.y, 3))
        if goal == self.last_goal:
            return
        self.last_goal = goal

        request = TeleportAbsolute.Request()
        request.x, request.y, request.theta = msg.x, msg.y, 0.0
        # call_async and then ignore the future: fire-and-forget is the right
        # shape inside a callback.
        self.teleport_client.call_async(request)


def main(args=None):
    rclpy.init(args=args)  # open this process's connection to the ROS graph
    node = GoalMarker()    # __init__ only creates the service clients

    try:
        # setup() blocks on /spawn and /set_pen once, up front. Only start
        # spinning if it actually succeeded -- there is nothing useful to do
        # with a marker turtle that was never spawned.
        if node.setup():
            rclpy.spin(node)
    except KeyboardInterrupt:
        # Ctrl-C is the normal way to stop a node, not an error condition.
        # Without this except, spin() lets the interrupt turn into a
        # traceback instead of a clean exit.
        pass
    finally:
        # Runs on both a clean stop and Ctrl-C, so cleanup always happens.
        node.destroy_node()  # release the node's clients and subscription
        if rclpy.ok():
            # Ctrl-C may already have shut the context down by this point;
            # calling shutdown() a second time raises, hence the guard.
            rclpy.shutdown()


if __name__ == '__main__':
    main()
