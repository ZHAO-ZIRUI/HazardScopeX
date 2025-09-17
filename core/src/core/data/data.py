import pickle
import struct
import time
from abc import ABC
from multiprocessing.shared_memory import SharedMemory

from typing_extensions import Self


class Data(ABC):

    def __init__(self):
        pass

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
        反序列化数据, 用于进程间通信. 该方法会阻塞进程, 可以使用 ``try_deserialize_from_shm``
        :param shm: 共享内存实例
        :return: 对象实例
        """
        while True:
            try:
                result = cls.try_deserialize_from_shm(shm, default=None)
                if result is None:
                    time.sleep(0.001)
                    continue
                return result

            except (pickle.UnpicklingError, struct.error, ValueError) as e:
                # 数据可能还在写入中或格式错误，继续等待
                time.sleep(0.001)
                continue

    @classmethod
    def try_deserialize_from_shm(cls, shm: SharedMemory, default: Self | None = None) -> Self:
        """
        以非阻塞方式从 SharedMemory 中反序列化数据
        :param shm: 共享内存实例
        :param default: 解析失败时的返回值, 默认为 ``None``
        :return:
        """
        try:
            view = shm.buf
            header = bytes(view[:4])
            total_size = struct.unpack('I', header)[0]
            payload = bytes(view[: total_size])
            return cls.deserialize(payload)

        except (pickle.UnpicklingError, EOFError, struct.error, ValueError) as e:
            return default