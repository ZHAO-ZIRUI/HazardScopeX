import pygame
from typing import Tuple
from pydantic import Field

from core.pygame import PgProgressBar


class PgProgressBarBipolar(PgProgressBar):
    """
    中心进度条控件, 值范围为 -1~1, 中心值为 0
    """
    center_width: int = Field(ge=0, default=2)
    center_color: None | Tuple[int, int, int, int] = None
    center_ignore_padding: bool = False

    value: float = Field(ge=-1, le=1, default=0)

    @property
    def content_rect(self) -> Tuple[int, int, int, int]:
        """计算双极进度条的内容矩形"""
        x, y, w, h = super().content_rect
        
        # 应用反向逻辑
        value = -self.value if self.reverse else self.value
        
        # 计算中心点和半尺寸
        center_x = x + w / 2
        center_y = y + h / 2
        half_w = w / 2
        half_h = h / 2
        distance = (half_w if not self.vertical else half_h) * abs(value)
        
        if not self.vertical:
            # 水平方向
            if value < 0:
                return int(center_x - distance), int(y), int(distance), int(h)
            else:
                return int(center_x), int(y), int(distance), int(h)
        else:
            # 垂直方向
            if value < 0:
                return int(x), int(center_y), int(w), int(distance)
            else:
                return int(x), int(center_y - distance), int(w), int(distance)

    @property
    def center_pose(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        中心线位置
        :return: ``center_pose[0]`` 为起始点, ``center_pose[1]`` 为终止点
        """
        # 选择基础矩形
        x, y, w, h = self.border_rect if self.center_ignore_padding else self.padding_rect
        
        # 计算中心点
        center_x = x + w / 2
        center_y = y + h / 2
        
        if not self.vertical:
            # 水平中心线：从上到下
            return (center_x, y), (center_x, y + h)
        else:
            # 垂直中心线：从左到右
            return (x, center_y), (x + w, center_y)

    def _draw_content(self):
        # 进度条
        pygame.draw.rect(
            self.surface,
            self.palette.PRIMARY.RGBA,
            self.content_rect,
        )

        # 中心线
        if self.center_width == 0:
            return
        pygame.draw.line(
            self.surface,
            (self.center_color or self.palette.BRIGHT_RED.RGBA),
            self.center_pose[0],
            self.center_pose[1],
            self.center_width,
        )
