import carla
import numpy as np
import cv2
from pathlib import Path
from enum import Enum
from typing import TYPE_CHECKING
from typing_extensions import Self

from shared.data import SimulatorOutput
from shared.define import TimestampSource


if TYPE_CHECKING:
    from sensor_msgs.msg import Image as ROS2Image

class Image(SimulatorOutput):
    """
    图像数据
    """

    class Format(Enum):
        BGRA8 = 'BGRA8'

    def __init__(
        self, 
        sim_frame: int, 
        sim_timestamp: float, 
        image: np.ndarray, 
        width: int, 
        height: int, 
        format: Format
    ):
        super().__init__(sim_frame, sim_timestamp)
        self._raw = image
        self._width = width
        self._height = height
        self._format = format

    @property
    def width(self) -> int:
        """图像宽度, 单位: 像素"""
        return self._width

    @property
    def height(self) -> int:
        """图像高度, 单位: 像素"""
        return self._height

    @property
    def format(self) -> Format:
        """图像格式"""
        return self._format

    @classmethod
    def from_carla(cls, carla_input: carla.Image) -> Self:
        # 处理图像的原始数据
        img = np.frombuffer(carla_input.raw_data, dtype=np.uint8)
        img = np.reshape(img, (carla_input.height, carla_input.width, 4))
        img = img.copy()    # 执行一次拷贝, 确保图像进入程序内存空间

        # 创建Image对象
        return cls(
            sim_frame=carla_input.frame,
            sim_timestamp=carla_input.timestamp,
            image=img,
            width=carla_input.width,
            height=carla_input.height,
            format=cls.Format.BGRA8,
        )

    def to_ros2(self, frame_id: str = 'world', ros_message_type: type = None, timestamp_source: TimestampSource = TimestampSource.OS) -> "ROS2Image":
        from sensor_msgs.msg import Image as ROS2Image
        from builtin_interfaces.msg import Time

        if ros_message_type is None:
            ros_message_type = ROS2Image
        assert ros_message_type.__name__ == 'Image', f"Unsupported ROS2 message type: {ros_message_type.__name__} for Image data"

        # 获取时间戳并转换为 ROS2 Time 格式
        timestamp = self.sim_timestamp if timestamp_source == TimestampSource.SIM else self.os_timestamp
        stamp = Time()
        stamp.sec = int(timestamp)
        stamp.nanosec = int((timestamp - stamp.sec) * 1e9)

        # 组装 ROS2 消息
        msg = ROS2Image()
        msg.header.stamp = stamp
        msg.header.frame_id = frame_id
        msg.width = self.width
        msg.height = self.height
        msg.encoding = 'bgra8'
        msg.is_bigendian = False
        msg.step = self.width * 4
        # 使用 memoryview + cast 直接暴露底层连续缓冲区, 避免多余拷贝
        # 此处直接操作 msg 的 _data 属性, 而不是 msg.data, 因为 msg.data 会进行额外的格式转换
        msg._data = memoryview(self._raw).cast('B')
        return msg

    @classmethod
    def from_ros2(cls, ros2_msg: "ROS2Image") -> Self:
        return cls(
            sim_frame=ros2_msg.header.stamp,
            sim_timestamp=ros2_msg.header.stamp,
            image=ros2_msg.data,
            width=ros2_msg.width,
            height=ros2_msg.height,
            format=cls.Format.BGRA8,
        )

    def to_file(self, file_path: str | Path) -> Self:
        file_path = Path(file_path) if isinstance(file_path, str) else file_path
        cv2.imwrite(file_path, self._raw)
        return self