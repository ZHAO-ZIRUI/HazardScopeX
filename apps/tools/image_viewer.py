import argparse
import logging
import pygame
from itertools import count
from multiprocessing.shared_memory import SharedMemory

from shared.pygame import *
from shared.io import ExternalSharedMemoryManager
from shared.utils import Logging
from shared.data import Image


class ImageViewer(PgApp):
    """图像查看器"""

    def __init__(
        self,
        *,
        window_width: int = 800,
        window_height: int = 600,
        window_title: str | None = None,
        window_fps: int = 30,
        log_name: str | None = None,
        log_level: int = logging.INFO,
        ros2_topic: str | None = None,
        shm_topic: str | None = None,
        shm_domain: str | None = None,
    ):
        super().__init__(
            window_width=window_width,
            window_height=window_height,
            window_title=window_title,
            window_fps=window_fps,
            log_name=log_name,
            log_level=log_level,
            ros2_topic=ros2_topic,
        )
        self._shm: SharedMemory | None = None
        self._shm_topic = shm_topic
        self._shm_domain = shm_domain
        self._shm_manager = ExternalSharedMemoryManager()

        self._statistics_window = 1.0
        self._statistics_fps = 0.0
        self._statistics_delta_sec = 0.0
        self._statistics_timestamps: list[float] = []
        self._statistics_last_frame: int | None = None

        self._info_box_show = True

    def __post_init__(self):
        super().__post_init__()

    def update(self) -> None:
        super().update()
        self._window_title = f"Image Viewer - [ {self._shm_domain}::{self._shm_topic} ]"

        # 更新信息框显示状态
        if pygame.K_i in self._key_released:
            self._info_box_show = not self._info_box_show
        if self._info_box_show:
            self.w_info_box.show = True
        else:
            self.w_info_box.show = False

        # 在非阻塞状态下尝试获取共享内存
        if self._shm is None:
            shm = self._shm_manager.try_get_shm(self._shm_domain, self._shm_topic)
            if shm is None:
                msg = f"Waiting for shared memory '{self._shm_domain}::{self._shm_topic}' to be created ..."
                Logging.interval(5, self.logger.info, msg, 'try_get_shm')
            else:
                Logging.cancel_interval('try_get_shm')
                self.logger.info(f'Shared memory "{self._shm_domain}::{self._shm_topic}" found')
                self._shm = shm
        
        # 如果共享内存丢失, 则关闭共享内存并更新界面
        if self._shm is not None and not self._shm_manager.is_shm_exists(self._shm_domain, self._shm_topic):
            self.logger.warning(f'Shared memory "{self._shm_domain}::{self._shm_topic}" lost')
            self._shm = None
            self._shm_manager.close(self._shm)
            self.w_text_connection_v.text = "FAILED"
            self.w_text_connection_v.color_text = PgColor.DANGER
            self.w_text_source_width_v.text = "ERR"
            self.w_text_source_width_v.color_text = PgColor.DANGER
            self.w_text_source_height_v.text = "ERR"
            self.w_text_source_height_v.color_text = PgColor.DANGER
            self.w_text_source_frame_v.text = "ERR"
            self.w_text_source_frame_v.color_text = PgColor.DANGER
            self.w_text_source_timestamp_v.text = "ERR"
            self.w_text_source_timestamp_v.color_text = PgColor.DANGER
            self.w_text_statistics_fps_v.text = "ERR"
            self.w_text_statistics_fps_v.color_text = PgColor.DANGER
            self.w_text_statistics_delta_sec_v.text = "ERR"
            self.w_text_statistics_delta_sec_v.color_text = PgColor.DANGER

        # 从共享内存中获取图片
        if self._shm is not None:
            image: Image | None = Image.try_from_shm(self._shm)
            if image is not None:
                # 更新统计数据
                self._update_statistics(image)

                # 更新界面
                self.w_text_source_width_v.text = str(image.width)
                self.w_text_source_width_v.color_text = PgColor.LIME_GREEN
                self.w_text_source_height_v.text = str(image.height)
                self.w_text_source_height_v.color_text = PgColor.LIME_GREEN
                self.w_text_source_frame_v.text = str(image.sim_frame)
                self.w_text_source_frame_v.color_text = PgColor.LIME_GREEN
                self.w_text_source_timestamp_v.text = f"{image.sim_timestamp:.3f}"
                self.w_text_source_timestamp_v.color_text = PgColor.LIME_GREEN
                self.w_text_statistics_fps_v.text = f"{self._statistics_fps:.1f}"
                self.w_text_statistics_fps_v.color_text = PgColor.LIME_GREEN
                self.w_text_statistics_delta_sec_v.text = f"{self._statistics_delta_sec:.3f}"
                self.w_text_statistics_delta_sec_v.color_text = PgColor.LIME_GREEN
                self.w_text_connection_v.text = "OK"
                self.w_text_connection_v.color_text = PgColor.LIME_GREEN
                # 更新图像
                self.w_image.image = image

    def close(self) -> None:
        self._shm_manager.close()
        super().close()

    def __init_widgets__(self) -> None:
        """初始化控件"""

        info_box_width = 12
        index = iter(i for i in count() for _ in range(2))
        
        self.w_grid = PgGrid(
            rect=PgRect(x=0, y=0, width=self.width, height=self.height),
            color_grid=PgColor.INFO,
            show=False,
        )
        self.widgets.append(self.w_grid)

        self.w_image = PgImage(
            rect=PgRect(x=0, y=0, width=self.width, height=self.height),
            image=None,
            scale=PgScale.SCALE,
            show_no_data=True,
            align_x=PgAlign.CENTER,
            align_y=PgAlign.CENTER,
        )
        self.widgets.append(self.w_image)

        box_rect = self.w_grid.get_rect(0, next(index), info_box_width, -1)
        box_rect.width += 12
        self.w_info_box = PgBox(
            rect=box_rect,
            color_margin=PgColor.alpha(PgColor.DARK, 0.1),
            padding=PgSpacing(x=5),
        )
        self.widgets.append(self.w_info_box)

        self.w_text_header = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text="[ INFO ]",
            bold=True,
            align_x=PgAlign.CENTER,
        )
        self.w_info_box.add_children(self.w_text_header)
        self.widgets.append(self.w_text_header)

        self.w_text_standard = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"[STANDARD]",
            bold=True,
        )
        self.w_info_box.add_children(self.w_text_standard)
        self.widgets.append(self.w_text_standard)

        next(index) # skip

        self.w_text_shm_domain_k = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"SHM DOMAIN:",
            bold=True,
        )
        self.w_info_box.add_children(self.w_text_shm_domain_k)
        self.widgets.append(self.w_text_shm_domain_k)

        self.w_text_shm_domain_v = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"{self._shm_domain}",
            bold=True,
            align_x=PgAlign.END,
            color_text=PgColor.LIME_GREEN,
        )
        self.w_info_box.add_children(self.w_text_shm_domain_v)
        self.widgets.append(self.w_text_shm_domain_v)

        self.w_text_shm_topic_k = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"SHM TOPIC:",
            bold=True,
        )
        self.w_info_box.add_children(self.w_text_shm_topic_k)
        self.widgets.append(self.w_text_shm_topic_k)

        self.w_text_shm_topic_v = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"{self._shm_topic}",
            bold=True,
            align_x=PgAlign.END,
            color_text=PgColor.LIME_GREEN,
        )
        self.w_info_box.add_children(self.w_text_shm_topic_v)
        self.widgets.append(self.w_text_shm_topic_v)

        self.w_text_connection_k = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"CONNECTION:",
            bold=True,
        )
        self.w_info_box.add_children(self.w_text_connection_k)
        self.widgets.append(self.w_text_connection_k)

        self.w_text_connection_v = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"FAILED",
            bold=True,
            align_x=PgAlign.END,
            color_text=PgColor.DANGER,
        )
        self.w_info_box.add_children(self.w_text_connection_v)
        self.widgets.append(self.w_text_connection_v)

        self.w_text_ros_export_k = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"ROS EXPORT:",
            bold=True,
        )
        self.w_info_box.add_children(self.w_text_ros_export_k)
        self.widgets.append(self.w_text_ros_export_k)

        self.w_text_ros_export_v = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text="DISABLED" if not self._flag_ros2_enabled else f"{self._ros2_export_topic}",
            bold=True,
            align_x=PgAlign.END,
            color_text=PgColor.LIME_GREEN if self._flag_ros2_enabled else PgColor.WARNING,
        )
        self.w_info_box.add_children(self.w_text_ros_export_v)
        self.widgets.append(self.w_text_ros_export_v)

        next(index) # skip
        next(index) # skip

        self.w_text_source_k = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"[SOURCE]",
            bold=True,
        )
        self.w_info_box.add_children(self.w_text_source_k)
        self.widgets.append(self.w_text_source_k)

        next(index) # skip

        self.w_text_source_width_k = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"WIDTH:",
            bold=True,
        )
        self.w_info_box.add_children(self.w_text_source_width_k)
        self.widgets.append(self.w_text_source_width_k)

        self.w_text_source_width_v = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"ERR",
            bold=True,
            align_x=PgAlign.END,
            color_text=PgColor.DANGER,
        )
        self.w_info_box.add_children(self.w_text_source_width_v)
        self.widgets.append(self.w_text_source_width_v)

        self.w_text_source_height_k = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"HEIGHT:",
            bold=True,
        )
        self.w_info_box.add_children(self.w_text_source_height_k)
        self.widgets.append(self.w_text_source_height_k)

        self.w_text_source_height_v = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"ERR",
            bold=True,
            align_x=PgAlign.END,
            color_text=PgColor.DANGER,
        )
        self.w_info_box.add_children(self.w_text_source_height_v)
        self.widgets.append(self.w_text_source_height_v)

        self.w_text_source_frame_k = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"FRAME:",
            bold=True,
        )
        self.w_info_box.add_children(self.w_text_source_frame_k)
        self.widgets.append(self.w_text_source_frame_k)

        self.w_text_source_frame_v = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"ERR",
            bold=True,
            align_x=PgAlign.END,
            color_text=PgColor.DANGER,
        )
        self.w_info_box.add_children(self.w_text_source_frame_v)
        self.widgets.append(self.w_text_source_frame_v)

        self.w_text_source_timestamp_k = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"TIMESTAMP:",
            bold=True,
        )
        self.w_info_box.add_children(self.w_text_source_timestamp_k)
        self.widgets.append(self.w_text_source_timestamp_k)

        self.w_text_source_timestamp_v = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"ERR",
            bold=True,
            align_x=PgAlign.END,
            color_text=PgColor.DANGER,
        )
        self.w_info_box.add_children(self.w_text_source_timestamp_v)
        self.widgets.append(self.w_text_source_timestamp_v)

        next(index) # skip
        next(index) # skip

        self.w_text_statistics = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"[STATISTICS]",
            bold=True,
        )
        self.w_info_box.add_children(self.w_text_statistics)
        self.widgets.append(self.w_text_statistics)

        next(index) # skip

        self.w_text_statistics_fps_k = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"FPS:",
            bold=True,
        )
        self.w_info_box.add_children(self.w_text_statistics_fps_k)
        self.widgets.append(self.w_text_statistics_fps_k)

        self.w_text_statistics_fps_v = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"ERR",
            bold=True,
            align_x=PgAlign.END,
            color_text=PgColor.DANGER,
        )
        self.w_info_box.add_children(self.w_text_statistics_fps_v)
        self.widgets.append(self.w_text_statistics_fps_v)

        self.w_text_statistics_delta_sec_k = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"DELTA SEC:",
            bold=True,
        )
        self.w_info_box.add_children(self.w_text_statistics_delta_sec_k)
        self.widgets.append(self.w_text_statistics_delta_sec_k)

        self.w_text_statistics_delta_sec_v = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 1),
            text=f"ERR",
            bold=True,
            align_x=PgAlign.END,
            color_text=PgColor.DANGER,
        )
        self.w_info_box.add_children(self.w_text_statistics_delta_sec_v)
        self.widgets.append(self.w_text_statistics_delta_sec_v)

        for _ in range(2 * 2):
            next(index) # skip
        
        self.w_text_info_box_description_1 = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 2),
            text=f"> Press 'I' to toggle info",
            bold=True,
            align_x=PgAlign.BEGIN,
            align_y=PgAlign.BEGIN,
            overflow_x=PgOverflow.EXTEND,
            color_text=PgColor.TEXT_MUTED,
        )
        self.w_info_box.add_children(self.w_text_info_box_description_1)
        self.widgets.append(self.w_text_info_box_description_1)

        next(index) # skip

        self.w_text_info_box_description_2 = PgText(
            rect=self.w_grid.get_rect(0, next(index), info_box_width, 2),
            text=f"> Press 'ESC' to exit",
            bold=True,
            align_x=PgAlign.BEGIN,
            align_y=PgAlign.BEGIN,
            overflow_x=PgOverflow.EXTEND,
            color_text=PgColor.TEXT_MUTED,
        )
        self.w_info_box.add_children(self.w_text_info_box_description_2)
        self.widgets.append(self.w_text_info_box_description_2)

    def _update_statistics(self, image: Image) -> None:
        """
        统计最近 ``_statistics_window`` 秒内的图像 FPS 和平均时间间隔
        """
        # 仅在帧号发生变化时统计, 避免同一帧被多次读取
        frame = int(image.sim_frame)
        if self._statistics_last_frame is not None and frame == self._statistics_last_frame:
            return
        self._statistics_last_frame = frame

        ts = float(image.sim_timestamp)

        # 追加当前时间戳
        self._statistics_timestamps.append(ts)

        # 丢弃时间窗口之前的旧样本
        window = float(self._statistics_window)
        while len(self._statistics_timestamps) >= 2 and ts - self._statistics_timestamps[0] > window:
            self._statistics_timestamps.pop(0)

        # 至少需要两个样本才能计算间隔
        n = len(self._statistics_timestamps)
        if n < 2:
            return

        duration = self._statistics_timestamps[-1] - self._statistics_timestamps[0]
        if duration <= 0.0:
            # 时间戳异常，保持原有统计值
            return

        # FPS = (样本数 - 1) / 总时长
        self._statistics_fps = (n - 1) / duration
        # 平均时间差 = 总时长 / (样本间隔数)
        self._statistics_delta_sec = duration / (n - 1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--window-width', type=int, default=800)
    parser.add_argument('--window-height', type=int, default=600)
    parser.add_argument('--window-title', type=str, default='Image Viewer')
    parser.add_argument('--window-fps', type=int, default=30)
    parser.add_argument('--ros2-topic', type=str, default=None)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--shm-domain', type=str, default='hazard_scope')
    parser.add_argument('shm_topic', type=str)
    args = parser.parse_args()

    app = ImageViewer(
        window_width=args.window_width,
        window_height=args.window_height,
        window_title=args.window_title,
        window_fps=args.window_fps,
        ros2_topic=args.ros2_topic,
        log_level=logging.DEBUG if args.debug else logging.INFO,
        shm_topic=args.shm_topic,
        shm_domain=args.shm_domain,
    )
    app.run()