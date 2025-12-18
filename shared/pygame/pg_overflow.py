from enum import Enum, auto

class PgOverflow(Enum):
    """溢出处理方式"""
    OVERFLOW = auto()   # 不处理, 允许文本超出内容区域
    HIDE = auto()       # 超出部分裁剪隐藏
    EXTEND = auto()     # 根据文本自动扩展控件尺寸