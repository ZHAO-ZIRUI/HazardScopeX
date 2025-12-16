import pygame
from typing import Tuple, Any
from pydantic import Field, PrivateAttr

from shared.pygame import PgColor, PgWidget, PgRect, PgSpacing, PgAlign, PgOverflow


class PgText(PgWidget):
    """PgApp 的文本控件"""

    # 字体候选列表, 按顺序回退查找
    FONT_FALLBACK: list[str] = [
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
        "sans-serif",
    ]

    # 文本与样式配置
    text: str = Field()
    color_text: tuple[int, int, int, int] | None = Field(default=None)
    bold: bool = Field(default=False)
    italic: bool = Field(default=False)
    font_name: str | None = Field(default=None)
    font_size: int = Field(default=16, ge=1)

    # 布局与溢出
    align_x: PgAlign = Field(default=PgAlign.BEGIN)
    align_y: PgAlign = Field(default=PgAlign.CENTER)
    overflow_x: PgOverflow = Field(default=PgOverflow.HIDE)
    overflow_y: PgOverflow = Field(default=PgOverflow.HIDE)

    # 闪烁
    blink_text: bool = Field(default=False)
    blink_border: bool = Field(default=False)
    blink_dim_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    blink_duration: int = Field(default=30, ge=1)

    # 运行时缓存
    _font: pygame.font.Font | None = PrivateAttr(default=None)
    _cache_font_key: str = PrivateAttr(default="")
    _count_frame: int = PrivateAttr(default=0)
    _cache_color_text: tuple[int, int, int, int] | None = PrivateAttr(default=None)
    _cache_color_border: tuple[int, int, int, int] | None = PrivateAttr(default=None)

    @property
    def text_size(self) -> Tuple[int, int]:
        """实时计算文本尺寸"""
        if not self.text or self._font is None:
            return 0, 0

        lines = self.text.split("\n")
        max_width = 0
        total_height = 0

        for line in lines:
            if line:
                line_width, line_height = self._font.size(line)
                max_width = max(max_width, line_width)
                total_height += line_height
            else:
                # 空行按空格高度计算
                _, line_height = self._font.size(" ")
                total_height += line_height

        return max_width, total_height

    def __init_widgets__(self) -> None:
        """初始化控件"""
        return

    def model_post_init(self, __context: Any) -> None:
        """模型初始化完成回调"""
        super().model_post_init(__context)
        self._update_font()

    def draw(self) -> None:
        """
        绘制控件, 增加闪烁支持:
        - 在调用父类 ``draw`` 之前根据闪烁状态临时修改文本与边框颜色
        - 在绘制完成后还原原始颜色, 避免产生副作用
        """
        self._count_frame += 1

        # 备份当前颜色
        self._cache_color_text = self.color_text
        self._cache_color_border = self.color_border

        blink_cycle = self.blink_duration * 2
        phase = self._count_frame % blink_cycle

        # 文本闪烁
        if self.blink_text:
            base_text_color = self._cache_color_text or PgColor.TEXT
            if phase >= self.blink_duration:
                # 使用变暗后的颜色
                self.color_text = PgColor.dim(base_text_color, self.blink_dim_ratio)

        # 边框闪烁
        if self.blink_border:
            base_border_color = self._cache_color_border or PgColor.BORDER
            if phase >= self.blink_duration:
                self.color_border = PgColor.dim(base_border_color, self.blink_dim_ratio)

        # 执行原有绘制流程
        super().draw()

        # 还原颜色, 保证外部状态不被修改
        self.color_text = self._cache_color_text
        self.color_border = self._cache_color_border

    def _update_font(self) -> None:
        """根据当前样式更新字体缓存"""
        font_key = f"{self.font_name}_{self.font_size}_{self.bold}_{self.italic}"
        if self._cache_font_key == font_key:
            return
        self._font = self._get_font()
        self._cache_font_key = font_key

    def _get_font(self) -> pygame.font.Font:
        """获取字体样式"""
        # 确保字体子系统已初始化
        if not pygame.font.get_init():
            pygame.font.init()

        font_candidates: list[str | None] = [self.font_name, *self.FONT_FALLBACK]
        font: pygame.font.Font | None = None

        for name in font_candidates:
            if not name:
                continue
            try:
                font = pygame.font.SysFont(
                    name,
                    self.font_size,
                    bold=self.bold,
                    italic=self.italic,
                )
                break
            except pygame.error:
                continue

        if font is None:
            # 使用默认字体兜底
            font = pygame.font.Font(None, self.font_size)
            # 对于默认字体尝试设置样式, 某些平台可能不支持
            try:
                font.set_bold(self.bold)
                font.set_italic(self.italic)
            except pygame.error:
                pass

        return font

    def _update_width_height(self) -> None:
        """根据 EXTEND 溢出策略自动更新控件尺寸"""
        if not self.text or self._font is None:
            return

        text_w, text_h = self.text_size

        # 当前内容区域尺寸
        content_rect: PgRect = self.content_rect
        content_w = content_rect.width
        content_h = content_rect.height

        # 计算 padding/border 占用
        padding: PgSpacing = self.padding
        border: PgSpacing = self.border
        pad_top, pad_bottom, pad_left, pad_right = padding()
        bor_top, bor_bottom, bor_left, bor_right = border()

        extra_w = pad_left + pad_right + bor_left + bor_right
        extra_h = pad_top + pad_bottom + bor_top + bor_bottom

        new_width = self.rect.width
        new_height = self.rect.height

        if self.overflow_x is PgOverflow.EXTEND and text_w > content_w:
            new_width = text_w + extra_w

        if self.overflow_y is PgOverflow.EXTEND and text_h > content_h:
            new_height = text_h + extra_h

        if new_width != self.rect.width or new_height != self.rect.height:
            self.rect = PgRect(
                x=self.rect.x,
                y=self.rect.y,
                width=new_width,
                height=new_height,
            )

    def _draw_content(self) -> None:
        """绘制文本内容"""
        if not self.text:
            return

        # 确保字体可用
        self._update_font()
        if self._font is None:
            return

        # 根据 EXTEND 溢出策略调整尺寸
        if (
            self.overflow_x is PgOverflow.EXTEND
            or self.overflow_y is PgOverflow.EXTEND
        ):
            self._update_width_height()

        # 内容绘制区域
        x, y, w, h = self.content_rect

        text_w, text_h = self.text_size
        if text_w == 0 or text_h == 0:
            return

        # 计算是否需要裁剪
        need_clip = (
            (self.overflow_x is PgOverflow.HIDE and text_w > w)
            or (self.overflow_y is PgOverflow.HIDE and text_h > h)
        )

        original_clip = None
        if need_clip:
            surface = self.surface
            original_clip = surface.get_clip()
            surface.set_clip(pygame.Rect(x, y, w, h))

        # 文本颜色
        color = self.color_text or PgColor.TEXT

        lines = self.text.split("\n")
        _, line_height = self._font.size(" ")

        # 垂直起始位置
        if self.align_y is PgAlign.BEGIN:
            start_y = y
        elif self.align_y is PgAlign.CENTER:
            start_y = y + (h - text_h) // 2
        else:
            start_y = y + h - text_h

        current_y = start_y
        surface = self.surface

        for line in lines:
            if line:
                line_surface = self._font.render(line, True, color)
                line_width, lh = line_surface.get_size()

                # 水平对齐
                if self.align_x is PgAlign.BEGIN:
                    line_x = x
                elif self.align_x is PgAlign.CENTER:
                    line_x = x + (w - line_width) // 2
                else:
                    line_x = x + w - line_width

                surface.blit(line_surface, (line_x, current_y))
                current_y += lh
            else:
                current_y += line_height

        if need_clip and original_clip is not None:
            surface.set_clip(original_clip)