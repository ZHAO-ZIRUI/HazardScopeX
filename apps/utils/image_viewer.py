import argparse
import logging
import numpy as np
import pygame
import time
from typing import Any
from pydantic import Field, PrivateAttr
from collections import deque
from multiprocessing.shared_memory import SharedMemory

from core.pygame import *
from core.data import Image
from core.utils import LogUtils, SharedMemoryUtils

class DebugImageGenerator:
    """
    测试用图像, 使用生成器模式
    """
    def __init__(self,
                 width: int = 200,
                 height: int = 100):
        self._width = width
        self._height = height
        self._frame_id = 0

    def __iter__(self):
        return self

    def __next__(self):
        self._frame_id += 1
        return Image(
            size_width=self._width,
            size_height=self._height,
            data_format=Image.Format.RGBA8,
            data=self._create_image_data(self._frame_id),
            frame_id=self._frame_id,
            timestamp_sim=time.perf_counter(),
        )

    def _create_image_data(self, phase: int = 0) -> np.ndarray:
        """
        生成测试用图像数据
        :param phase: 渐变色的相位偏移
        :return: ``(height, width, 4)`` 的 RGBA 图像数据
        """
        width, height = self._width, self._height
        # 斜对角线渐变（TL->BR）
        yy, xx = np.meshgrid(
            np.linspace(-1.0, 1.0, height, dtype=np.float32),
            np.linspace(-1.0, 1.0, width, dtype=np.float32),
            indexing='ij')
        inv_sqrt2 = 0.70710678118  # 1/sqrt(2)
        proj = (xx + yy) * inv_sqrt2
        ortho = (xx - yy) * inv_sqrt2

        # 平滑插值权重
        t = np.clip((proj + 1.0) * 0.5, 0.0, 1.0)
        t = t * t * (3.0 - 2.0 * t)

        # 相位驱动的柔和彩色
        theta = float(phase) * 0.12
        offsets = np.array([0.0, 2.09439510239, 4.18879020478], dtype=np.float32)  # 0, 120°, 240°
        sinv = np.sin(theta + offsets)
        c0 = 127.5 * (1.0 + sinv)
        c1 = 0.85 * (255.0 - c0)

        # 正交方向轻微衰减
        vignette = 1.0 - 0.10 * (ortho * ortho)
        rgb = ((1.0 - t)[..., None] * c0 + t[..., None] * c1) * vignette[..., None]
        rgb = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
        alpha = np.full((height, width, 1), 255, dtype=np.uint8)
        data = np.concatenate([rgb, alpha], axis=2)

        # 角点颜色（基于相位），其余像素保持原绘制
        p = int(phase) & 0xFF
        data[0, 0, :3] = (p, 0, 0)
        data[0, width - 1, :3] = (0, (p * 3) & 0xFF, 0)
        data[height - 1, width - 1, :3] = ((p * 7) & 0xFF, (p * 11) & 0xFF, (p * 13) & 0xFF)

        # 中心白矩形
        center_y, center_x = height // 2, width // 2
        rect_h, rect_w = 50, 80
        y_slice = slice(center_y - rect_h // 2, center_y + rect_h // 2)
        x_slice = slice(center_x - rect_w // 2, center_x + rect_w // 2)
        data[y_slice, x_slice, :3] = 255

        # 内部 RGB 色条
        inner_margin = 6
        inner_x0 = center_x - rect_w // 2 + inner_margin
        inner_y0 = center_y - rect_h // 2 + inner_margin
        inner_x1 = center_x + rect_w // 2 - inner_margin
        inner_y1 = center_y + rect_h // 2 - inner_margin
        inner_w = max(0, inner_x1 - inner_x0)
        inner_h = max(0, inner_y1 - inner_y0)

        if inner_w > 0 and inner_h > 0:
            bar_w = max(1, inner_w // 3)
            # RGB 三段色条
            data[inner_y0:inner_y0 + inner_h, inner_x0:inner_x0 + bar_w, :3] = (255, 0, 0)
            gx0 = inner_x0 + bar_w
            data[inner_y0:inner_y0 + inner_h, gx0:gx0 + bar_w, :3] = (0, 255, 0)
            bx0 = inner_x0 + 2 * bar_w
            data[inner_y0:inner_y0 + inner_h, bx0:bx0 + bar_w, :3] = (0, 0, 255)

            # “RGB” 点阵字母
            glyphs = {
                'R': ["11110", "10001", "10001", "11110", "10100", "10010", "10001"], 
                'G': ["01111", "10000", "10000", "10111", "10001", "10001", "01111"], 
                'B': ["11110", "10001", "10001", "11110", "10001", "10001", "11110"]
            }

            label_scale = 2
            glyph_w = 5 * label_scale
            glyph_h = 7 * label_scale

            # 字母顶边
            label_y = max(0, min(inner_y1 - glyph_h, inner_y0 + 2))

            # 计算字母左边界
            r_left = max(inner_x0, min(inner_x1 - glyph_w, inner_x0 + bar_w // 2 - glyph_w // 2))
            g_left = max(inner_x0, min(inner_x1 - glyph_w, gx0 + bar_w // 2 - glyph_w // 2))
            b_left = max(inner_x0, min(inner_x1 - glyph_w, bx0 + bar_w // 2 - glyph_w // 2))

            # 放大点阵并掩码绘制
            for ch, left in (("R", r_left), ("G", g_left), ("B", b_left)):
                pattern = np.array([[c == '1' for c in row] for row in glyphs[ch]], dtype=bool)
                glyph_img = np.kron(pattern, np.ones((label_scale, label_scale), dtype=bool))

                y0 = label_y
                x0 = left
                y1 = min(height, y0 + glyph_img.shape[0])
                x1 = min(width, x0 + glyph_img.shape[1])
                if y0 < y1 and x0 < x1:
                    gy0 = 0
                    gx0i = 0
                    if y0 < 0:
                        gy0 = -y0
                        y0 = 0
                    if x0 < 0:
                        gx0i = -x0
                        x0 = 0
                    submask = glyph_img[gy0:gy0 + (y1 - y0), gx0i:gx0i + (x1 - x0)]
                    data[y0:y1, x0:x1, 0:3][submask] = 0

        return np.ascontiguousarray(data)

class ImageViewer(PgApp):

    show_grid_debug: bool = Field(default=False)
    no_debug_image: bool = Field(default=False)
    shm_topic: str | None = Field(default=None)

    W_GRID: PgGrid = None
    W_DEBUG_BOX: PgWidget = None
    W_IMAGE: PgWidget = None
    W_CONNECTION_TEXT: PgTextStatic = None
    W_CONNECTION_VAL: PgTextValue = None
    W_SHM_TEXT: PgTextStatic = None
    W_SHM_VAL: PgTextValue = None
    W_TYPE_TEXT: PgTextStatic = None
    W_TYPE_VAL: PgTextValue = None
    W_SIZE_TEXT: PgTextStatic = None
    W_SIZE_VAL: PgTextValue = None
    W_FRAME_TEXT: PgTextStatic = None
    W_FRAME_VAL: PgTextValue = None
    W_FPS_IMG_TEXT: PgTextStatic = None
    W_FPS_IMG_VAL: PgTextValue = None
    W_FPS_WINDOWS_TEXT: PgTextStatic = None
    W_FPS_WINDOWS_VAL: PgTextValue = None
    W_TS_IMG_SIM_TEXT: PgTextStatic = None
    W_TS_IMG_SIM_VAL: PgTextValue = None
    W_TS_IMG_OS_TEXT: PgTextStatic = None
    W_TS_IMG_OS_VAL: PgTextValue = None
    W_TS_DELTA_MAX_TEXT: PgTextStatic = None
    W_TS_DELTA_MAX_VAL: PgTextValue = None
    W_TS_DELTA_AVG_TEXT: PgTextStatic = None
    W_TS_DELTA_AVG_VAL: PgTextValue = None
    W_TS_THIS_OS_TEXT: PgTextStatic = None
    W_TS_THIS_OS_VAL: PgTextValue = None
    W_TS_COMM_DELAY_TEXT: PgTextStatic = None
    W_TS_COMM_DELAY_VAL: PgTextValue = None
    W_HELP_TEXT: PgTextStatic = None

    _debug_image_gen: DebugImageGenerator = PrivateAttr()
    _image: Image = PrivateAttr(default=None)
    _image_display: Image = PrivateAttr(default=None)
    _img_prev_ts_os: float = PrivateAttr(default=None)
    _img_frame_id_last: int = PrivateAttr(default=None)
    _img_dt_ring: deque = PrivateAttr(default_factory=lambda: deque(maxlen=120))
    _img_fps: float = PrivateAttr(default=0.0)
    _img_dt_max: float = PrivateAttr(default=0.0)
    _img_dt_avg: float = PrivateAttr(default=0.0)

    _shm: SharedMemory | None = PrivateAttr(default=None)

    def model_post_init(self, context: Any, /) -> None:
        super().model_post_init(context)
        self._debug_image_gen = DebugImageGenerator(width=200, height=100)
        if not self.no_debug_image:
            self._image_display = next(self._debug_image_gen)

    def _init_widgets(self):
        self.W_GRID = PgGrid(
            surface=self._screen,
            position=(0, 0),
            width=self.width,
            height=self.height,
            show=self.show_grid_debug,
        )

        # 主图像
        self.W_IMAGE = PgImage(
            surface=self._screen,
            position=self.W_GRID.get_position(0, 0),
            width=self.W_GRID.content_width,
            height=self.W_GRID.content_height,
            image=self._image_display,
        )

        # 调试信息框
        self.W_DEBUG_BOX = PgBox(
            surface=self._screen,
            position=self.W_GRID.get_position(0, 0),
            width=100,
            height= self.W_GRID.row_interval * 15,
            margin_bg_color=PgPalette.alpha(self.palette.BLACK, 0.4).RGBA,
            z_index=1
        )

        # 调试数据
        self.W_SHM_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(0, 0),
            text="SHM TOPIC:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_SHM_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(0, 5),
            text="-",
            status=PgTextValue.Status.DANGER,
            height=self.W_GRID.row_interval,
            bold=True,
            z_index=2,
        )

        self.W_CONNECTION_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(1, 0),
            text="CONNECTION:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_CONNECTION_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(1, 5),
            text="-",
            status=PgTextValue.Status.DANGER,
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        self.W_TYPE_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(2, 0),
            text="FORMAT:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_TYPE_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(2, 5),
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        self.W_SIZE_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(3, 0),
            text="SIZE:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_SIZE_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(3, 5),
            text="-",
            status=PgTextValue.Status.DANGER,
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        self.W_FRAME_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(4, 0),
            text="FRAME:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_FRAME_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(4, 5),
            text="-",
            status=PgTextValue.Status.DANGER,
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        self.W_FPS_IMG_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(5, 0),
            text="FPS_IMG:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_FPS_IMG_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(5, 5),
            height=self.W_GRID.row_interval,
            text="-",
            status=PgTextValue.Status.DANGER,
            z_index=2,
        )

        self.W_FPS_WINDOWS_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(6, 0),
            text="FPS_WINDOW:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_FPS_WINDOWS_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(6, 5),
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        self.W_TS_IMG_SIM_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(7, 0),
            text="TS_IMG_SIM:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_TS_IMG_SIM_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(7, 5),
            height=self.W_GRID.row_interval,
            text="-",
            status=PgTextValue.Status.DANGER,
            z_index=2,
        )

        self.W_TS_IMG_OS_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(8, 0),
            text="TS_IMG_OS:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_TS_IMG_OS_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(8, 5),
            height=self.W_GRID.row_interval,
            text="-",
            status=PgTextValue.Status.DANGER,
            z_index=2,
        )

        self.W_TS_THIS_OS_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(9, 0),
            text="TS_THIS_OS:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_TS_THIS_OS_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(9, 5),
            height=self.W_GRID.row_interval,
            decimal_places=2,
            z_index=2,
        )

        self.W_TS_DELTA_MAX_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(10, 0),
            text="TS_DT_MAX:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_TS_DELTA_MAX_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(10, 5),
            height=self.W_GRID.row_interval,
            text="-",
            status=PgTextValue.Status.DANGER,
            decimal_places=2,
            z_index=2,
        )

        self.W_TS_DELTA_AVG_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(11, 0),
            text="TS_DT_AVG:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_TS_DELTA_AVG_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(11, 5),
            height=self.W_GRID.row_interval,
            text="-",
            status=PgTextValue.Status.DANGER,
            decimal_places=2,
            z_index=2,
        )

        self.W_TS_COMM_DELAY_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(12, 0),
            text="COMM_DELAY:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_TS_COMM_DELAY_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(12, 5),
            height=self.W_GRID.row_interval,
            text="-",
            status=PgTextValue.Status.DANGER,
            decimal_places=4,
            z_index=2,
        )

        # 调试信息帮助
        self.W_HELP_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(13, 0),
            text="""
            Press <I> to toggle info.
            Press <ECS> to quit.
            """,
            height=self.W_GRID.row_interval * 2,
            z_index=2,
        )

    def _update(self):
        # 更新 BOX 的宽度以适应内容
        self.W_DEBUG_BOX.width = max(
            self.W_CONNECTION_VAL.width,
            self.W_SHM_VAL.width,
            self.W_TYPE_VAL.width,
            self.W_SIZE_VAL.width,
            self.W_FRAME_VAL.width,
            self.W_FPS_IMG_VAL.width,
            self.W_FPS_WINDOWS_VAL.width,
            self.W_TS_IMG_SIM_VAL.width,
            self.W_TS_IMG_OS_VAL.width,
            self.W_TS_THIS_OS_VAL.width,
            100
        ) + self.W_GRID.col_interval * 5 + 10

        # 处理信息框的键盘响应
        if pygame.K_i in self._keys_released:
            for widget in self.widgets.values():
                if widget is self.W_IMAGE:
                    continue
                if widget is self.W_GRID:
                    continue
                widget.show = not widget.show

        # 图像更新
        if self.shm_topic and not self._shm:
            try:
                self._shm = SharedMemory(name=self.shm_topic)
            except FileNotFoundError:
                LogUtils.interval(2.0, token=(id(self), self.shm_topic), log_call=self._logger.warning,
                                  content=f"Trying connect to SHM topic: '{self.shm_topic}', retrying ...")
        if self._shm is not None:
            self._image = Image.try_deserialize_from_shm(self._shm)
            if self._image is None:
                self._logger.warning(f"SHM deserialize failed at topic: '{self.shm_topic}'")

        if self._image is not None:
            self._image_display = self._image
        if not self.no_debug_image and self._image is None:
            self._image_display = next(self._debug_image_gen)
        self.W_IMAGE.image = self._image_display

        # 统计（基于图像 OS 时间戳）
        self._update_image_statistics(self._image_display)

        # 基础 UI 更新
        os_time_now = time.time()
        self.W_TS_THIS_OS_VAL.text = os_time_now
        self.W_FPS_WINDOWS_VAL.text = self.window_fps

        # 与 img 有关的 UI 更新
        img = self._image_display
        status = PgTextValue.Status.NORMAL if img else PgTextValue.Status.DANGER

        items = [
            (self.W_SIZE_VAL, f"{img.size_width}x{img.size_height}" if img else "-"),
            (self.W_TYPE_VAL, img.data_format.name if img else "-"),
            (self.W_FRAME_VAL, img.frame_id if img else "-"),
            (self.W_TS_IMG_SIM_VAL, img.timestamp_sim if img else "-"),
            (self.W_TS_IMG_OS_VAL, img.timestamp_os if img else "-"),
            (self.W_FPS_IMG_VAL, self._img_fps if img else "-"),
            (self.W_TS_DELTA_MAX_VAL, self._img_dt_max if img else "-"),
            (self.W_TS_DELTA_AVG_VAL, self._img_dt_avg if img else "-"),
            (self.W_TS_COMM_DELAY_VAL, (os_time_now - img.timestamp_os) if img else "-"),
        ]
        for widget, text in items:
            widget.text = text
            widget.status = status

        # 与 SHM 有关的 UI 更新
        self.W_SHM_VAL.text = self.shm_topic if self.shm_topic else "NOT SET"
        self.W_SHM_VAL.status = PgTextValue.Status.NORMAL if self.shm_topic else PgTextValue.Status.DANGER
        self.W_CONNECTION_VAL.text = 'OK' if self._shm else 'FAILED'
        self.W_CONNECTION_VAL.status = PgTextValue.Status.NORMAL if self._shm else PgTextValue.Status.DANGER

    def _update_image_statistics(self, img: Image | None) -> None:
        if img is None:
            return
        is_new_frame = (self._img_frame_id_last != img.frame_id)
        if is_new_frame and self._img_prev_ts_os is not None:
            dt = max(0.0, img.timestamp_os - float(self._img_prev_ts_os))
            self._img_dt_ring.append(dt)
            if n := len(self._img_dt_ring):
                total = sum(self._img_dt_ring)
                self._img_dt_avg = total / n
                self._img_dt_max = max(self._img_dt_ring)
                self._img_fps = (1.0 / self._img_dt_avg) if self._img_dt_avg > 1e-9 else 0.0
        if is_new_frame:
            self._img_prev_ts_os = img.timestamp_os
            self._img_frame_id_last = img.frame_id

    def _shutdown(self):
        if self._shm:
            SharedMemoryUtils.consumer_close(self._shm)
        super()._shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Image Viewer Application")
    parser.add_argument('--debug', action='store_true', help='Enable debug grid display.')
    parser.add_argument('--debug-grid', action='store_true', help='Enable debug grid display for UI development.')
    parser.add_argument('--width', type=int, default=800, help='Window width.')
    parser.add_argument('--height', type=int, default=600, help='Window height.')
    parser.add_argument('--fps', type=int, default=30, help='Window FPS.')
    parser.add_argument('--name', type=str, default="Image Viewer", help='Window title.')
    parser.add_argument('--ros2-export-topic', type=str, default=None, help='ROS2 UI export topic name to export UI.')
    parser.add_argument('--ros2-export-node', type=str, default=None, help='ROS2 UI export node name to export UI.')
    parser.add_argument('--ros2-export-qos', type=int, default=10, help='ROS2 UI export QoS depth for topic export.')
    parser.add_argument('--ros2-export-fps', type=int, default=10, help='ROS2 UI export FPS.')
    parser.add_argument('SHM_TOPIC', type=str, nargs='?', default=None, help='Shared Memory topic name to receive image from.')
    args = parser.parse_args()

    app = ImageViewer(
        window_width=args.width,
        window_height=args.height,
        window_fps=args.fps,
        window_title=args.name,
        no_debug_image=not args.debug,
        show_grid_debug=args.debug_grid,
        logger_level=logging.DEBUG if args.debug else logging.INFO,
        ros2_export=True if args.ros2_export_topic else False,
        ros2_export_topic=args.ros2_export_topic,
        ros2_export_node_name=args.ros2_export_node,
        ros2_export_qos=args.ros2_export_qos,
        ros2_export_fps=args.ros2_export_fps,
        shm_topic=args.SHM_TOPIC,
    )
    app.run()