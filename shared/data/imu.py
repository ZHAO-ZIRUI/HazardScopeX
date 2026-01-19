import carla
import numpy as np
from pathlib import Path
from typing import TYPE_CHECKING
from typing_extensions import Self

from shared.data import SimulatorOutput, TimestampSource


if TYPE_CHECKING:
    from sensor_msgs.msg import Imu as ROS2Imu

class Imu(SimulatorOutput):
    """
    IMU 数据, 包含加速度计、陀螺仪和罗盘数据
    """
    DTYPE = np.dtype([
        ('accelerometer', np.float64, (3,)),
        ('gyroscope', np.float64, (3,)),
        ('compass', np.float64),
    ])

    def __init__(
        self, 
        sim_frame: int, 
        sim_timestamp: float, 
        accelerometer: tuple[float, float, float],
        gyroscope: tuple[float, float, float],
        compass: float,
    ):
        super().__init__(sim_frame, sim_timestamp)
        self._raw = np.array((accelerometer, gyroscope, compass), dtype=self.DTYPE)

    @property
    def accelerometer(self) -> tuple[float, float, float]:
        """加速度计数据 (x, y, z), 单位: m/s²"""
        return tuple(self._raw['accelerometer'])

    @property
    def gyroscope(self) -> tuple[float, float, float]:
        """陀螺仪数据 (x, y, z), 单位: rad/s"""
        return tuple(self._raw['gyroscope'])

    @property
    def compass(self) -> float:
        """罗盘方向, 单位: rad"""
        return float(self._raw['compass'])

    @classmethod
    def from_carla(cls, carla_input: carla.IMUMeasurement) -> Self:
        return cls(
            sim_frame=carla_input.frame,
            sim_timestamp=carla_input.timestamp,
            accelerometer=(
                carla_input.accelerometer.x,
                carla_input.accelerometer.y,
                carla_input.accelerometer.z,
            ),
            gyroscope=(
                carla_input.gyroscope.x,
                carla_input.gyroscope.y,
                carla_input.gyroscope.z,
            ),
            compass=carla_input.compass,
        )

    def to_ros2(self, frame_id: str = 'world', ros_message_type: type = None, timestamp_source: TimestampSource = TimestampSource.OS) -> "ROS2Imu":
        from sensor_msgs.msg import Imu as ROS2Imu
        from builtin_interfaces.msg import Time

        if ros_message_type is None:
            ros_message_type = ROS2Imu
        assert ros_message_type.__name__ == 'Imu', \
            f"Unsupported ROS2 message type: {ros_message_type.__name__} for Imu data"

        # 获取时间戳并转换为 ROS2 Time 格式
        timestamp = self.sim_timestamp if timestamp_source == TimestampSource.SIM else self.os_timestamp
        stamp = Time()
        stamp.sec = int(timestamp)
        stamp.nanosec = int((timestamp - stamp.sec) * 1e9)

        # 组装 ROS2 消息
        msg = ROS2Imu()
        msg.header.stamp = stamp
        msg.header.frame_id = frame_id

        # 加速度计 -> linear_acceleration
        msg.linear_acceleration.x = self.accelerometer[0]
        msg.linear_acceleration.y = self.accelerometer[1]
        msg.linear_acceleration.z = self.accelerometer[2]

        # 陀螺仪 -> angular_velocity
        msg.angular_velocity.x = self.gyroscope[0]
        msg.angular_velocity.y = self.gyroscope[1]
        msg.angular_velocity.z = self.gyroscope[2]

        # orientation 设置为未知 (covariance[0] = -1 表示无效)
        msg.orientation_covariance[0] = -1.0

        return msg

    @classmethod
    def from_ros2(cls, ros2_msg: "ROS2Imu") -> Self:
        raise NotImplementedError

    def to_file(self, file_path: str | Path) -> Self:
        raise NotImplementedError
