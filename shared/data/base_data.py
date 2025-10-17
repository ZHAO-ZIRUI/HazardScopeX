import pickle
import struct
import time
from abc import ABC, abstractmethod
from typing import Any
from enum import Enum
from typing_extensions import Self
from multiprocessing.shared_memory import SharedMemory

class TimestampSource(Enum):
    SIM = 'sim'
    OS = 'os'

class BaseData(ABC):

    HEADER_SIZE = 4 # 数据帧头长度
    
    def __init__(self):
        self._raw: Any = None

    @property
    def raw(self) -> Any:
        return self._raw

    def serialize(self) -> bytes:
        serialized_data = pickle.dumps(self)
        data_size = len(serialized_data)
        total_size = data_size + self.HEADER_SIZE 

        data = struct.pack('I', total_size)
        data += serialized_data
        return data

    @classmethod
    def deserialize(cls, data: bytes) -> Self:
        # 解析数据长度
        if len(data) < cls.HEADER_SIZE:
            raise ValueError(f"Invalid data size: {len(data)} < 4")
        size = struct.unpack('I', data[:cls.HEADER_SIZE])[0]

        # 解析数据
        if len(data) < size:
            raise ValueError(f"Invalid data size: {len(data)} < {size}")
        payload = data[cls.HEADER_SIZE:size]
        instance = cls.deserialize(payload)
        return instance

    def to_shm(self, shm: SharedMemory) -> Self:
        data = self.serialize()

        # 检查 SHM 是否已关闭
        if shm.buf is None:
            return self

        # 检查 SHM 大小
        if shm.size < len(data):
            raise ValueError(f'SharedMemory size ({shm.size}) is too small, required {len(data)}')

        # 写入 SHM
        shm.buf[:len(data)] = data
        return self

    @classmethod
    def from_shm(cls, shm: SharedMemory) -> Self:
        while True:
            try:
                result = cls.try_from_shm(shm, default=None)
                if result is None:
                    time.sleep(0.001)
                    continue
                return result

            except (pickle.UnpicklingError, struct.error, ValueError) as e:
                # 数据可能还在写入中或格式错误，继续等待
                time.sleep(0.001)
                continue

    @classmethod
    def try_from_shm(cls, shm: SharedMemory, default: Any = None) -> Any:
        try:
            return cls.deserialize(shm.buf)
        except (pickle.UnpicklingError, EOFError, struct.error, ValueError) as e:
            return default

    @abstractmethod
    def to_ros2(self, frame_id: str = 'world', timestamp_source: TimestampSource = TimestampSource.OS) -> Any:
        """将数据转换为 ROS2 消息"""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_ros2(cls, ros2_msg: Any) -> Self | None:
        """从 ROS2 消息中创建数据"""
        raise NotImplementedError