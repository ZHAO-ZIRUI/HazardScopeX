import pygame
from typing import Tuple

from core.pygame import PgProgressBar


class PgProgressBarLinear(PgProgressBar):
    """
    线性进度条控件, 值范围为 0~1
    """

    @property
    def content_rect(self) -> Tuple[int, int, int, int]:
        """计算线性进度条的内容矩形"""
        x, y, w, h = super().content_rect
        
        # 计算进度尺寸
        progress_w = w * self.value
        progress_h = h * self.value
        
        if not self.vertical:
            # 水平方向
            if self.reverse:
                # 右向左：从右边开始
                return int(x + w - progress_w), int(y), int(progress_w), int(h)
            else:
                # 左向右：从左边开始
                return int(x), int(y), int(progress_w), int(h)
        else:
            # 垂直方向
            if self.reverse:
                # 上向下：从顶部开始
                return int(x), int(y), int(w), int(progress_h)
            else:
                # 下向上：从底部开始
                return int(x), int(y + h - progress_h), int(w), int(progress_h)

    def _draw_content(self):
        pygame.draw.rect(
            self.surface,
            self.content_color,
            self.content_rect,
        )