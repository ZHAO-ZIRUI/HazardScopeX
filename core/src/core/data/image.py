import carla
import numpy as np
from enum import Enum

from .incoming_data import IncomingData


class Image(IncomingData):
    """
    图像数据
    """

    class Format(Enum):
        BGRA8 = "BGRA8"

    def __init__(
            self,
            size_width: int,
            size_height: int,
            data_format: Format,
            data: np.ndarray,
            *,
            frame_id: int = 0,
            timestamp_sim: float = 0,
    ):
        """
        :param size_width: 图像的宽, 单位: 像素
        :param size_height: 图像的高, 单位: 像素
        :param data_format: 图像的编码格式
        :param data: 以 ``np.ndarray`` 形式存储的数据
        :param frame_id: 帧序号
        :param timestamp_sim: 仿真时间戳
        """
        super().__init__(frame_id, timestamp_sim)
        self._size_width = size_width
        self._size_height = size_height
        self._data_format: Image.Format = data_format
        self._data: np.ndarray = data

    @property
    def size_width(self) -> int:
        """
        :return: 图像的宽, 单位: 像素
        """
        return self._size_width

    @property
    def size_height(self) -> int:
        """
        :return: 图像的高, 单位: 像素
        """
        return self._size_height

    @property
    def data_format(self) -> Format:
        """
        :return: 图像的编码格式
        """
        return self._data_format

    @property
    def data(self) -> np.ndarray:
        """
        :return: 以 ``np.ndarray`` 形式存储的数据
        """
        return self._data

    @classmethod
    def from_carla(cls, data: carla.Image) -> 'Image':
        # 处理图像的原始数据
        img = np.frombuffer(data.raw_data, dtype=np.uint8)
        img = np.reshape(img, (data.height, data.width, 4))
        img = img.copy()    # 执行一次拷贝, 确保图像进入程序内存空间

        # 生成实例
        instance = cls(
            size_width=data.width,
            size_height=data.height,
            data_format=cls.Format.BGRA8,
            data=img,
            frame_id=data.frame,
            timestamp_sim=data.timestamp,
        )
        return instance