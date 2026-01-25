import pickle
import struct
import time
from abc import ABC, abstractmethod
from typing import Any
from pathlib import Path
from typing_extensions import Self
from multiprocessing.shared_memory import SharedMemory

from shared.define import TimestampSource

class BaseData(ABC):

    HEADER_SIZE = 12 # 数据帧头长度: size(4字节 uint32) + frame(8字节 uint64)
    
    def __init__(self):
        self._frame = 0
        self._raw: Any = None

    @property
    def raw(self) -> Any:
        return self._raw

    @property
    def frame(self) -> int:
        return self._frame

    def serialize(self) -> bytes:
        # 序列化格式: [total_size(4字节 uint32)] [frame(8字节 uint64)] [pickle数据...]
        serialized_data = pickle.dumps(self)
        data_size = len(serialized_data)
        total_size = data_size + self.HEADER_SIZE 
        data = struct.pack('<IQ', total_size, self._frame)
        data += serialized_data
        return data

    @classmethod
    def deserialize(cls, data: bytes) -> Self:
        # 解析数据长度和帧号
        if len(data) < cls.HEADER_SIZE:
            raise ValueError(f"Invalid data size: {len(data)} < {cls.HEADER_SIZE}")
        total_size, frame = struct.unpack('<IQ', data[:cls.HEADER_SIZE])

        # 解析数据
        if len(data) < total_size:
            raise ValueError(f"Invalid data size: {len(data)} < {total_size}")
        payload = data[cls.HEADER_SIZE:total_size]
        instance = pickle.loads(payload)
        return instance
    
    @classmethod
    def deserialize_frame_only(cls, data: bytes) -> int | None:
        """
        仅解析帧序号，用于快速检查是否为重复帧
        
        Returns:
            int: 帧序号，如果数据无效则返回 None
        """
        try:
            # 检查最小长度
            if len(data) < cls.HEADER_SIZE:
                return None
            total_size, frame = struct.unpack('<IQ', data[:cls.HEADER_SIZE])
            
            # 验证 total_size 是否合理
            if total_size < cls.HEADER_SIZE:
                return None
            return frame
        except (struct.error, ValueError, TypeError) as e:
            return None

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
    
    @classmethod
    def try_from_shm_frame_only(cls, shm: SharedMemory, default: int | None = None) -> int | None:
        """
        仅从共享内存中提取帧序号，用于快速检查
        
        Returns:
            int: 帧序号，如果数据无效则返回 default
        """
        try:
            # 检查共享内存缓冲区是否有效
            if shm.buf is None:
                return default
            
            # 检查数据长度
            if len(shm.buf) < cls.HEADER_SIZE:
                return default
            frame = cls.deserialize_frame_only(shm.buf)            
            return frame if frame is not None else default
        except (struct.error, ValueError, TypeError, AttributeError) as e:
            return default

    @abstractmethod
    def to_file(self, file_path: str | Path) -> Self:
        """将数据保存到文件"""
        raise NotImplementedError