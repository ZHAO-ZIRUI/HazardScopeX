import pygame
from abc import abstractmethod
from typing import Any
from typing_extensions import Self
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr

from shared.pygame import PgColor, PgPos, PgRect, PgSpacing, PgRefSurface


class PgWidget(BaseModel):
    """PgApp 的控件基类"""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    # 上下文
    _ref_surface: PgRefSurface = PrivateAttr(default=PgRefSurface(None))
    parent: Self | None = None
    childrens: list[Self] = Field(default_factory=list, frozen=True)

    # 基础控件位置
    rect: PgRect                                                                    # 控件基础位置
    z_index: int = Field(default=0)                                                 # 层级排序
    show: bool = Field(default=True)                                                # 控件是否显示

    # 边框与布局
    margin: PgSpacing = Field(default_factory=PgSpacing)                            # 外边距
    padding: PgSpacing = Field(default_factory=PgSpacing)                           # 内边距
    border: PgSpacing = Field(default_factory=PgSpacing)                            # 边框宽度

    # 颜色配置
    color_margin: tuple[int, int, int, int] | None = Field(default=None)            # 外边距背景色
    color_padding: tuple[int, int, int, int] | None = Field(default=None)           # 内边距背景色
    color_border: tuple[int, int, int, int] | None = Field(default=PgColor.BORDER)  # 边框颜色
    color_background: tuple[int, int, int, int] | None = Field(default=None)           # 内容颜色

    @abstractmethod
    def __init_widgets__(self) -> None:
        """初始化控件"""
        raise NotImplementedError()

    def model_post_init(self, __context: Any) -> None:
        self.__init_widgets__()

    @property
    def center_pos(self) -> PgPos:
        return PgPos(
            x=self.rect.x + self.rect.width / 2,
            y=self.rect.y + self.rect.height / 2,
        )

    @property
    def margin_rect(self) -> PgRect:
        return self.rect

    @property
    def border_rect(self) -> PgRect:
        return self._calc_inset_rect(self.margin_rect, self.margin)

    @property
    def padding_rect(self) -> PgRect:
        return self._calc_inset_rect(self.border_rect, self.border)

    @property
    def content_rect(self) -> PgRect:
        return self._calc_inset_rect(self.padding_rect, self.padding)

    @property
    def surface(self) -> pygame.Surface:
        return self._ref_surface()

    def set_ref_surface(self, ref_surface: PgRefSurface) -> None:
        self._ref_surface = ref_surface

    def draw(self) -> None:
        """绘制控件"""
        if not self.show or not self._check_parent_show():
            return

        self._draw_margin_rect()
        self._draw_border_rect()
        self._draw_padding_rect()
        self._draw_content_rect()

        self._draw_content()

    @abstractmethod
    def _draw_content(self) -> None:
        """绘制内容"""
        raise NotImplementedError()

    def _check_parent_show(self) -> bool:
        """
        递归检查父控件链的 show 状态

        Returns:
            bool: 如果所有父控件都 show=True 返回 True, 否则返回 False
        """
        parent = self.parent
        while parent is not None:
            if not parent.show:
                return False
            parent = parent.parent
        return True

    @staticmethod
    def _calc_inset_rect(
            rect: tuple[int, int, int, int] | PgRect,
            amount: tuple[int, int, int, int] | PgSpacing,
    ) -> PgRect:
        """
        计算内缩后的矩形位置和尺寸

        Args:
            rect: 原始矩形，可以是 (x, y, width, height) 元组或 PgRect 对象
            amount: 内缩量，可以是 (top, bottom, left, right) 元组或 PgSpacing 对象

        Returns:
            PgRect: 内缩后的新矩形

        Raises:
            ValueError: 当计算结果导致尺寸为 0 时抛出异常
        """
        # 统一处理 rect 参数
        if isinstance(rect, PgRect):
            x, y, w, h = rect.x, rect.y, rect.width, rect.height
        else:
            x, y, w, h = rect

        # 统一处理 amount 参数
        if isinstance(amount, PgSpacing):
            top, bottom, left, right = amount()
        else:
            top, bottom, left, right = amount

        # 计算新的位置和尺寸
        new_x = x + left
        new_y = y + top
        new_w = max(0, w - left - right)
        new_h = max(0, h - top - bottom)

        # 如果尺寸为 0，抛出异常
        if new_w == 0 or new_h == 0:
            raise ValueError(
                f"Layout calc error: resulting size is zero "
                f"(w={new_w}, h={new_h}, inset=({top}, {bottom}, {left}, {right}))"
            )

        return PgRect(x=new_x, y=new_y, width=new_w, height=new_h)

    def _draw_margin_rect(self) -> None:
        """绘制 margin 矩形, 仅在 ``color_margin`` 被赋值时生效"""
        if self.color_margin is None:
            return
        x, y, w, h = self.margin_rect
        # 使用中间 SRCALPHA Surface 以正确应用 RGBA 的 alpha
        temp_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        temp_surface.fill(self.color_margin)
        self.surface.blit(temp_surface, (x, y))

    def _draw_border_rect(self) -> None:
        """绘制边框"""
        x, y, w, h = self.border_rect
        top, bottom, left, right = self.border

        if top == 0 and bottom == 0 and left == 0 and right == 0:
            return

        if top > 0:
            pygame.draw.rect(self.surface, self.color_border, (x, y, w, top))
        if bottom > 0:
            pygame.draw.rect(self.surface, self.color_border, (x, y + h - bottom, w, bottom))
        if left > 0:
            pygame.draw.rect(self.surface, self.color_border, (x, y, left, h))
        if right > 0:
            pygame.draw.rect(self.surface, self.color_border, (x + w - right, y, right, h))

    def _draw_padding_rect(self) -> None:
        """绘制 padding 矩形, 仅在 ``color_padding`` 被赋值时生效"""
        if self.color_padding is None:
            return
        x, y, w, h = self.padding_rect
        # 使用中间 SRCALPHA Surface 以正确应用 RGBA 的 alpha
        temp_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        temp_surface.fill(self.color_padding)
        self.surface.blit(temp_surface, (x, y))

    def _draw_content_rect(self) -> None:
        """绘制内容矩形, 仅在 ``color_background`` 被赋值时生效"""
        if self.color_background is None:
            return
        x, y, w, h = self.content_rect
        # 使用中间 SRCALPHA Surface 以正确应用 RGBA 的 alpha
        temp_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        temp_surface.fill(self.color_background)
        self.surface.blit(temp_surface, (x, y))