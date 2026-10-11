#!/usr/bin/env python3
"""
Keyboard Teleop untuk TR Mecanum Robot
Requirement Final Project ITS Robocon 2027 - TR poin (b)

Node ini membaca input keyboard secara real-time dan mengirim
Twist message ke /cmd_vel untuk menggerakkan robot mecanum.

Kontrol:
    w / s       : maju / mundur
    a / d       : strafe kiri / kanan (khas mecanum!)
    q / e       : putar kiri / kanan (yaw)
    space       : stop (semua kecepatan 0)
    + / -       : naik / turunkan kecepatan
    Ctrl+C      : keluar
"""

import sys
import termios
import tty

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


# ============================================================
# KONFIGURASI KECEPATAN
# ============================================================
LINEAR_SPEED = 0.3       # m/s — kecepatan maju/mundur
STRAFE_SPEED = 0.3       # m/s — kecepatan geser samping (mecanum)
ANGULAR_SPEED = 0.8      # rad/s — kecepatan putar
SPEED_STEP = 0.1         # kenaikan/penurunan tiap tekan + / -
MIN_SPEED = 0.05         # batas bawah
MAX_SPEED = 1.0          # batas atas (biar gak nabrak)


# ============================================================
# KEYBOARD HANDLER — baca 1 tombol tanpa perlu Enter
# ============================================================
class KeyboardReader:
    """Baca input keyboard raw mode (tanpa perlu Enter)."""

    def __init__(self):
        self._fd = sys.stdin.fileno()
        self._old_settings = termios.tcgetattr(self._fd)

    def __enter__(self):
        tty.setraw(self._fd)
        return self

    def __exit__(self, *args):
        termios.tcsetattr(
            self._fd, termios.TCSADRAIN, self._old_settings
        )

    def read_key(self):
        """Baca 1 karakter dari keyboard (blocking)."""
        return sys.stdin.read(1)


# ============================================================
# NODE ROS 2
# ============================================================
class KeyboardTeleop(Node):
    def __init__(self):
        super().__init__('keyboard_teleop')

        # Publisher ke /cmd_vel
        self._publisher = self.create_publisher(Twist, '/cmd_vel', 10)

        # State kecepatan (bisa di-adjust pakai + / -)
        self._linear_speed = LINEAR_SPEED
        self._strafe_speed = STRAFE_SPEED
        self._angular_speed = ANGULAR_SPEED

        self._print_banner()

    def _print_banner(self):
        self.get_logger().info('=' * 50)
        self.get_logger().info('  KEYBOARD TELEOP — TR MECANUM ROBOT')
        self.get_logger().info('=' * 50)
        self.get_logger().info('  w / s  : maju / mundur')
        self.get_logger().info('  a / d  : strafe kiri / kanan')
        self.get_logger().info('  q / e  : putar kiri / kanan')
        self.get_logger().info('  space  : STOP')
        self.get_logger().info('  + / -  : naik / turun kecepatan')
        self.get_logger().info('  Ctrl+C : keluar')
        self.get_logger().info('=' * 50)
        self.get_logger().info(
            f'  Kecepatan: linear={self._linear_speed:.2f} m/s, '
            f'strafe={self._strafe_speed:.2f} m/s, '
            f'angular={self._angular_speed:.2f} rad/s'
        )
        self.get_logger().info('=' * 50)

    def _build_twist(self, key):
        """Convert tombol jadi Twist message."""
        twist = Twist()

        if key == 'w':
            twist.linear.x = self._linear_speed
        elif key == 's':
            twist.linear.x = -self._linear_speed
        elif key == 'a':
            twist.linear.y = self._strafe_speed
        elif key == 'd':
            twist.linear.y = -self._strafe_speed
        elif key == 'q':
            twist.angular.z = self._angular_speed
        elif key == 'e':
            twist.angular.z = -self._angular_speed
        elif key == ' ':
            # Stop — semua nol
            pass

        return twist

    def _adjust_speed(self, key):
        """Naik/turunkan kecepatan pakai + / -."""
        if key == '+':
            delta = SPEED_STEP
        elif key == '-':
            delta = -SPEED_STEP
        else:
            return

        self._linear_speed = max(
            MIN_SPEED, min(MAX_SPEED, self._linear_speed + delta)
        )
        self._strafe_speed = max(
            MIN_SPEED, min(MAX_SPEED, self._strafe_speed + delta)
        )
        self._angular_speed = max(
            MIN_SPEED, min(MAX_SPEED, self._angular_speed + delta)
        )
        self.get_logger().info(
            f'Kecepatan → linear={self._linear_speed:.2f}, '
            f'strafe={self._strafe_speed:.2f}, '
            f'angular={self._angular_speed:.2f}'
        )

    def run(self):
        """Loop utama — baca keyboard & publish."""
        twist = Twist()  # default stop

        with KeyboardReader() as reader:
            while rclpy.ok():
                key = reader.read_key()

                # Ctrl+C
                if key == '\x03':
                    break

                # Adjust kecepatan
                if key in ('+', '-'):
                    self._adjust_speed(key)
                    continue

                # Build & publish twist
                twist = self._build_twist(key)
                self._publisher.publish(twist)

                # Log singkat
                self.get_logger().debug(
                    f'key={repr(key)} → '
                    f'vx={twist.linear.x:.2f}, '
                    f'vy={twist.linear.y:.2f}, '
                    f'wz={twist.angular.z:.2f}'
                )

        # Stop robot saat keluar
        self._publisher.publish(Twist())
        self.get_logger().info('Keluar. Robot di-stop.')


# ============================================================
# MAIN
# ============================================================
def main(args=None):
    rclpy.init(args=args)
    node = KeyboardTeleop()

    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
