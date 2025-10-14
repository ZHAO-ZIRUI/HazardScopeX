import carla
import numpy as np
from enum import Enum
from typing import Literal
from typing_extensions import Self

from shared.data import SimulatorOutput


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