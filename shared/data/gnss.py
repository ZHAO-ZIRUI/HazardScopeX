import carla
import numpy as np
from pathlib import Path
from typing import TYPE_CHECKING
from typing_extensions import Self

from shared.data import SimulatorOutput, TimestampSource


if TYPE_CHECKING:
    from sensor_msgs.msg import NavSatFix as ROS2NavSatFix

class Gnss(SimulatorOutput):
    """
    GNSS 数据
    """
    DTYPE = np.dtype([
        ('latitude', np.float64),
        ('longitude', np.float64),
        ('altitude', np.float64),
    ])

    def __init__(self, sim_frame: int, sim_timestamp: float, latitude: float, longitude: float, altitude: float):
        super().__init__(sim_frame, sim_timestamp)
        self._raw = np.array((latitude, longitude, altitude), dtype=self.DTYPE)

    @property
    def latitude(self) -> float:
        """纬度, 遵循 OpenDRIVE 坐标系定义, 单位: 度"""
        return float(self._raw['latitude'])

    @property
    def longitude(self) -> float:
        """经度, 遵循 OpenDRIVE 坐标系定义, 单位: 度"""
        return float(self._raw['longitude'])

    @property
    def altitude(self) -> float:
        """海拔高度, 遵循 OpenDRIVE 坐标系定义, 单位: 米"""
        return float(self._raw['altitude'])

    @classmethod
    def from_carla(cls, carla_input: carla.GnssMeasurement) -> Self:
        return cls(
            sim_frame=carla_input.frame,
            sim_timestamp=carla_input.timestamp,
            latitude=carla_input.latitude,
            longitude=carla_input.longitude,
            altitude=carla_input.altitude,
        )

    def to_ros2(self, frame_id: str = 'world', ros_message_type: type = None, timestamp_source: TimestampSource = TimestampSource.OS) -> "ROS2NavSatFix":
        from sensor_msgs.msg import NavSatFix as ROS2NavSatFix
        from builtin_interfaces.msg import Time

        if ros_message_type is None:
            ros_message_type = ROS2NavSatFix
        assert ros_message_type.__name__ == 'NavSatFix', \
            f"Unsupported ROS2 message type: {ros_message_type.__name__} for Gnss data"

        # 获取时间戳并转换为 ROS2 Time 格式
        timestamp = self.sim_timestamp if timestamp_source == TimestampSource.SIM else self.os_timestamp
        stamp = Time()
        stamp.sec = int(timestamp)
        stamp.nanosec = int((timestamp - stamp.sec) * 1e9)

        # 组装 ROS2 消息
        msg = ROS2NavSatFix()
        msg.header.stamp = stamp
        msg.header.frame_id = frame_id
        msg.latitude = self.latitude
        msg.longitude = self.longitude
        msg.altitude = self.altitude
        return msg

    @classmethod
    def from_ros2(cls, ros2_msg: "ROS2NavSatFix") -> Self:
        raise NotImplementedError

    def to_file(self, file_path: str | Path) -> Self:
        raise NotImplementedError