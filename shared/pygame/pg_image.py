import pygame
from typing import Any

from pydantic import Field

from shared.data.image import Image
from shared.pygame import PgWidget, PgRect, PgAlign, PgScale, PgColor


class PgImage(PgWidget):
    """用于显示图像数据的控件"""

    # 图像与显示配置
    image: Image | None = Field(default=None)
    scale: PgScale = Field(default=PgScale.SCALE)
    show_no_data: bool = Field(default=True)
    align_x: PgAlign = Field(default=PgAlign.CENTER)
    align_y: PgAlign = Field(default=PgAlign.CENTER)

    def __init_widgets__(self) -> None:
        """初始化控件"""
        return

    def _draw_content(self) -> None:
        """绘制图像内容"""
        if self.image is None:
            if self.show_no_data:
                self._draw_no_data_image()
            return

        # 将 Image 转换为 pygame.Surface
        image_surface = self._image_to_surface(self.image)
        if image_surface is None:
            if self.show_no_data:
                self._draw_no_data_image()
            return

        if self.scale is PgScale.SCALE:
            self._draw_scaled(image_surface)
        elif self.scale is PgScale.STRETCH:
            self._draw_stretched(image_surface)
        elif self.scale is PgScale.PIXEL_PERFECT:
            self._draw_pixel_perfect(image_surface)

    # region: 绘制模式
    def _draw_scaled(self, image_surface: pygame.Surface) -> None:
        """
        按比例缩放模式绘制图像, 保持宽高比
        """
        x, y, w, h = self.content_rect

        img_w, img_h = image_surface.get_size()
        if img_w == 0 or img_h == 0 or w <= 0 or h <= 0:
            return

        scale_x = w / img_w
        scale_y = h / img_h
        scale = min(scale_x, scale_y)

        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))

        draw_x = self._calc_aligned_position(x, w, new_w, self.align_x)
        draw_y = self._calc_aligned_position(y, h, new_h, self.align_y)

        scaled_surface = pygame.transform.scale(image_surface, (new_w, new_h))
        self.surface.blit(scaled_surface, (draw_x, draw_y))

    def _draw_stretched(self, image_surface: pygame.Surface) -> None:
        """
        拉伸模式: 拉伸图像以填满内容区域
        """
        x, y, w, h = self.content_rect
        if w <= 0 or h <= 0:
            return

        stretched_surface = pygame.transform.scale(image_surface, (w, h))
        self.surface.blit(stretched_surface, (x, y))

    def _draw_pixel_perfect(self, image_surface: pygame.Surface) -> None:
        """
        像素精确模式: 不缩放图像, 按 1:1 像素绘制
        """
        x, y, w, h = self.content_rect

        img_w, img_h = image_surface.get_size()
        if img_w == 0 or img_h == 0:
            return

        draw_x = self._calc_aligned_position(x, w, img_w, self.align_x)
        draw_y = self._calc_aligned_position(y, h, img_h, self.align_y)

        self.surface.blit(image_surface, (draw_x, draw_y))
    # endregion

    # region: 辅助方法
    @staticmethod
    def _image_to_surface(image: Image) -> pygame.Surface | None:
        """
        将 ``shared.data.image.Image`` 转换为 pygame.Surface
        """
        # Image._raw 为 BGRA8, 这里按 BGRA8 构造 Surface
        try:
            array = image._raw  # type: ignore[attr-defined]
            height, width, channels = array.shape
            if channels != 4:
                return None
            surface = pygame.image.frombuffer(array.tobytes(), (width, height), "BGRA")
            return surface.convert_alpha()
        except Exception:
            return None

    @staticmethod
    def _calc_aligned_position(
        start: int,
        container_size: int,
        content_size: int,
        align: PgAlign,
    ) -> int:
        """
        计算单轴上的对齐位置
        """
        if container_size <= content_size:
            return start

        if align is PgAlign.BEGIN:
            return start
        if align is PgAlign.CENTER:
            return start + (container_size - content_size) // 2
        return start + (container_size - content_size)

    def _draw_no_data_image(self) -> None:
        """
        绘制无数据时的占位图像: 红色背景 + 对角线
        """
        x, y, w, h = self.content_rect
        if w <= 0 or h <= 0:
            return

        # 背景
        pygame.draw.rect(self.surface, PgColor.DANGER, (x, y, w, h))

        # 暗一点的边框
        dim_border = PgColor.dim(PgColor.DANGER, 0.2)
        pygame.draw.rect(self.surface, dim_border, (x, y, w, h), 2)

        # 对角线
        pygame.draw.line(self.surface, PgColor.WHITE, (x, y), (x + w, y + h), 3)
        pygame.draw.line(self.surface, PgColor.WHITE, (x + w, y), (x, y + h), 3)
    # endregion


