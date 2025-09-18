import pygame
from enum import Enum
from pydantic import Field

from core.pygame import PgWidget, PgPalette
from core.data import Image


class PgImage(PgWidget):

    class Align(Enum):
        """对齐方式"""
        BEGIN = "BEGIN"
        CENTER = "CENTER"
        END = "END"

    class Scale(Enum):
        """
        图像的缩放模式

        - SCALE: 按比例缩放，保持宽高比
        - STRETCH: 拉伸图像以填满整个区域
        - PIXEL_PERFECT: 1:1像素绘制, 图像不会缩放
        """
        SCALE = "SCALE"
        STRETCH = "STRETCH"
        PIXEL_PERFECT = "PIXEL_PERFECT"

    image: Image | None = Field(default=None, description="Image to display")
    scale: Scale = Field(default=Scale.SCALE, description="Image scaling mode")
    show_no_data: bool = Field(default=True, description="Show no data image when image is None")
    align_x: Align = Field(default=Align.CENTER, description="Horizontal alignment")
    align_y: Align = Field(default=Align.CENTER, description="Vertical alignment")

    def _draw_content(self):
        if self.image is None or self.image.data is None:
            if self.show_no_data:
                self._draw_no_data_image()
            return

        image_surface = self.image.to_pygame_surface()

        if self.scale == self.Scale.SCALE:
            self._draw_scaled(image_surface)
        elif self.scale == self.Scale.STRETCH:
            self._draw_stretched(image_surface)
        elif self.scale == self.Scale.PIXEL_PERFECT:
            self._draw_pixel_perfect(image_surface)

    def _draw_scaled(self, image_surface: pygame.Surface):
        """
        缩放模式下的绘制方法
        :param image_surface: 图像 ``pygame.Surface`` 对象, 用于处理绘制
        """
        x, y, w, h = self.content_rect

        # 计算缩放比例
        img_w, img_h = image_surface.get_size()
        scale_x = w / img_w
        scale_y = h / img_h
        scale = min(scale_x, scale_y)
        
        # 计算缩放后的尺寸
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        
        # 基于对齐方式计算绘制位置
        draw_x = self._calc_aligned_position(x, w, new_w, self.align_x)
        draw_y = self._calc_aligned_position(y, h, new_h, self.align_y)
        
        # 缩放并绘制
        scaled_surface = pygame.transform.scale(image_surface, (new_w, new_h))
        self.surface.blit(scaled_surface, (draw_x, draw_y))

    def _draw_stretched(self, image_surface: pygame.Surface):
        """
        以拉伸模式进行绘制
        :param image_surface: 图像 ``pygame.Surface`` 对象, 用于处理绘制
        """
        x, y, w, h = self.content_rect

        # 拉伸后的尺寸等于内容区域尺寸，覆盖整个区域。
        # 在该模式下对齐设置不影响绘制位置，直接从内容区域原点绘制。
        stretched_surface = pygame.transform.scale(image_surface, (w, h))
        self.surface.blit(stretched_surface, (x, y))

    def _draw_pixel_perfect(self, image_surface: pygame.Surface):
        """
        以点对点模式进行绘制
        :param image_surface: 图像 ``pygame.Surface`` 对象, 用于处理绘制
        """
        x, y, w, h = self.content_rect

        img_w, img_h = image_surface.get_size()

        # 基于对齐方式计算绘制位置
        draw_x = self._calc_aligned_position(x, w, img_w, self.align_x)
        draw_y = self._calc_aligned_position(y, h, img_h, self.align_y)

        # 直接绘制，不缩放
        self.surface.blit(image_surface, (draw_x, draw_y))

    def _calc_aligned_position(self, start: int, container_size: int, content_size: int, align: Align) -> int:
        """
        计算对齐位置的坐标, 只在特定的轴上使用
        :param start: 起始点
        :param container_size: 外部容器的总尺寸
        :param content_size: 内容的总尺寸
        :param align: 对齐方式
        :return:
        """
        if align == self.Align.BEGIN:
            return start
        if align == self.Align.CENTER:
            return start + (container_size - content_size) // 2
        return start + (container_size - content_size)

    def _draw_no_data_image(self):
        """
        绘制无数据时的默认图像（红色背景）
        """
        x, y, w, h = self.content_rect
        
        # 绘制红色背景与边框
        pygame.draw.rect(self.surface, self.palette.DANGER.RGBA, (x, y, w, h))
        pygame.draw.rect(self.surface, PgPalette.dim(self.palette.DANGER, 0.2).RGBA, (x, y, w, h), 2)
        
        # 绘制对角线
        pygame.draw.line(self.surface, self.palette.WHITE.RGBA, (x, y), (x + w, y + h), 3)
        pygame.draw.line(self.surface, self.palette.WHITE.RGBA, (x + w, y), (x, y + h), 3)