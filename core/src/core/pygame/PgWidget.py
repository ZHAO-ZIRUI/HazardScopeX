import pygame
from pydantic import BaseModel, Field, ConfigDict
from typing import Tuple
from abc import ABC, abstractmethod

from core.pygame import PgColor


class PgWidget(BaseModel, ABC):
    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True
    )

    # 上下文
    surface: pygame.Surface

    # 基础控件位置
    position: Tuple[int, int]
    width: int = Field(ge=0)
    height: int = Field(ge=0)

    # 边框与布局
    margin: int = Field(default=0, ge=0)
    margin_x: int = Field(default=0, ge=0)
    margin_y: int = Field(default=0, ge=0)
    margin_top: int = Field(default=0, ge=0)
    margin_bottom: int = Field(default=0, ge=0)
    margin_left: int = Field(default=0, ge=0)
    margin_right: int = Field(default=0, ge=0)

    padding: int = Field(default=0, ge=0)
    padding_x: int = Field(default=0, ge=0)
    padding_y: int = Field(default=0, ge=0)
    padding_top: int = Field(default=0, ge=0)
    padding_bottom: int = Field(default=0, ge=0)
    padding_left: int = Field(default=0, ge=0)
    padding_right: int = Field(default=0, ge=0)

    border: int = Field(default=0, ge=0)
    border_x: int = Field(default=0, ge=0)
    border_y: int = Field(default=0, ge=0)
    border_top: int = Field(default=0, ge=0)
    border_bottom: int = Field(default=0, ge=0)
    border_left: int = Field(default=0, ge=0)
    border_right: int = Field(default=0, ge=0)

    # 颜色
    palette: PgColor = Field(default_factory=PgColor)
    margin_bg_color: None | Tuple[int, int, int, int] = None
    padding_bg_color: None | Tuple[int, int, int, int] = None
    border_color: None | Tuple[int, int, int, int] = None

    @property
    def x(self) -> int:
        return self.position[0]

    @property
    def y(self) -> int:
        return self.position[1]

    @property
    def center(self) -> Tuple[int, int]:
        return self.center_x, self.center_y

    @property
    def center_x(self) -> int:
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        return self.y + self.height // 2

    @property
    def margin_rect(self) -> Tuple[int, int, int, int]:
        """
        Margin 所处占位的矩形
        :return: ``x``, ``y``, ``width``, ``height``
        """
        return self.x, self.y, self.width, self.height

    @property
    def border_rect(self) -> Tuple[int, int, int, int]:
        """
        Border 所处占位的矩形
        :return: ``x``, ``y``, ``width``, ``height``
        """
        margin = (
            self.margin_top or self.margin_y or self.margin,
            self.margin_bottom or self.margin_y or self.margin,
            self.margin_left or self.margin_x or self.margin,
            self.margin_right or self.margin_x or self.margin
        )
        return self._calc_inset_rect(self.margin_rect, margin)

    @property
    def padding_rect(self) -> Tuple[int, int, int, int]:
        """
        Padding 所处占位的矩形
        :return: ``x``, ``y``, ``width``, ``height``
        """
        border = (
            self.border_top or self.border_y or self.border,
            self.border_bottom or self.border_y or self.border,
            self.border_left or self.border_x or self.border,
            self.border_right or self.border_x or self.border
        )
        return self._calc_inset_rect(self.border_rect, border)

    @property
    def content_rect(self) -> Tuple[int, int, int, int]:
        """
        Content 所处占位的矩形
        :return: ``x``, ``y``, ``width``, ``height``
        """
        padding = (
            self.padding_top or self.padding_y or self.padding,
            self.padding_bottom or self.padding_y or self.padding,
            self.padding_left or self.padding_x or self.padding,
            self.padding_right or self.padding_x or self.padding
        )
        return self._calc_inset_rect(self.padding_rect, padding)

    def _draw_margin_rect(self) -> None:
        """绘制 margin 矩形, 仅在 ``margin_bg_color`` 被赋值时生效"""
        if self.margin_bg_color is None:
            return
        pygame.draw.rect(
            self.surface,
            self.margin_bg_color,
            self.margin_rect,
        )

    def _draw_border_rect(self) -> None:
        """绘制边框"""
        if self.border == 0:
            return
            
        color = self.border_color or self.palette.PRIMARY
        x, y, w, h = self.border_rect
        
        # 计算边框宽度
        border_top = self.border_top or self.border_y or self.border
        border_bottom = self.border_bottom or self.border_y or self.border
        border_left = self.border_left or self.border_x or self.border
        border_right = self.border_right or self.border_x or self.border
        
        # 绘制
        if border_top > 0:
            pygame.draw.rect(
                self.surface,
                color,
                (x, y, w, border_top)
            )
        if border_bottom > 0:
            pygame.draw.rect(
                self.surface,
                color,
                (x, y + h - border_bottom, w, border_bottom)
            )
        if border_left > 0:
            pygame.draw.rect(
                self.surface,
                color,
                (x, y, border_left, h)
            )
        if border_right > 0:
            pygame.draw.rect(
                self.surface,
                color,
                (x + w - border_right, y, border_right, h)
            )

    def _draw_padding_rect(self) -> None:
        """绘制 padding 矩形, 仅在 ``padding_bg_color`` 被赋值时生效"""
        if self.padding_bg_color is None:
            return
        pygame.draw.rect(
            self.surface,
            self.padding_bg_color,
            self.padding_rect,
        )

    @abstractmethod
    def _draw_content(self):
        """绘制主体内容"""
        raise NotImplementedError()

    def draw(self):
        self._draw_margin_rect()
        self._draw_border_rect()
        self._draw_padding_rect()
        self._draw_content()

    def update(self, *args, **kwargs):
        """更新控件状态, 在 ``draw()`` 之前调用"""
        pass

    @staticmethod
    def _calc_inset_rect(
            rect: Tuple[int, int, int, int],
            amount: Tuple[int, int, int, int],
    ) -> Tuple[int, int, int, int]:
        """
        计算下一级别的元素位置
        :param rect: 4 个元素构成的元组: x, y, width, height
        :param amount: 4 个元素构成的元组: top, bottom, left, right
        :return: 新的矩形位置和尺寸
        """
        x, y, w, h = rect
        top, bottom, left, right = amount
        
        # 计算新的位置和尺寸
        new_x = x + left
        new_y = y + top
        new_w = max(0, w - left - right)
        new_h = max(0, h - top - bottom)
        
        # 如果尺寸为0，抛出异常
        if new_w == 0 or new_h == 0:
            raise ValueError(f"Layout calc error: resulting size is zero (w={new_w}, h={new_h})")
            
        return new_x, new_y, new_w, new_h