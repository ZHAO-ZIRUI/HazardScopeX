import pygame
import uuid
from typing import Any, List, Tuple, Dict
from pydantic import Field, PrivateAttr

from core.pygame import PgWidget, PgCursor, PgText, PgContainer


class PgGrid(PgContainer):
    """使用 PgCursor 控件构造的网格布局"""

    col_interval: int = Field(default=24)
    row_interval: int = Field(default=24)

    color: None | Tuple[int, int, int, int] = None

    _row: PgCursor = PrivateAttr()
    _cols: List[PgCursor] = PrivateAttr(default_factory=list)
    _debug_text: PgText = PrivateAttr()

    def get_position(self, row: int, col: int) -> Tuple[int, int]:
        """根据 Grid 中的行列定义取得坐标"""
        return self._cols[col][row]

    def model_post_init(self, context: Any, /) -> None:
        # 提供默认值
        self.color = self.color or self.palette.WARNING

        # 构建 ROW
        self._row = PgCursor(
            surface=self.surface,
            position=self.position,
            width=self.width,
            height=self.height,
            interval=self.col_interval,
            vertical=False,
            show=self.show,
            color=self.color,
        )
        self.add_widget(self._row)


        for i in range(len(self._row)):
            col = PgCursor(
                surface=self.surface,
                position=self._row[i],
                width=self.width,
                height=self.height,
                interval=self.row_interval,
                vertical=True,
                show=self.show,
                color=self.color,
            )
            self._cols.append(col)
            self.add_widget(col)

        self.z_index = 999
        self._debug_text = PgText(
            surface=self.surface,
            position=(0, 0),
            width=1,
            height=self.col_interval,
            bold=True,
            text_color=self.palette.WARNING,
            background_color=self.palette.BLACK,
            overflow_x=PgText.Overflow.AUTO,
            border=2,
            border_color=self.palette.WARNING,
            text=""
        )
        self.add_widget(self._debug_text)

    def _draw_content(self):
        if not self.show:
            return

        # 获取鼠标位置
        x, y = pygame.mouse.get_pos()

        # 处理鼠标出界
        if not (self.x <= x < self.x + self.width and self.y <= y < self.y + self.height):
            return

        # 计算索引
        col_index = (x - self.x) // self.row_interval
        row_index = (y - self.y) // self.col_interval
        if len(self._row) > 0:
            max_col = len(self._row) - 1
            col_index = max(0, min(col_index, max_col))
        else:
            col_index = 0
        if self._cols and len(self._cols[0]) > 0:
            max_row = len(self._cols[0]) - 1
            row_index = max(0, min(row_index, max_row))
        else:
            row_index = 0

        self._debug_text.text = f"GRID R/C: {row_index}/{col_index}"
        
        super()._draw_content()




