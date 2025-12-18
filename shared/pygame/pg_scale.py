from enum import Enum, auto


class PgScale(Enum):
    """
    缩放模式

    - SCALE: 按比例缩放, 保持宽高比
    - STRETCH: 拉伸以填满整个区域
    - PIXEL_PERFECT: 1:1像素绘制
    """
    SCALE = auto()
    STRETCH = auto()
    PIXEL_PERFECT = auto()