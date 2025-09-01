import struct
import time
import carla
import pickle
from multiprocessing.shared_memory import SharedMemory
from abc import ABC, abstractmethod
from typing_extensions import Self


class IncomingData(ABC):
    """
    来自仿真器的数据
    """

    def __init__(
            self,
            frame_id: int,
            timestamp_sim: float,
    ):
        self.frame_id : int = frame_id
        self.timestamp_sim : float = timestamp_sim
        self.timestamp_os : float = time.time()
        self._data = None

    @classmethod
    @abstractmethod
    def from_carla(cls, data: carla.SensorData) -> Self:
        """
        从 CARLA 的数据帧 ``carla.SensorData`` 中解析数据
        :param data: CARLA Server 返回的数据
        :return: 对象实例
        """
        raise NotImplementedError()

    def serialize(self) -> bytes:
        """
        序列化数据, 用于进程间通信
        :return: 序列化的数据
        """
        serialized_data = pickle.dumps(self)
        data_size = len(serialized_data)
        total_size = data_size + 4

        data = struct.pack('I', total_size)
        data += serialized_data
        return data

    def serialize_to_shm(self, ref_shm: SharedMemory) -> None:
        if not isinstance(ref_shm, SharedMemory):
            raise RuntimeError(f'Reference SharedMemory is required, not {type(ref_shm)}')

        data = self.serialize()

        # 检查 shm 大小
        if ref_shm.size < len(data):
            raise ValueError(f'Reference SharedMemory size ({ref_shm.size}) is too small, required {len(data)}')

        # 写入
        ref_shm.buf[:len(data)] = data
        return

    @classmethod
    def deserialize(cls, data: bytes):
        """
        反序列化数据, 用于进程间通信
        :param data: 数据帧
        :return: 实例
        """
        instance = pickle.loads(data[4:])
        return instance

    @classmethod
    def deserialize_from_shm(cls, shm: SharedMemory) -> Self:
        """
        反序列化数据, 用于进程间通信
        :param shm: 原始数据帧
        :return: 对象实例
        """
        while True:
            try:
                shm_data = bytes(shm.buf[:shm.size])
                
                # 检查数据是否为空
                if not shm_data or len(shm_data) < 4:
                    time.sleep(0.001)
                    continue
                
                # 剪裁出合适的数据大小
                total_size = struct.unpack('I', shm_data[:4])[0]
                data = shm_data[: total_size]


                # 反序列化
                return cls.deserialize(shm_data)
                
            except (pickle.UnpicklingError, struct.error, ValueError) as e:
                # 数据可能还在写入中或格式错误，继续等待
                time.sleep(0.001)
                continue
