from dataclasses import dataclass


@dataclass
class PgColor:
    """
    基于 W3C 定义的颜色, 编码为 RGBA
    """
    # W3C
    BLACK = (0, 0, 0, 255)
    WHITE = (255, 255, 255, 255)
    BRIGHT_RED = (255, 0, 0, 255)
    BRIGHT_GREEN = (0, 255, 0, 255)
    BRIGHT_BLUE = (0, 0, 255, 255)
    BRIGHT_YELLOW = (255, 255, 0, 255)
    BRIGHT_CYAN = (0, 255, 255, 255)
    BRIGHT_MAGENTA = (255, 0, 255, 255)
    ORANGE = (255, 165, 0, 255)
    LIME = (0, 255, 0, 255)
    AQUA = (0, 255, 255, 255)
    VIOLET = (238, 130, 238, 255)
    GOLD = (255, 215, 0, 255)
    LIGHT_BLUE = (135, 206, 250, 255)
    LIGHT_GRAY = (192, 192, 192, 255)
    GRAY = (128, 128, 128, 255)
    DARK_GRAY = (64, 64, 64, 255)
    SILVER = (192, 192, 192, 255)
    DARK_RED = (139, 0, 0, 255)
    DARK_GREEN = (0, 100, 0, 255)
    DARK_BLUE = (0, 0, 139, 255)
    NAVY = (0, 0, 128, 255)
    PURPLE = (128, 0, 128, 255)
    MAROON = (128, 0, 0, 255)
    OLIVE = (128, 128, 0, 255)
    TEAL = (0, 128, 128, 255)
    PINK = (255, 192, 203, 255)
    BROWN = (165, 42, 42, 255)
    INDIGO = (75, 0, 130, 255)

    # CUSTOM
    GREEN = (0, 200, 0, 255)


    # 以下内容为应用侧颜色定义, 如需自定义颜色可在继承该类后覆写以下内容

    PRIMARY = GREEN
    SECONDARY = LIGHT_GRAY
    SUCCESS = BRIGHT_GREEN
    DANGER = BRIGHT_RED
    WARNING = BRIGHT_YELLOW
    INFO = BRIGHT_CYAN
    LIGHT = WHITE
    DARK = BLACK
    
    BACKGROUND = BLACK
    TEXT_PRIMARY = WHITE
    TEXT_SECONDARY = LIGHT_GRAY
    TEXT_MUTED = GRAY