import carla
import numpy as np
from enum import Enum

from .simulator_output import SimulatorOutput


class Image(SimulatorOutput):
    """
    图像数据
    """

    class Format(Enum):
        BGRA8 = "BGRA8"
        RGBA8 = "RGBA8"
        ARGB32 = "ARGB32"

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

    def reformat(self, new_format: Format) -> 'Image':
        """
        将图像转换为新的编码格式

        :param new_format: 目标编码格式
        :return: 转换后的图像
        """
        if self._data_format == new_format:
            return self

        # 如果格式为 8 位 int, 则统一转换为 BGRA8
        if self._data_format.value.endswith('8'):
            img = self._reformat_uint8_to_bgra8()
        else:
            raise NotImplementedError(f"Unsupported format conversion from {self._data_format}")

        # 向目标格式转换
        if new_format == Image.Format.BGRA8:
            return img
        elif new_format == Image.Format.RGBA8:
            new_data = img._data[:, :, [2, 1, 0, 3]]
            return Image(
                size_width=img._size_width,
                size_height=img._size_height,
                data_format=Image.Format.RGBA8,
                data=new_data,
                frame_id=img.frame_id,
                timestamp_sim=img.timestamp_sim,
            )
        elif new_format == Image.Format.ARGB32:
            a = img._data[:, :, 3].astype(np.uint32)
            r = img._data[:, :, 2].astype(np.uint32)
            g = img._data[:, :, 1].astype(np.uint32)
            b = img._data[:, :, 0].astype(np.uint32)
            new_data = (a << 24) | (r << 16) | (g << 8) | b
            return Image(
                size_width=img._size_width,
                size_height=img._size_height,
                data_format=Image.Format.ARGB32,
                data=new_data,
                frame_id=img.frame_id,
                timestamp_sim=img.timestamp_sim,
            )
        else:
            raise NotImplementedError(f"Unsupported format conversion to {new_format}")

    def _reformat_uint8_to_bgra8(self) -> 'Image':
        if self._data_format == Image.Format.BGRA8:
            return self
        elif self._data_format == Image.Format.RGBA8:
            new_data = self._data[:, :, [2, 1, 0, 3]]
            return Image(
                size_width=self._size_width,
                size_height=self._size_height,
                data_format=Image.Format.BGRA8,
                data=new_data,
                frame_id=self.frame_id,
                timestamp_sim=self.timestamp_sim,
            )
        else:
            raise NotImplementedError(f"Unsupported format conversion from {self._data_format} to BGRA8")

    def to_pygame_surface(self):
        """
        将图像转换为 Pygame 的 Surface 对象

        :return: ``pygame.Surface`` 对象
        """
        import pygame

        # 统一转为 RGBA8 三维数组
        img = self if self._data_format == Image.Format.RGBA8 else self.reformat(Image.Format.RGBA8)

        # 使用 frombuffer + convert_alpha，确保 Surface 拥有正确的像素格式与 alpha
        width, height = img.size_width, img.size_height
        buf = img._data.tobytes(order='C')
        surface = pygame.image.frombuffer(buf, (width, height), 'RGBA').convert_alpha()
        return surface

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