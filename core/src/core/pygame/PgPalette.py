from typing import Tuple

from core.pygame.PgColor import PgColor


class PgPalette:
    """
    包含预制颜色, 风格与颜色调整的类
    """

    # W3C 基准颜色
    BLACK = PgColor(0, 0, 0)
    WHITE = PgColor(255, 255, 255)
    BRIGHT_RED = PgColor(255, 0, 0)
    BRIGHT_GREEN = PgColor(0, 255, 0)
    BRIGHT_BLUE = PgColor(0, 0, 255)
    BRIGHT_YELLOW = PgColor(255, 255, 0)
    BRIGHT_CYAN = PgColor(0, 255, 255)
    BRIGHT_MAGENTA = PgColor(255, 0, 255)
    ORANGE = PgColor(255, 165, 0)
    GREEN = PgColor(0, 200, 0)
    LIME = PgColor(0, 255, 0)
    AQUA = PgColor(0, 255, 255)
    VIOLET = PgColor(238, 130, 238)
    GOLD = PgColor(255, 215, 0)
    LIGHT_BLUE = PgColor(135, 206, 250)
    LIGHT_GRAY = PgColor(192, 192, 192)
    GRAY = PgColor(128, 128, 128)
    DARK_GRAY = PgColor(64, 64, 64)
    SILVER = PgColor(192, 192, 192)
    DARK_RED = PgColor(139, 0, 0)
    DARK_GREEN = PgColor(0, 100, 0)
    DARK_BLUE = PgColor(0, 0, 139)
    NAVY = PgColor(0, 0, 128)
    PURPLE = PgColor(128, 0, 128)
    MAROON = PgColor(128, 0, 0)
    OLIVE = PgColor(128, 128, 0)
    TEAL = PgColor(0, 128, 128)
    PINK = PgColor(255, 192, 203)
    BROWN = PgColor(165, 42, 42)
    INDIGO = PgColor(75, 0, 130)

    @property
    def PRIMARY(self) -> PgColor:
        return self.BRIGHT_BLUE

    @property
    def SECONDARY(self) -> PgColor:
        return self.LIGHT_GRAY

    @property
    def SUCCESS(self) -> PgColor:
        return self.BRIGHT_GREEN

    @property
    def DANGER(self) -> PgColor:
        return self.BRIGHT_RED

    @property
    def WARNING(self) -> PgColor:
        return self.BRIGHT_YELLOW

    @property
    def INFO(self) -> PgColor:
        return self.BRIGHT_CYAN

    @property
    def LIGHT(self) -> PgColor:
        return self.WHITE

    @property
    def DARK(self) -> PgColor:
        return self.BLACK

    @property
    def BACKGROUND(self) -> PgColor:
        return self.BLACK

    @property
    def TEXT_PRIMARY(self) -> PgColor:
        return self.WHITE

    @property
    def TEXT_SECONDARY(self) -> PgColor:
        return self.LIGHT_GRAY

    @property
    def TEXT_MUTED(self) -> PgColor:
        return self.GRAY

    @staticmethod
    def dim(
            color: Tuple[int, int, int, int] | PgColor,
            factor: float,
            alpha: bool = False
    ) -> PgColor:
        """
        将颜色变暗
        :param color: 颜色, (r, g, b, a)
        :param factor: 变暗因子, 0.0 ~ 1.0, 0.0 表示不变, 1.0 表示完全变黑
        :param alpha: 是否对透明度进行变暗
        """
        if not (0.0 <= factor <= 1.0):
            raise ValueError("Factor must be between 0.0 and 1.0")

        if isinstance(color, PgColor):
            color = color.RGBA

        factor = 1.0 - factor

        r = int(color[0] * factor)
        g = int(color[1] * factor)
        b = int(color[2] * factor)
        if alpha:
            a = int(color[3] * factor)
        else:
            a = color[3]
        return PgColor(r, g, b, a)

    @staticmethod
    def alpha(
            color: Tuple[int, int, int, int],
            factor: float
    ) -> PgColor:
        """
        调整颜色透明度
        :param color: 颜色, (r, g, b, a)
        :param factor: 透明度因子, 0.0 ~ 1.0, 0.0 表示完全透明, 1.0 表示不变
        """
        if not (0.0 <= factor <= 1.0):
            raise ValueError("Factor must be between 0.0 and 1.0")

        if isinstance(color, PgColor):
            color = color.RGBA

        a = int(color[3] * factor)
        return PgColor(color[0], color[1], color[2], a)