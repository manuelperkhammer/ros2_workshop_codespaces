#!/usr/bin/env python3
"""Publish a goal position that you steer with the arrow keys.

This is the *input* half of the workshop example. It owns a single piece of
state -- a goal point somewhere in the turtlesim field -- and publishes it on
the topic ``/goal_pose``. It knows nothing at all about turtles.

Run it in its own terminal, because it needs the keyboard:

    ros2 run turtle_goal goal_publisher
"""

import os
import select
import sys
import termios
import tty

from geometry_msgs.msg import Point
import rclpy
from rclpy.node import Node

# --------------------------------------------------------------------------
# Terminal plumbing. Not ROS, just the least-bad way to read arrow keys from a
# terminal without pulling in a dependency. Read it once, then forget it.
# --------------------------------------------------------------------------

ARROWS = {
    '\x1b[A': 'up',
    '\x1b[B': 'down',
    '\x1b[C': 'right',
    '\x1b[D': 'left',
}


class KeyboardReader:
    """Non-blocking reader for single keypresses, including arrow keys."""

    def __init__(self):
        self._fd = sys.stdin.fileno()
        self._saved = termios.tcgetattr(self._fd)
        # cbreak (not raw): keys arrive immediately and unechoed, but Ctrl-C
        # still generates SIGINT so the node stays killable.
        tty.setcbreak(self._fd)
        self._buf = ''

    def read_keys(self):
        """Return every key pressed since the last call. Never blocks."""
        while select.select([sys.stdin], [], [], 0.0)[0]:
            chunk = os.read(self._fd, 1024).decode(errors='ignore')
            if not chunk:
                break
            self._buf += chunk

        keys, i = [], 0
        while i < len(self._buf):
            if self._buf[i] == '\x1b':
                seq = self._buf[i:i + 3]
                if seq in ARROWS:
                    keys.append(ARROWS[seq])
                    i += 3
                    continue
                if len(self._buf) - i < 3:
                    break  # escape sequence split across reads; wait for more
            keys.append(self._buf[i])
            i += 1

        self._buf = self._buf[i:]
        return keys

    def restore(self):
        termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved)


# --------------------------------------------------------------------------
# The ROS 2 node.
# --------------------------------------------------------------------------

BANNER = """
  Arrow keys : move the goal
  r          : reset the goal to the middle of the field
  q / Ctrl-C : quit
"""


class GoalPublisher(Node):

    def __init__(self):
        super().__init__('goal_publisher')

        # Parameters: values you can change at launch time without touching
        # the code.  ros2 run turtle_goal goal_publisher --ros-args -p step:=0.5
        self.declare_parameter('step', 0.5)          # metres per keypress
        self.declare_parameter('publish_rate', 20.0)  # Hz
        self.step = self.get_parameter('step').value
        rate = self.get_parameter('publish_rate').value

        # A publisher is typed: this one only ever carries Point messages, and
        # only on the topic /goal_pose. The 10 is the queue depth.
        self.publisher = self.create_publisher(Point, '/goal_pose', 10)

        # A timer gives the node a heartbeat. rclpy calls on_timer at `rate` Hz.
        self.timer = self.create_timer(1.0 / rate, self.on_timer)

        self.goal = Point(x=5.5, y=5.5, z=0.0)
        self.keyboard = KeyboardReader()

        self.get_logger().info('goal_publisher ready.' + BANNER)

    def on_timer(self):
        """Drain the keyboard, then publish the goal. Called ~20x a second."""
        for key in self.keyboard.read_keys():
            if key == 'q':
                raise KeyboardInterrupt
            self.apply_key(key)

        self.publisher.publish(self.goal)

    def apply_key(self, key):
        before = (self.goal.x, self.goal.y)

        if key == 'up':
            self.goal.y += self.step
        elif key == 'down':
            self.goal.y -= self.step
        elif key == 'right':
            self.goal.x += self.step
        elif key == 'left':
            self.goal.x -= self.step
        elif key == 'r':
            self.goal.x, self.goal.y = 5.5, 5.5

        # The turtlesim window is roughly 11x11. Keep the goal inside it.
        self.goal.x = min(max(self.goal.x, 0.5), 10.5)
        self.goal.y = min(max(self.goal.y, 0.5), 10.5)

        if (self.goal.x, self.goal.y) != before:
            self.get_logger().info(
                f'goal -> x={self.goal.x:.2f} y={self.goal.y:.2f}')


def main(args=None):
    rclpy.init(args=args)   # open this process's connection to the ROS graph
    node = GoalPublisher()  # __init__ does all the setup; nothing runs yet

    try:
        # Hand control to ROS. From here on, rclpy calls our timer callback
        # itself -- this line does not return until the node is told to stop.
        rclpy.spin(node)
    except KeyboardInterrupt:
        # Ctrl-C is the normal way to stop a node, not an error condition.
        # Without this except, spin() lets the interrupt turn into a
        # traceback instead of a clean exit.
        pass
    finally:
        # Runs on both a clean stop and Ctrl-C, so cleanup always happens.
        node.keyboard.restore()  # give the terminal back its normal input mode
        node.destroy_node()      # release the node's publisher, timer, etc.
        if rclpy.ok():
            # Ctrl-C may already have shut the context down by this point;
            # calling shutdown() a second time raises, hence the guard.
            rclpy.shutdown()


if __name__ == '__main__':
    main()
