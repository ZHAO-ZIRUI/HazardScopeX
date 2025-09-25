import argparse
import logging
import math
import time
import numpy as np
import pygame
from typing import Any
from pydantic import Field, PrivateAttr
from multiprocessing.shared_memory import SharedMemory

from core.pygame import *
from core.data.point_cloud import PointCloud
from core.utils import LogUtils, SharedMemoryUtils
from enum import Enum


class DebugPointCloudGenerator:
    """
    调试用点云生成器
    """

    def __init__(self, channels: int = 128, points_per_channel: int = 300):
        self._channels = channels
        self._ppc = points_per_channel
        self._frame_id = 0
        # 调试点云的生成半径范围
        self._r_min = 2.0
        self._r_max = 20.0

    def __iter__(self):
        return self

    def __next__(self) -> PointCloud:
        self._frame_id += 1
        t = self._frame_id * 0.02  # 每帧间隔约 20ms, 用于动画效果计算
        data = self._create_frame(t)
        return PointCloud(
            data_channels=self._channels,
            data_format=PointCloud.Format.XYZ_Intensity_Channel,
            data=data,
            frame_id=self._frame_id,
            timestamp_sim=time.perf_counter(),
        )

    def _create_frame(self, t: float) -> np.ndarray:
        """
        生成一帧点云数据，形状为 (channels*ppc, 5): (x, y, z, intensity, channel)
        """
        channels = self._channels
        ppc = self._ppc

        # 点数据缓存
        x_list = []
        y_list = []
        z_list = []
        intensity_list = []
        channel_list = []

        for ch in range(channels):
            # 半径
            r = float(max(1, channels - 1))
            r_base = self._r_min + (ch / r) * (self._r_max - self._r_min)
            r_scale = 1.0 + 0.2 * math.sin(1.5 * t)
            r = r_base * r_scale

            # 高度 Z 轴
            z_min, z_max = -2.0, 5.0
            z_base = z_min + (ch / r) * (z_max - z_min)
            wobble = 0.2 * float(np.sin(0.1 * r + t))

            # 生成圆形分布的角度
            theta = np.linspace(0, 2.0 * math.pi, ppc, endpoint=False, dtype=np.float32)
            theta += t * 0.5

            # 生成点云
            x_ch = r * np.cos(theta)
            y_ch = r * np.sin(theta)
            z_ch = np.full(ppc, np.clip(z_base + wobble, z_min, z_max), dtype=np.float32)
            x_list.extend(x_ch)
            y_list.extend(y_ch)
            z_list.extend(z_ch)
            intensity_list.extend([1.0] * ppc)
            channel_list.extend([float(ch)] * ppc)

        # 转换为numpy数组
        x = np.array(x_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.float32)
        z = np.array(z_list, dtype=np.float32)
        intensity = np.array(intensity_list, dtype=np.float32)
        channel_ids = np.array(channel_list, dtype=np.float32)
        pcd= np.stack([x, y, z, intensity, channel_ids], axis=1)
        return np.ascontiguousarray(pcd)


class HelpModelBox(PgContainer):

    def model_post_init(self, context: Any, /) -> None:
        super().model_post_init(context)

        self.border = 2
        self.margin = 8
        self.margin_bg_color = self.palette.LIGHT_GRAY.RGBA
        self.border_color = self.palette.BLACK.RGBA

        header = PgTextStatic(
            surface=self.surface,
            position=(self.content_rect[0], self.content_rect[1]),
            bold=True,
            width=self.content_rect[2],
            height=24,
            text='[ HELPS ]',
            text_color=self.palette.BLACK.RGBA,
            align_x=PgText.Align.CENTER,
        )
        content_text = """
        CONTROLS:
         - Mouse Drag: Orbit camera
         - W/S/A/D: Camera position
         - Arrow Keys: Camera rotate
         - Q/E: Camera height up/down
         - R/F: Zoom in/out
         - +/-: Point size
         - C: Cycle color mode
         - SPACE: Reset camera
         - I: Toggle info display
         - H: Show/Hide this help
         - ESC: Exit
        """
        content = PgTextStatic(
            surface=self.surface,
            position=(self.content_rect[0], self.content_rect[1] + 24),
            bold=True,
            width=self.content_rect[2],
            height=self.content_rect[3] - 24,
            text=content_text.strip('\n'),
            text_color=self.palette.BLACK.RGBA,
            align_y=PgText.Align.BEGIN,
        )

        self.add_widget(header)
        self.add_widget(content)


