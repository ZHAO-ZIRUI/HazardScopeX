import pygame
from typing import Any, Tuple

from pydantic import Field, PrivateAttr

from shared.pygame import PgColor, PgPos, PgRect, PgSpacing, PgWidget, PgText, PgOverflow


class PgGrid(PgWidget):
    """使用网格间距辅助布局并显示调试信息的控件"""

    # 网格间距
    col_interval: int = Field(default=24, ge=1)  # 列宽
    row_interval: int = Field(default=24, ge=1)  # 行高
    
    z_index: int = Field(default=999)

    # 网格线颜色
    color_grid: tuple[int, int, int, int] | None = Field(default=None)

    # 调试文本
    _debug_text: PgText | None = PrivateAttr(default=None)

    def __init_widgets__(self) -> None:
        """初始化控件"""
        from shared.pygame import PgText as _PgTextAlias  # 避免循环导入

        # 默认网格颜色
        if self.color_grid is None:
            self.color_grid = PgColor.WARNING

        # 调试文本: 显示当前鼠标所在的行列索引
        debug_rect = PgRect(
            x=self.rect.x,
            y=self.rect.y,
            width=self.col_interval,
            height=self.row_interval,
            z_index=self.z_index,
            show=self.show,
        )
        self._debug_text = _PgTextAlias(
            rect=debug_rect,
            text="",
            bold=True,
            color_text=PgColor.WARNING,
            color_background=PgColor.BLACK,
            overflow_x=PgOverflow.EXTEND,
            border=PgSpacing(value=2),
            color_border=PgColor.WARNING,
            z_index=self.z_index,
            show=self.show,
        )
        self.childrens.append(self._debug_text)

    def get_pos(self, col: int, row: int) -> PgPos:
        """
        根据行列索引返回该网格单元格左上角位置

        Args:
            row: 行索引 (从 0 开始)
            col: 列索引 (从 0 开始)

        Returns:
            PgPos: 该单元格左上角位置
        """
        return PgPos(x=self.rect.x + col * self.col_interval, y=self.rect.y + row * self.row_interval)

    def get_rect(self, col: int, row: int, width: int = 1, height: int = 1) -> PgRect:
        """
        根据行列索引返回该网格单元格矩形

        Args:
            row: 行索引 (从 0 开始)
            col: 列索引 (从 0 开始)
            width: 单元格宽度 (默认 1)
            height: 单元格高度 (默认 1)

        Returns:
            PgRect: 该单元格矩形
        """
        return PgRect(x=self.rect.x + col * self.col_interval, y=self.rect.y + row * self.row_interval, width=width * self.col_interval, height=height * self.row_interval)

    def _draw_content(self) -> None:
        """绘制网格与调试文本内容"""
        if not self.show:
            return

        surface = self.surface
        x, y, w, h = self.rect

        # 绘制网格线
        if self.color_grid is not None:
            # 垂直线
            col = 0
            while True:
                line_x = x + col * self.col_interval
                if line_x > x + w:
                    break
                pygame.draw.line(
                    surface,
                    self.color_grid,
                    (line_x, y),
                    (line_x, y + h),
                    1,
                )
                col += 1

            # 水平线
            row = 0
            while True:
                line_y = y + row * self.row_interval
                if line_y > y + h:
                    break
                pygame.draw.line(
                    surface,
                    self.color_grid,
                    (x, line_y),
                    (x + w, line_y),
                    1,
                )
                row += 1

        # 调试文本: 显示鼠标所在的行/列
        if self._debug_text is None:
            return

        mouse_x, mouse_y = pygame.mouse.get_pos()

        # 鼠标不在网格区域内时不显示调试信息
        if not (x <= mouse_x < x + w and y <= mouse_y < y + h):
            self._debug_text.text = ""
            return

        col_index = (mouse_x - x) // self.col_interval
        row_index = (mouse_y - y) // self.row_interval

        if col_index < 0:
            col_index = 0
        if row_index < 0:
            row_index = 0

        self._debug_text.text = f"GRID R/C: {row_index}/{col_index}"


