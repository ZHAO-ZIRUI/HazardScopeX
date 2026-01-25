import carla
import numpy as np
from pathlib import Path
from typing import TYPE_CHECKING
from typing_extensions import Self

from shared.data import SimulatorOutput
from shared.define import TimestampSource


if TYPE_CHECKING:
    from rosgraph_msgs.msg import Clock as ROS2Clock
    from builtin_interfaces.msg import Time as ROS2Time

class Clock(SimulatorOutput):
    """
    时钟数据
    """

    def __init__(self, sim_frame: int, sim_timestamp: float):
        super().__init__(sim_frame, sim_timestamp)

   
    @classmethod
    def from_carla(cls, carla_input: carla.WorldSnapshot) -> Self:
        return cls(
            sim_frame=carla_input.frame,
            sim_timestamp=carla_input.timestamp.elapsed_seconds,
        )

    def to_ros2(self, ros_message_type: type = None, timestamp_source: TimestampSource = TimestampSource.OS) -> "ROS2Clock":
        from rosgraph_msgs.msg import Clock as ROS2Clock
        from builtin_interfaces.msg import Time as ROS2Time

        if ros_message_type is None:
            ros_message_type = ROS2Clock
        assert ros_message_type.__name__ == 'Clock' or ros_message_type.__name__ == 'Time', \
            f"Unsupported ROS2 message type: {ros_message_type.__name__} for Clock data"
        
         # 获取时间戳并转换为 ROS2 Time 格式
        timestamp = self.sim_timestamp if timestamp_source == TimestampSource.SIM else self.os_timestamp
        stamp = ROS2Time()
        stamp.sec = int(timestamp)
        stamp.nanosec = int((timestamp - stamp.sec) * 1e9)
        if ros_message_type.__name__ == 'Clock':
            msg = ROS2Clock()
            msg.clock = stamp
            return msg
        elif ros_message_type.__name__ == 'Time':
            return stamp

    @classmethod
    def from_ros2(cls, ros2_msg: any) -> Self:
        raise NotImplementedError

    def to_file(self, file_path: str | Path) -> Self:
        raise NotImplementedError