class CloudViewer(PgApp):
    
    class ColorMode(Enum):
        """点云显示模式"""
        WHITE = "WHITE"
        HEIGHT = "HEIGHT"
        CHANNEL = "CHANNEL"

    show_grid_debug: bool = Field(default=False)
    no_debug_pcd: bool = Field(default=True)
    point_size: int = Field(default=2)
    color_mode: ColorMode = Field(default=ColorMode.CHANNEL)
    
    # 相机默认状态参数
    CAMERA_DEFAULT_TARGET: tuple[float, float, float] = Field(default=(0.0, 0.0, 0.0))
    CAMERA_DEFAULT_YAW: float = Field(default=45.0)
    CAMERA_DEFAULT_PITCH: float = Field(default=-20.0)
    CAMERA_DEFAULT_DISTANCE: float = Field(default=10.0)

    W_GRID: PgGrid = None
    W_DEBUG_BOX: PgWidget = None
    W_CONNECTION_TEXT: PgTextStatic = None
    W_CONNECTION_VAL: PgTextValue = None
    W_FORMAT_TEXT: PgTextStatic = None
    W_FORMAT_VAL: PgTextValue = None
    W_COLORMODE_TEXT: PgTextStatic = None
    W_COLORMODE_VAL: PgTextValue = None
    W_CHANNELS_TEXT: PgTextStatic = None
    W_CHANNELS_VAL: PgTextValue = None
    W_POINTS_TEXT: PgTextStatic = None
    W_POINTS_VAL: PgTextValue = None
    W_FRAME_TEXT: PgTextStatic = None
    W_FRAME_VAL: PgTextValue = None
    W_FPS_PCD_TEXT: PgTextStatic = None
    W_FPS_PCD_VAL: PgTextValue = None
    W_FPS_WINDOW_TEXT: PgTextStatic = None
    W_FPS_WINDOW_VAL: PgTextValue = None
    W_TS_PCD_SIM_TEXT: PgTextStatic = None
    W_TS_PCD_SIM_VAL: PgTextValue = None
    W_TS_PCD_OS_TEXT: PgTextStatic = None
    W_TS_PCD_OS_VAL: PgTextValue = None
    W_TS_THIS_OS_TEXT: PgTextStatic = None
    W_TS_THIS_OS_VAL: PgTextValue = None
    W_TS_DT_MAX_TEXT: PgTextStatic = None
    W_TS_DT_MAX_VAL: PgTextValue = None
    W_TS_DT_AVG_TEXT: PgTextStatic = None
    W_TS_DT_AVG_VAL: PgTextValue = None
    W_COMM_DELAY_TEXT: PgTextStatic = None
    W_COMM_DELAY_VAL: PgTextValue = None
    W_CAM_ZOOM_TEXT: PgTextStatic = None
    W_CAM_ZOOM_VAL: PgTextValue = None
    W_CAM_DEG_TEXT: PgTextStatic = None
    W_CAM_DEG_VAL: PgTextValue = None
    W_CAM_POSE_TEXT: PgTextStatic = None
    W_CAM_POSE_VAL: PgTextValue = None
    W_HELP_TEXT: PgTextStatic = None
    W_HELP_MODAL: PgContainer = None

    _debug_pcd_gen: DebugPointCloudGenerator = PrivateAttr()
    _pcd: PointCloud | None = PrivateAttr(default=None)
    _pcd_prev_ts_os: float | None = PrivateAttr(default=None)
    _pcd_frame_id_last: int | None = PrivateAttr(default=None)
    _pcd_dt_ring: list[float] = PrivateAttr(default_factory=list)
    _pcd_fps: float = PrivateAttr(default=0.0)
    _pcd_dt_max: float = PrivateAttr(default=0.0)
    _pcd_dt_avg: float = PrivateAttr(default=0.0)

    # SHM 帧数统计
    _shm_frame_count: int = PrivateAttr(default=0)
    _shm_last_stats_time: float = PrivateAttr(default=0.0)

    # 相机状态
    _cam_target: np.ndarray = PrivateAttr()
    _cam_yaw: float = PrivateAttr()
    _cam_pitch: float = PrivateAttr()
    _cam_dist: float = PrivateAttr()

    # 交互状态
    _dragging: bool = PrivateAttr(default=False)
    _drag_prev: tuple[int, int] | None = PrivateAttr(default=None)
    _mouse_prev_buttons: tuple[bool, bool, bool] = PrivateAttr(default_factory=lambda: (False, False, False))
    _mouse_prev_pos: tuple[int, int] | None = PrivateAttr(default=None)
    _shm: SharedMemory | None = PrivateAttr(default=None)
    shm_topic: str | None = Field(default=None)

    def model_post_init(self, context: Any, /) -> None:
        super().model_post_init(context)
        self._debug_pcd_gen = DebugPointCloudGenerator()
        
        # 初始化相机状态
        self._cam_target = np.array(self.CAMERA_DEFAULT_TARGET, dtype=np.float32)
        self._cam_yaw = self.CAMERA_DEFAULT_YAW
        self._cam_pitch = self.CAMERA_DEFAULT_PITCH
        self._cam_dist = self.CAMERA_DEFAULT_DISTANCE
        
        if not self.no_debug_pcd:
            self._logger.warning("Debug point cloud generator enabled - synthetic test point clouds will be displayed")
        
        if self.show_grid_debug:
            self._logger.warning("Grid debug mode enabled - you will see some grid points for UI development")
        
        if not self.shm_topic:
            self._logger.warning("SHM TOPIC is empty - no data will be received from shared memory")

    def _init_widgets(self):
        # 主网格
        self.W_GRID = PgGrid(
            surface=self._screen,
            position=(0, 0),
            width=self.width,
            height=self.height,
            show=self.show_grid_debug,
        )

        # 信息显示框
        self.W_DEBUG_BOX = PgBox(
            surface=self._screen,
            position=self.W_GRID.get_position(0, 0),
            width=100,
            height=self.W_GRID.row_interval * 19,
            margin_bg_color=PgPalette.alpha(self.palette.BLACK, 0.4).RGBA,
            z_index=1,
        )

        # CONNECTION
        self.W_CONNECTION_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(0, 0),
            text="CONNECTION:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_CONNECTION_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(0, 5),
            text="-",
            status=PgTextValue.Status.DANGER,
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        # FORMAT
        self.W_FORMAT_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(1, 0),
            text="FORMAT:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_FORMAT_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(1, 5),
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        # COLORMODE
        self.W_COLORMODE_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(2, 0),
            text="COLORMODE:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_COLORMODE_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(2, 5),
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        # CHANNELS
        self.W_CHANNELS_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(3, 0),
            text="CHANNELS:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_CHANNELS_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(3, 5),
            text="-",
            status=PgTextValue.Status.DANGER,
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        # POINTS
        self.W_POINTS_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(4, 0),
            text="POINTS:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_POINTS_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(4, 5),
            text="-",
            status=PgTextValue.Status.DANGER,
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        # FRAME
        self.W_FRAME_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(5, 0),
            text="FRAME:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_FRAME_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(5, 5),
            text="-",
            status=PgTextValue.Status.DANGER,
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        # FPS_PCD
        self.W_FPS_PCD_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(6, 0),
            text="FPS_PCD:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_FPS_PCD_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(6, 5),
            height=self.W_GRID.row_interval,
            text="-",
            status=PgTextValue.Status.DANGER,
            z_index=2,
        )

        # FPS_WINDOW
        self.W_FPS_WINDOW_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(7, 0),
            text="FPS_WINDOW:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_FPS_WINDOW_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(7, 5),
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        # TS_PCD_SIM
        self.W_TS_PCD_SIM_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(8, 0),
            text="TS_PCD_SIM:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_TS_PCD_SIM_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(8, 5),
            text="-",
            status=PgTextValue.Status.DANGER,
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        # TS_PCD_OS
        self.W_TS_PCD_OS_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(9, 0),
            text="TS_PCD_OS:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_TS_PCD_OS_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(9, 5),
            text="-",
            status=PgTextValue.Status.DANGER,
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        # TS_THIS_OS
        self.W_TS_THIS_OS_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(10, 0),
            text="TS_THIS_OS:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_TS_THIS_OS_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(10, 5),
            height=self.W_GRID.row_interval,
            decimal_places=2,
            z_index=2,
        )

        # TS_DT_MAX
        self.W_TS_DT_MAX_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(11, 0),
            text="TS_DT_MAX:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_TS_DT_MAX_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(11, 5),
            text="-",
            status=PgTextValue.Status.DANGER,
            height=self.W_GRID.row_interval,
            decimal_places=2,
            z_index=2,
        )

        # TS_DT_AVG
        self.W_TS_DT_AVG_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(12, 0),
            text="TS_DT_AVG:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_TS_DT_AVG_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(12, 5),
            text="-",
            status=PgTextValue.Status.DANGER,
            height=self.W_GRID.row_interval,
            decimal_places=2,
            z_index=2,
        )

        # COMM_DELAY
        self.W_COMM_DELAY_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(13, 0),
            text="COMM_DELAY:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_COMM_DELAY_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(13, 5),
            text="-",
            status=PgTextValue.Status.DANGER,
            height=self.W_GRID.row_interval,
            decimal_places=4,
            z_index=2,
        )

        # CAM_ZOOM
        self.W_CAM_ZOOM_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(14, 0),
            text="CAM_ZOOM:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_CAM_ZOOM_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(14, 5),
            text="-",
            status=PgTextValue.Status.NORMAL,
            height=self.W_GRID.row_interval,
            decimal_places=1,
            z_index=2,
        )

        # CAM_DEG
        self.W_CAM_DEG_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(15, 0),
            text="CAM_DEG:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_CAM_DEG_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(15, 5),
            text="-",
            status=PgTextValue.Status.NORMAL,
            height=self.W_GRID.row_interval,
            z_index=2,
        )

        # CAM_POSE
        self.W_CAM_POSE_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(16, 0),
            text="CAM_POSE:",
            height=self.W_GRID.row_interval,
            z_index=2,
        )
        self.W_CAM_POSE_VAL = PgTextValue(
            surface=self._screen,
            position=self.W_GRID.get_position(16, 5),
            text="-",
            status=PgTextValue.Status.NORMAL,
            height=self.W_GRID.row_interval,
            decimal_places=1,
            z_index=2,
        )

        # HELP
        self.W_HELP_TEXT = PgTextStatic(
            surface=self._screen,
            position=self.W_GRID.get_position(17, 0),
            text="""
            Press <I> to toggle info.
            Press <H> for help.
            Press <ESC> to quit.
            """,
            height=self.W_GRID.row_interval * 3,
            z_index=2,
        )

        # 帮助模态框
        self.W_HELP_MODAL = HelpModelBox(
            surface=self._screen,
            position=self.W_GRID.get_position(6, 8),
            width=self.W_GRID.col_interval * 17,
            height=self.W_GRID.row_interval * 14,
            show=False,
            z_index=100,
        )
        self.widgets["HELP_MODAL"] = self.W_HELP_MODAL

    def _update(self):
        # 处理用户输入
        self._handle_input()

        # 准备 SHM 连接
        if self.shm_topic and not self._shm:
            try:
                self._shm = SharedMemory(name=self.shm_topic)
            except FileNotFoundError:
                LogUtils.interval(2.0, token=(id(self), self.shm_topic), log_call=self._logger.warning,
                                  content=f"Trying connect to SHM topic: '{self.shm_topic}', retrying ...")
        
        if self._shm is not None:
            pcd = PointCloud.try_deserialize_from_shm(self._shm) if hasattr(PointCloud, 'try_deserialize_from_shm') else None
            if pcd is None:
                self._logger.warning(f"SHM deserialize failed at topic: '{self.shm_topic}'")
            elif not hasattr(self, '_shm_connected_logged'):
                self._logger.info(f"Successfully reading data from SHM topic: '{self.shm_topic}'")
                self._shm_connected_logged = True
                self._shm_last_stats_time = time.time()
            else:
                # SHM 帧数统计日志
                self._shm_frame_count += 1
                current_time = time.time()
                if current_time - self._shm_last_stats_time >= 5.0:
                    self._logger.debug(f"SHM data flow: {self._shm_frame_count} frames processed in last 5 seconds")
                    self._shm_frame_count = 0
                    self._shm_last_stats_time = current_time
            self._pcd = pcd
        else:
            if not self.no_debug_pcd:
                self._pcd = next(self._debug_pcd_gen)

        # 更新点云统计信息
        self._update_pcd_statistics(self._pcd)

        # 渲染点云
        self._render_point_cloud(self._pcd)

        # 更新UI显示
        os_time_now = time.time()
        self.W_TS_THIS_OS_VAL.text = os_time_now
        self.W_FPS_WINDOW_VAL.text = self.window_fps

        # 与 PCD 相关的 UI 更新
        pcd = self._pcd
        status = PgTextValue.Status.NORMAL if pcd else PgTextValue.Status.DANGER

        items = [
            (self.W_FORMAT_VAL, pcd.data_format.name if pcd else "-"),
            (self.W_CHANNELS_VAL, pcd.data_channels if pcd else "-"),
            (self.W_POINTS_VAL, int(pcd.data.shape[0]) if pcd else "-"),
            (self.W_FRAME_VAL, pcd.frame_id if pcd else "-"),
            (self.W_TS_PCD_SIM_VAL, pcd.timestamp_sim if pcd else "-"),
            (self.W_TS_PCD_OS_VAL, pcd.timestamp_os if pcd else "-"),
            (self.W_FPS_PCD_VAL, self._pcd_fps if pcd else "-"),
            (self.W_TS_DT_MAX_VAL, self._pcd_dt_max if pcd else "-"),
            (self.W_TS_DT_AVG_VAL, self._pcd_dt_avg if pcd else "-"),
            (self.W_COMM_DELAY_VAL, (os_time_now - pcd.timestamp_os) if pcd else "-"),
        ]
        for widget, text in items:
            widget.text = text
            widget.status = status

        # 与 SHM 有关的 UI 更新
        self.W_CONNECTION_VAL.text = 'OK' if self._shm else 'FAILED'
        self.W_CONNECTION_VAL.status = PgTextValue.Status.NORMAL if self._shm else PgTextValue.Status.DANGER
        
        # 颜色模式显示
        self.W_COLORMODE_VAL.text = self.color_mode.value
        self.W_COLORMODE_VAL.status = PgTextValue.Status.NORMAL
        
        # 相机状态显示
        self.W_CAM_ZOOM_VAL.text = self._cam_dist
        self.W_CAM_ZOOM_VAL.status = PgTextValue.Status.NORMAL
        
        self.W_CAM_DEG_VAL.text = f"{int(self._cam_yaw)}/{int(self._cam_pitch)}"
        self.W_CAM_DEG_VAL.status = PgTextValue.Status.NORMAL
        
        self.W_CAM_POSE_VAL.text = f"{self._cam_target[0]:.1f},{self._cam_target[1]:.1f},{self._cam_target[2]:.1f}"
        self.W_CAM_POSE_VAL.status = PgTextValue.Status.NORMAL

        # 信息框宽度自适应
        self.W_DEBUG_BOX.width = max(
            self.W_CONNECTION_VAL.width,
            self.W_FORMAT_VAL.width,
            self.W_COLORMODE_VAL.width,
            self.W_CHANNELS_VAL.width,
            self.W_POINTS_VAL.width,
            self.W_FRAME_VAL.width,
            self.W_FPS_PCD_VAL.width,
            self.W_FPS_WINDOW_VAL.width,
            self.W_TS_PCD_SIM_VAL.width,
            self.W_TS_PCD_OS_VAL.width,
            self.W_TS_THIS_OS_VAL.width,
            self.W_TS_DT_MAX_VAL.width,
            self.W_TS_DT_AVG_VAL.width,
            self.W_COMM_DELAY_VAL.width,
            self.W_CAM_ZOOM_VAL.width,
            self.W_CAM_DEG_VAL.width,
            self.W_CAM_POSE_VAL.width,
            120,
        ) + self.W_GRID.col_interval * 5 + 10

    def _handle_input(self) -> None:
        # 获取鼠标状态
        buttons = pygame.mouse.get_pressed(3)
        pos = pygame.mouse.get_pos()

        # 检测左键按下/抬起
        if buttons[0] and not self._mouse_prev_buttons[0]:
            self._dragging = True
            self._drag_prev = pos
        if (not buttons[0]) and self._mouse_prev_buttons[0]:
            self._dragging = False
            self._drag_prev = None

        # 鼠标拖动旋转相机
        if self._dragging and self._drag_prev is not None:
            x, y = pos
            px, py = self._drag_prev
            dx, dy = x - px, y - py
            self._drag_prev = (x, y)
            self._cam_yaw += dx * 0.3
            self._cam_pitch = np.clip(self._cam_pitch - dy * 0.3, -89.0, 89.0)

        # 鼠标滚轮缩放
        for e in pygame.event.get(pygame.MOUSEWHEEL):
            if e.y > 0:
                self._cam_dist = max(1.0, self._cam_dist * 0.9)
            elif e.y < 0:
                self._cam_dist = min(5000.0, self._cam_dist * 1.1)

        # 键盘控制: 相机移动
        move_speed = max(1.0, self._cam_dist * 0.01)
        if pygame.K_w in self._keys_pressed:
            self._translate_camera_local(0.0, +move_speed, 0.0)
        if pygame.K_s in self._keys_pressed:
            self._translate_camera_local(0.0, -move_speed, 0.0)
        if pygame.K_a in self._keys_pressed:
            self._translate_camera_local(-move_speed, 0.0, 0.0)
        if pygame.K_d in self._keys_pressed:
            self._translate_camera_local(+move_speed, 0.0, 0.0)

        # 键盘控制: 相机旋转
        if pygame.K_UP in self._keys_pressed:
            self._cam_pitch = np.clip(self._cam_pitch + 0.5, -89.0, 89.0)
        if pygame.K_DOWN in self._keys_pressed:
            self._cam_pitch = np.clip(self._cam_pitch - 0.5, -89.0, 89.0)
        if pygame.K_LEFT in self._keys_pressed:
            self._cam_yaw -= 0.5
        if pygame.K_RIGHT in self._keys_pressed:
            self._cam_yaw += 0.5

        # 键盘控制: 点云大小
        if pygame.K_MINUS in self._keys_released or pygame.K_KP_MINUS in self._keys_released:
            self.point_size = max(1, self.point_size - 1)
        if pygame.K_EQUALS in self._keys_released or pygame.K_PLUS in self._keys_released or pygame.K_KP_PLUS in self._keys_released:
            self.point_size = min(20, self.point_size + 1)
        
        # 键盘控制: 相机缩放
        if pygame.K_r in self._keys_pressed:
            self._cam_dist = min(5000.0, self._cam_dist * 1.02)
        if pygame.K_f in self._keys_pressed:
            self._cam_dist = max(1.0, self._cam_dist * 0.98)

        # 键盘控制: 相机高度
        height_speed = max(0.1, self._cam_dist * 0.005)
        if pygame.K_q in self._keys_pressed:
            self._cam_target[2] -= height_speed  # Q 降低
        if pygame.K_e in self._keys_pressed:
            self._cam_target[2] += height_speed  # E 升高

        # 键盘控制: 色彩模式切换
        if pygame.K_c in self._keys_released:
            modes = [self.ColorMode.WHITE, self.ColorMode.HEIGHT, self.ColorMode.CHANNEL]
            try:
                idx = modes.index(self.color_mode)
            except ValueError:
                idx = 0
            self.color_mode = modes[(idx + 1) % len(modes)]

        # 键盘控制: 信息显示/隐藏
        if pygame.K_i in self._keys_released:
            for widget in self.widgets.values():
                if widget is self.W_GRID or widget is self.W_HELP_MODAL:
                    continue
                widget.show = not widget.show

        # 键盘控制: 帮助显示/隐藏
        if pygame.K_h in self._keys_released:
            self.W_HELP_MODAL.show = not self.W_HELP_MODAL.show

        # 记录上一帧鼠标状态
        self._mouse_prev_buttons = buttons
        self._mouse_prev_pos = pos
        # 空格键重置相机状态
        if pygame.K_SPACE in self._keys_released:
            self._reset_camera()

    def _reset_camera(self) -> None:
        """重置相机状态到初始位置"""
        self._cam_target = np.array(self.CAMERA_DEFAULT_TARGET, dtype=np.float32)
        self._cam_yaw = self.CAMERA_DEFAULT_YAW
        self._cam_pitch = self.CAMERA_DEFAULT_PITCH
        self._cam_dist = self.CAMERA_DEFAULT_DISTANCE

    def _translate_camera_local(self, dx: float, dy: float, dz: float) -> None:
        """
        在相机局部坐标系中平移相机观察目标（等效为移动场景）。
        """
        # 基于 yaw 的平面方向
        yaw_rad = math.radians(self._cam_yaw)
        forward = np.array([math.cos(yaw_rad), math.sin(yaw_rad), 0.0], dtype=np.float32)
        right = np.array([-math.sin(yaw_rad), math.cos(yaw_rad), 0.0], dtype=np.float32)
        up = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        delta = right * dx + forward * dy + up * dz
        self._cam_target += delta

    def _camera_matrices(self) -> tuple[np.ndarray, np.ndarray, float, float, float, float]:
        """
        构造视图和投影参数。
        :return: (R, t, fx, fy, cx, cy)
        """
        width, height = self.width, self.height

        # 相机在世界坐标的位置（轨道）
        yaw = math.radians(self._cam_yaw)
        pitch = math.radians(self._cam_pitch)
        # 以 Z 为上，绕 Z 旋转 yaw，再绕 X 旋转 pitch
        dir_cam = np.array([
            math.cos(pitch) * math.cos(yaw),
            math.cos(pitch) * math.sin(yaw),
            math.sin(pitch),
        ], dtype=np.float32)
        cam_pos = self._cam_target - dir_cam * self._cam_dist

        # 视图矩阵（R, t）：把世界点变换到相机坐标
        up_world = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        z_axis = (self._cam_target - cam_pos)
        z_axis = z_axis / (np.linalg.norm(z_axis) + int(1e-9))
        x_axis = np.cross(up_world, z_axis)
        x_axis = x_axis / (np.linalg.norm(x_axis) + int(1e-9))
        y_axis = np.cross(z_axis, x_axis)
        R = np.stack([x_axis, y_axis, z_axis], axis=0)  # 相机坐标轴在世界坐标下的方向
        t = -R @ cam_pos

        # 简单 pinhole 投影参数
        fov_deg = 60.0
        f = 0.5 * width / math.tan(math.radians(fov_deg * 0.5))
        fx = fy = f
        cx = width * 0.5
        cy = height * 0.5
        return R, t, fx, fy, cx, cy

    def _render_no_data(self) -> None:
        """
        在屏幕中心渲染一个 NO DATA 的文本
        """
        font = pygame.font.SysFont(None, 48)
        text = font.render("NO DATA", True, self.palette.BRIGHT_RED.RGBA)
        text_rect = text.get_rect(center=(self.width // 2, self.height // 2))
        self._screen.blit(text, text_rect)

    def _render_point_cloud(self, pcd: PointCloud | None) -> None:
        """
        渲染点云到屏幕
        :param pcd: 点云数据
        """
        if pcd is None:
            # 显示无数据状态
            self._render_no_data()
            return
        
        # 获取相机参数
        R, t, fx, fy, cx, cy = self._camera_matrices()
        
        # 提取点云坐标并转换到相机坐标系
        pts = pcd.data[:, 0:3].astype(np.float32, copy=False)  # (N,3)
        cam_pts = (R @ pts.T).T + t

        # 视图剪裁
        z = cam_pts[:, 2]
        valid = z > 1e-3
        cam_pts = cam_pts[valid]
        if cam_pts.size == 0:
            return

        x = cam_pts[:, 0]
        y = cam_pts[:, 1]
        z = cam_pts[:, 2]

        # 透视投影到屏幕坐标
        inv_z = 1.0 / z
        u = fx * (x * inv_z) + cx
        v = fy * (-(y * inv_z)) + cy

        # 裁剪到屏幕范围内
        w, h = self.width, self.height
        m = (u >= 0) & (u < w) & (v >= 0) & (v < h)
        u = u[m].astype(np.int32)
        v = v[m].astype(np.int32)

        # 计算点的颜色
        idx_valid = np.nonzero(valid)[0]
        idx_screen = idx_valid[m]
        if self.color_mode == self.ColorMode.WHITE:
            colors = np.full((len(idx_screen), 3), 255, dtype=np.uint8)
        elif self.color_mode == self.ColorMode.HEIGHT:
            z_world = pts[idx_screen, 2]
            t_h = (z_world - z_world.min()) / (np.ptp(z_world) + 1e-6)
            h = (4.0 / 6.0) * (1.0 - t_h)
            colors = self._fast_hsv_to_rgb(h)
        elif self.color_mode == self.ColorMode.CHANNEL and pcd.data.shape[1] >= 5:
            ch = pcd.data[idx_screen, 4].astype(np.float32, copy=False)
            r = max(1.0, float(pcd.data_channels - 1))
            t_h = np.clip(ch / r, 0.0, 1.0)
            h = (4.0 / 6.0) * (1.0 - t_h)
            colors = self._fast_hsv_to_rgb(h)
        else:
            colors = np.full((len(idx_screen), 3), 255, dtype=np.uint8)

        # 绘制点, 根据点大小选择不同方法
        ps = max(1, int(self.point_size))
        if ps <= 2:
            arr = pygame.surfarray.pixels3d(self._screen)
            arr[u, v] = colors  # 注意：surfarray 的索引是 [x, y]
            # 释放引用以解锁表面，避免后续 blit 报错
            del arr
        else:
            for i in range(len(u)):
                pygame.draw.circle(
                    self._screen,
                    color=tuple(int(c) for c in colors[i]),
                    center=(int(u[i]), int(v[i])),
                    radius=ps // 2
                )

        # 绘制坐标轴
        p0_world = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        ex = p0_world + np.array([1.0, 0.0, 0.0], dtype=np.float32)
        ey = p0_world + np.array([0.0, 1.0, 0.0], dtype=np.float32)
        ez = p0_world + np.array([0.0, 0.0, 1.0], dtype=np.float32)

        def proj_pt(pw: np.ndarray):
            pc_ = R @ pw + t
            if pc_[2] <= 1e-3:
                return None
            uu = fx * (pc_[0] / pc_[2]) + cx
            vv = fy * (-(pc_[1] / pc_[2])) + cy
            return int(uu), int(vv)

        p0 = proj_pt(p0_world)
        px = proj_pt(ex)
        py = proj_pt(ey)
        pz = proj_pt(ez)
        anchor = (40, self.height - 40)
        if p0 is None:
            p0 = anchor
        if px is None:
            px = (p0[0] + 30, p0[1])
        if py is None:
            py = (p0[0], p0[1] - 30)
        if pz is None:
            pz = (p0[0] - 20, p0[1] - 20)
        pygame.draw.line(self._screen, (255, 0, 0), p0, px, 3)
        pygame.draw.line(self._screen, (0, 255, 0), p0, py, 3)
        pygame.draw.line(self._screen, (0, 128, 255), p0, pz, 3)
        font = pygame.font.SysFont(None, 18)
        for label, pt in (("X", px), ("Y", py), ("Z", pz)):
            img = font.render(label, True, (255, 255, 255))
            self._screen.blit(img, (pt[0] + 4, pt[1] + 2))

    @staticmethod
    def _fast_hsv_to_rgb(h: np.ndarray) -> np.ndarray:
        """
        高效的 HSV 到 RGB 转换，避免创建大量 PgColor 对象
        :param h: 色相值数组 (0.0-1.0)
        :return: RGB 颜色数组 (N, 3) uint8
        """
        # 转换色相到度数
        h_deg = h * 360.0

        # HSV参数（S=1, V=1）
        c = np.ones_like(h)
        x = c * (1 - np.abs((h_deg / 60.0) % 2 - 1))

        # 初始化RGB数组
        rgb = np.zeros((len(h), 3), dtype=np.float32)

        # 按色相区间计算RGB
        sector = (h_deg / 60.0).astype(np.int32) % 6

        # 0-60 度
        mask = (sector == 0)
        rgb[mask, 0] = c[mask]
        rgb[mask, 1] = x[mask]
        rgb[mask, 2] = 0

        # 60-120 度
        mask = (sector == 1)
        rgb[mask, 0] = x[mask]
        rgb[mask, 1] = c[mask]
        rgb[mask, 2] = 0

        # 120-180 度
        mask = (sector == 2)
        rgb[mask, 0] = 0
        rgb[mask, 1] = c[mask]
        rgb[mask, 2] = x[mask]

        # 180-240 度
        mask = (sector == 3)
        rgb[mask, 0] = 0
        rgb[mask, 1] = x[mask]
        rgb[mask, 2] = c[mask]

        # 240-300 度
        mask = (sector == 4)
        rgb[mask, 0] = x[mask]
        rgb[mask, 1] = 0
        rgb[mask, 2] = c[mask]

        # 300-360 度
        mask = (sector == 5)
        rgb[mask, 0] = c[mask]
        rgb[mask, 1] = 0
        rgb[mask, 2] = x[mask]

        # 转换为 uint8
        return np.clip(rgb * 255, 0, 255).astype(np.uint8)

    def _update_pcd_statistics(self, pcd: PointCloud | None) -> None:
        if pcd is None:
            return
        is_new_frame = (self._pcd_frame_id_last != pcd.frame_id)
        if is_new_frame and self._pcd_prev_ts_os is not None:
            dt = max(0.0, pcd.timestamp_os - float(self._pcd_prev_ts_os))
            self._pcd_dt_ring.append(dt)
            if n := len(self._pcd_dt_ring):
                total = sum(self._pcd_dt_ring)
                self._pcd_dt_avg = total / n
                self._pcd_dt_max = max(self._pcd_dt_ring)
                self._pcd_fps = (1.0 / self._pcd_dt_avg) if self._pcd_dt_avg > 1e-9 else 0.0
        if is_new_frame:
            self._pcd_prev_ts_os = pcd.timestamp_os
            self._pcd_frame_id_last = pcd.frame_id

    def _shutdown(self):
        # 关闭 SHM 句柄，与参考实现一致
        if self._shm:
            SharedMemoryUtils.consumer_close(self._shm)
        super()._shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Point Cloud Viewer Application")
    parser.add_argument('--debug', action='store_true', help='Enable debug log display.')
    parser.add_argument('--debug-grid', action='store_true', help='Enable debug grid display for UI development.')
    parser.add_argument('--debug-pcd', action='store_true', help='Enable debug point cloud generation.')
    parser.add_argument('--width', type=int, default=800, help='Window width.')
    parser.add_argument('--height', type=int, default=600, help='Window height.')
    parser.add_argument('--fps', type=int, default=60, help='Window FPS.')
    parser.add_argument('--name', type=str, default="Cloud Viewer", help='Window title.')
    parser.add_argument('--color', type=str, default='white', choices=['white', 'height', 'channel'], help='Point color mode.')
    parser.add_argument('--ros2-export-topic', type=str, default=None, help='ROS2 UI export topic name to export UI.')
    parser.add_argument('--ros2-export-node', type=str, default=None, help='ROS2 UI export node name to export UI.')
    parser.add_argument('--ros2-export-qos', type=int, default=10, help='ROS2 UI export QoS depth for topic export.')
    parser.add_argument('--ros2-export-fps', type=int, default=10, help='ROS2 UI export FPS.')
    parser.add_argument('SHM_TOPIC', type=str, nargs='?', default=None, help='Shared Memory topic name to receive point cloud from.')
    args = parser.parse_args()

    app = CloudViewer(
        window_width=args.width,
        window_height=args.height,
        window_fps=args.fps,
        window_title=args.name,
        show_grid_debug=args.debug_grid,
        no_debug_pcd=not args.debug_pcd,
        logger_level=logging.DEBUG if args.debug else logging.INFO,
        color_mode=CloudViewer.ColorMode(args.color.upper()),
        shm_topic=args.SHM_TOPIC,
        ros2_export=True if args.ros2_export_topic else False,
        ros2_export_topic=args.ros2_export_topic,
        ros2_export_node_name=args.ros2_export_node,
        ros2_export_qos=args.ros2_export_qos,
        ros2_export_fps=args.ros2_export_fps,
    )
    app.run()
