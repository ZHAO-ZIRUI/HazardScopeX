import pygame
from typing import Tuple, Any
from enum import Enum
from pydantic import Field, PrivateAttr

from core.pygame import PgWidget


class PgText(PgWidget):

    FONT_FALLBACK: list[str] = Field(default=[
        "monospace",
        "Consolas",
        "Monaco",
        "DejaVu Sans Mono",
        "Liberation Mono",
        "Courier New",
        "Arial",
        "Helvetica",
        "DejaVu Sans",
        "Liberation Sans",
        "sans-serif"
    ])

    class Align(Enum):
        """对齐方式"""
        BEGIN = "BEGIN"
        CENTER = "CENTER"
        END = "END"

    class Overflow(Enum):
        OVERFLOW = "OVERFLOW"
        HIDE = "HIDE"
        AUTO = "AUTO"

    text: str = Field(default="")
    text_color: Tuple[int, int, int, int] | None = Field(default=None)
    background_color: Tuple[int, int, int, int] | None = Field(default=None)

    bold: bool = Field(default=False)
    italic: bool = Field(default=False)
    font_name: str | None = Field(default=None)
    font_size: int = Field(default=16, ge=1)
    
    align_x: Align = Field(default=Align.BEGIN)
    align_y: Align = Field(default=Align.CENTER)
    overflow_x: Overflow = Field(default=Overflow.HIDE)
    overflow_y: Overflow = Field(default=Overflow.HIDE)

    _font: pygame.font.Font = PrivateAttr(None)
    _cache_font_key: str = PrivateAttr("")

    @property
    def text_size(self) -> Tuple[int, int]:
        """实时计算文本尺寸"""
        if not self.text or not self._font:
            return 0, 0
        
        lines = self.text.split('\n')
        max_width = 0
        total_height = 0
        
        for line in lines:
            if line:
                line_width, line_height = self._font.size(line)
                max_width = max(max_width, line_width)
                total_height += line_height
            else:
                _, line_height = self._font.size(' ')
                total_height += line_height
                
        return (max_width, total_height)

    def model_post_init(self, context: Any, /) -> None:
        self._update_font()

    def content_rect(self) -> Tuple[int, int, int, int]:
        x, y, w, h = super().content_rect

        # 如果需要进行自动计算, 在这里覆写
        if self.overflow_x == self.Overflow.AUTO or self.overflow_y == self.Overflow.AUTO:
            text_w, text_h = self.text_size

            if self.overflow_x == self.Overflow.AUTO:
                if text_w > w:
                    w = text_w

            if self.overflow_y == self.Overflow.AUTO:
                if text_h > h:
                    h = text_h

        return x, y, w, h

    def _update_font(self):
        """更新字体"""
        font_key = f"{self.font_name}_{self.font_size}_{self.bold}_{self.italic}"
        if self._cache_font_key != font_key:
            self._font = self._get_font()
            self._cache_font_key = font_key

    def _update_width_height(self):
        """根据自适应设置更新组件尺寸"""
        if not self.text:
            return
            
        text_w, text_h = self.text_size
        
        new_width = self.width
        new_height = self.height
        
        if self.overflow_x == self.Overflow.AUTO:
            current_content_w = self.width
            padding_w = (self.padding_left or self.padding_x or self.padding) + \
                       (self.padding_right or self.padding_x or self.padding)
            border_w = (self.border_left or self.border_x or self.border) + \
                      (self.border_right or self.border_x or self.border)
            margin_w = (self.margin_left or self.margin_x or self.margin) + \
                      (self.margin_right or self.margin_x or self.margin)
            current_content_w = current_content_w - padding_w - border_w - margin_w

            if text_w > current_content_w:
                new_width = text_w + padding_w + border_w + margin_w
            
        if self.overflow_y == self.Overflow.AUTO:
            current_content_h = self.height
            padding_h = (self.padding_top or self.padding_y or self.padding) + \
                       (self.padding_bottom or self.padding_y or self.padding)
            border_h = (self.border_top or self.border_y or self.border) + \
                      (self.border_bottom or self.border_y or self.border)
            margin_h = (self.margin_top or self.margin_y or self.margin) + \
                      (self.margin_bottom or self.margin_y or self.margin)
            current_content_h = current_content_h - padding_h - border_h - margin_h

            if text_h > current_content_h:
                new_height = text_h + padding_h + border_h + margin_h
        
        self.width = new_width
        self.height = new_height

    def _draw_content(self):
        if not self.text:
            return

        original_clip = None

        # 更新字体
        self._update_font()

        if (self.overflow_x == self.Overflow.AUTO or
            self.overflow_y == self.Overflow.AUTO):
            self._update_width_height()

        x, y, w, h = self.content_rect()

        # 背景色填充
        if self.background_color is not None:
            pygame.draw.rect(self.surface, self.background_color, pygame.Rect(x, y, w, h))

        text_w, text_h = self.text_size
        
        if not self.text or not self._font:
            return
        
        need_clip = ((self.overflow_x == self.Overflow.HIDE and text_w > w) or
                     (self.overflow_y == self.Overflow.HIDE and text_h > h))
        
        if need_clip:
            original_clip = self.surface.get_clip()
            clip_rect = pygame.Rect(x, y, w, h)
            self.surface.set_clip(clip_rect)
        
        # 获取文本颜色
        color = self.text_color or self.palette.TEXT_PRIMARY
        
        lines = self.text.split('\n')
        _, line_height = self._font.size(' ')
        
        # 计算垂直对齐起始位置
        if self.align_y == self.Align.BEGIN:
            start_y = y
        elif self.align_y == self.Align.CENTER:
            start_y = y + (h - text_h) // 2
        else:
            start_y = y + h - text_h
        
        current_y = start_y
        for line in lines:
            if line:
                # 每帧直接渲染文本
                line_surface = self._font.render(line, True, color)
                line_width, line_height = line_surface.get_size()
                
                # 计算水平对齐位置
                if self.align_x == self.Align.BEGIN:
                    line_x = x
                elif self.align_x == self.Align.CENTER:
                    line_x = x + (w - line_width) // 2
                else:
                    line_x = x + w - line_width
                
                self.surface.blit(line_surface, (line_x, current_y))
                current_y += line_height
            else:
                current_y += line_height
        
        if need_clip:
            self.surface.set_clip(original_clip)

    def _get_font(self) -> pygame.font.Font:
        """获取字体样式"""
        font_candidates = [self.font_name, *self.FONT_FALLBACK]
        font = None
        
        for font_name in font_candidates:
            if font_name is None:
                continue
            try:
                font = pygame.font.SysFont(font_name, self.font_size, bold=self.bold, italic=self.italic)
                break
            except pygame.error:
                continue
        
        if font is None:
            font = pygame.font.Font(None, self.font_size)
            # 对于默认字体，尝试应用样式
            if self.bold or self.italic:
                try:
                    font.set_bold(self.bold)
                    font.set_italic(self.italic)
                except pygame.error:
                    pass
        
        return font