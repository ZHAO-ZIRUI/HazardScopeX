import numpy as np
import random
from shared.scenarios import Factor
from shared.simulator import *
from shared.data import Image
from typing import Literal


class FactorCameraBrokenLines(Factor):
    NAME = 'F_CameraBrokenLines'

    def __init__(
        self, 
        context: CarlaContext, 
        sensor: CarlaSensor,
        *,
        orientation: Literal['horizontal', 'vertical', 'both'] = 'vertical',
    ):
        super().__init__(context)
        self._sensor = sensor
        self._orientation = orientation.lower()
        if self._orientation not in ['horizontal', 'vertical', 'both']:
            raise ValueError(f"orientation must be 'horizontal', 'vertical', or 'both', got '{orientation}'")
        self._mask = None  # 蒙版，标记需要绘制洋红色的像素位置

    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def _generate_mask(self, width: int, height: int) -> np.ndarray:
        """生成坏线蒙版
        
        Args:
            width: 图像宽度
            height: 图像高度
            
        Returns:
            布尔数组，True表示需要绘制洋红色的像素
        """
        mask = np.zeros((height, width), dtype=bool)
        
        # 计算中心50%区域
        center_x_start = int(width * 0.25)
        center_x_end = int(width * 0.75)
        center_y_start = int(height * 0.25)
        center_y_end = int(height * 0.75)
        
        # 在中心50%区域随机选择一个点
        center_x = random.randint(center_x_start, center_x_end)
        center_y = random.randint(center_y_start, center_y_end)
        
        # 基础线条宽度5px
        base_line_width = 5
        half_width = base_line_width // 2
        
        # 根据orientation参数决定生成哪种线条
        if self._orientation in ['horizontal', 'both']:
            # 绘制贯穿图片的横向基础线条（5px宽）
            y_start = max(0, center_y - half_width)
            y_end = min(height, center_y + half_width + 1)
            mask[y_start:y_end, :] = True
            
            # 在基础线条的上下，临近±5%区域内，根据高斯采样生成一些线条，1px宽
            y_range = height * 0.05  # ±5%区域
            y_min = max(0, int(center_y - y_range))
            y_max = min(height, int(center_y + y_range))
            
            # 生成一些横向辅助线条（1px宽）
            num_horizontal_lines = random.randint(3, 8)
            for _ in range(num_horizontal_lines):
                # 高斯采样y坐标
                y_offset = np.random.normal(0, y_range / 3)
                y_line = int(center_y + y_offset)
                y_line = max(y_min, min(y_max - 1, y_line))
                if 0 <= y_line < height:
                    mask[y_line, :] = True
        
        if self._orientation in ['vertical', 'both']:
            # 绘制贯穿图片的纵向基础线条（5px宽）
            x_start = max(0, center_x - half_width)
            x_end = min(width, center_x + half_width + 1)
            mask[:, x_start:x_end] = True
            
            # 在基础线条的左右，临近±5%区域内，根据高斯采样生成一些线条，1px宽
            x_range = width * 0.05  # ±5%区域
            x_min = max(0, int(center_x - x_range))
            x_max = min(width, int(center_x + x_range))
            
            # 生成一些纵向辅助线条（1px宽）
            num_vertical_lines = random.randint(3, 8)
            for _ in range(num_vertical_lines):
                # 高斯采样x坐标
                x_offset = np.random.normal(0, x_range / 3)
                x_line = int(center_x + x_offset)
                x_line = max(x_min, min(x_max - 1, x_line))
                if 0 <= x_line < width:
                    mask[:, x_line] = True
        
        return mask

    def on_sensor_data_recv(self, data: Image) -> Image:
        # 首次收到图像时计算蒙版
        if self._mask is None:
            self._mask = self._generate_mask(data.width, data.height)
            self.logger.info(f'Generated broken lines mask for image size: {data.width}x{data.height}')
        
        # 应用蒙版，将标记的像素设置为洋红色 (BGRA格式: B=255, G=0, R=255, A=255)
        magenta = np.array([255, 0, 255, 255], dtype=np.uint8)
        data._raw[self._mask] = magenta
        
        return data