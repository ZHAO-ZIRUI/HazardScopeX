from typing import Any, Dict
from pydantic import Field, PrivateAttr
from enum import Enum

from core.pygame import PgText, PgPalette


class PgTextValue(PgText):
    """
    显示值文本的文本控件, 继承自 PgText, 提供了以下功能:

    - 预设了常用属性
    - 提供了状态与颜色的绑定
    - 提供了对数值类型的小数位数支持
    - 提供了对数值类型的正负号支持
    - 提供了闪烁动画
    """

    class Status(Enum):
        NORMAL = "normal"
        INFO = "info"
        WARNING = "warning"
        DANGER = "danger"

    MAPPING_STATUS_TO_COLOR: Dict[Status, tuple[int, int, int, int]] = Field(default_factory=dict)
    MAPPING_STATUS_TO_COLOR_DIM: Dict[Status, tuple[int, int, int, int]] = Field(default_factory=dict)

    text: str | float | int = Field(default="0")
    width: int = Field(default=1, ge=0)
    padding_x: int = Field(default=2, ge=0)
    margin_y: int = Field(default=2, ge=0)
    overflow_x: PgText.Overflow = Field(default=PgText.Overflow.AUTO)

    decimal_places: int = Field(default=2, ge=0)
    show_sign: bool = Field(default=False)

    blink_text: bool = Field(default=False)
    blink_border: bool = Field(default=False)
    blink_dim_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    blink_duration: int = Field(default=30, ge=1)

    status: Status = Field(default=Status.NORMAL)

    _cache_text: str | None = PrivateAttr(default=None)
    _cache_text_color: tuple[int, int, int, int] | None = PrivateAttr(default=None)
    _cache_border_color: tuple[int, int, int, int] | None = PrivateAttr(default=None)
    _count_frame: int = PrivateAttr(default=0)

    def model_post_init(self, context: Any, /) -> None:
        super().model_post_init(context)
        self.MAPPING_STATUS_TO_COLOR = {
            self.Status.NORMAL: self.palette.SUCCESS.RGBA,
            self.Status.INFO: self.palette.INFO.RGBA,
            self.Status.WARNING: self.palette.WARNING.RGBA,
            self.Status.DANGER: self.palette.DANGER.RGBA,
        }

        self.MAPPING_STATUS_TO_COLOR_DIM = {
            self.Status.NORMAL: PgPalette.dim(self.MAPPING_STATUS_TO_COLOR[self.Status.NORMAL], self.blink_dim_ratio).RGBA,
            self.Status.INFO: PgPalette.dim(self.MAPPING_STATUS_TO_COLOR[self.Status.INFO], self.blink_dim_ratio).RGBA,
            self.Status.WARNING: PgPalette.dim(self.MAPPING_STATUS_TO_COLOR[self.Status.WARNING], self.blink_dim_ratio).RGBA,
            self.Status.DANGER: PgPalette.dim(self.MAPPING_STATUS_TO_COLOR[self.Status.DANGER], self.blink_dim_ratio).RGBA,
        }

    def draw(self):
        self._count_frame += 1

        # 临时备份内容, 以最小化改动代码, 在调用父类方法后再还原
        self._cache_text = self.text
        self._cache_text_color = self.text_color
        self._cache_border_color = self.border_color

        self.text = self._calc_text_value(self.text)
        self.text_color = self._calc_text_color()
        self.border_color = self._calc_border_color()

        super().draw()

        # 还原内容
        self.text = self._cache_text
        self.text_color = self._cache_text_color
        self.border_color = self._cache_border_color

    def _calc_text_value(self, text: str) -> str:
        """
        计算文本值, 应用 ``decimal_places`` 和 ``show_sign`` 属性
        :param text: 输入文本
        :return: 处理后的文本
        """
        value = self._try_convert_to_number(text)
        if value is None:
            return text

        # 处理小数位数
        if value.is_integer():
            result = f"{int(value)}"
        else:
            result = f"{value:.{self.decimal_places}f}"

        # 处理正负号
        if self.show_sign:
            abs_value = abs(value)
            # 避免浮点数精度问题，使用绝对值判断
            if abs_value < 1e-10:
                result = f"+{abs_value}"
            elif value > 0:
                result = f"+{result}"

        return result

    def _calc_text_color(self) -> tuple[int, int, int, int]:
        """
        计算文本颜色, 应用 ``status`` 和 ``blink_text`` 属性
        :return: 文本颜色值
        """
        if self.text_color is not None:
            return self.text_color

        color = self.MAPPING_STATUS_TO_COLOR[self.status]
        if not self.blink_text:
            return color
            
        # 计算闪烁效果
        blink_cycle = self.blink_duration * 2
        if (self._count_frame % blink_cycle) < self.blink_duration:
            return color
        else:
            return self.MAPPING_STATUS_TO_COLOR_DIM[self.status]

    def _calc_border_color(self) -> tuple[int, int, int, int] | None:
        """
        计算边框颜色, 应用 ``status`` 和 ``blink_border`` 属性
        :return: 边框颜色值
        """
        if self._cache_border_color is not None:
            return self._cache_border_color

        color = self.MAPPING_STATUS_TO_COLOR[self.status]
        if not self.blink_border:
            return color

        blink_cycle = self.blink_duration * 2
        if (self._count_frame % blink_cycle) < self.blink_duration:
            return color
        else:
            return self.MAPPING_STATUS_TO_COLOR_DIM[self.status]


    @staticmethod
    def _try_convert_to_number(value: Any) -> float | None:
        try:
            return float(value)
        except (ValueError, TypeError):
            return None