import logging
import pygame
from typing import Any, Dict, Set, Tuple
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from rich.logging import RichHandler
from threading import Thread

from core.pygame import PgColor, PgWidget


class PgApp(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,   # 增加赋值时的检查, 务必保持开启
    )

    logger_name: str = Field(default=None)
    logger_level: int = Field(default=logging.INFO)

    window_width: int = Field(default=800, ge=0, frozen=True)
    window_height: int = Field(default=600, ge=0, frozen=True)
    window_title: str = Field(default=None)
    window_fps: int = Field(default=30, ge=0, frozen=True)

    palette: PgColor = Field(default_factory=PgColor)
    widgets: Dict[str, PgWidget] = Field(default_factory=dict, frozen=True)

    _frame: int = PrivateAttr(default=0)
    _clock: pygame.time.Clock = PrivateAttr(default_factory=pygame.time.Clock)
    _screen: pygame.Surface = PrivateAttr()
    _logger: logging.Logger = PrivateAttr()
    _keys_pressed: Set[str] = PrivateAttr(default_factory=set)
    _keys_released: Set[str] = PrivateAttr(default_factory=set)

    # 界面 ROS2 播送
    ros2_export: bool = Field(default=False)
    ros2_export_topic: str | None = Field(default=None)
    ros2_export_qos: int = Field(default=10)
    ros2_export_node_name: str | None = Field(default=None)
    ros2_export_fps: int = Field(default=10, ge=1)
    _ros2_export_node: Any = PrivateAttr(default=None)
    _ros2_export_publisher: Any = PrivateAttr(default=None)
    _ros2_export_spin_thread: Thread = PrivateAttr(default=None)
    _ros2_export_publisher_timer: Any = PrivateAttr(default=None)
    _ros2_export_cache_msg: Any = PrivateAttr(default=None)
    

    @property
    def frame(self) -> int:
        return self._frame

    @property
    def width(self) -> int:
        return self.window_width

    @property
    def height(self) -> int:
        return self.window_height

    @property
    def center(self) -> Tuple[int, int]:
        return self.window_width // 2, self.window_height // 2

    @property
    def center_x(self) -> int:
        return self.window_width // 2

    @property
    def center_y(self) -> int:
        return self.window_height // 2

    def model_post_init(self, context: Any, /) -> None:
        # 默认值处理
        if not self.window_title:
            self.window_title = self.__class__.__name__
        if not self.logger_name:
            self.logger_name = self.__class__.__name__
        if not self.ros2_export_node_name:
            self.ros2_export_node_name = self.__class__.__name__
        if not self.ros2_export_topic:
            self.ros2_export_topic = f"/{self.__class__.__name__}/export"

        # 日志系统
        self._logger = self._create_logger()

        # 完成
        self._logger.debug("Initialization complete")
        return

    def run(self):
        """执行 PyGame 主循环"""
        # 初始化 PyGame 窗口
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption(self.window_title)
        self._screen = pygame.display.set_mode((self.window_width, self.window_height))

        self._logger.info("Program started")
        try:
            self._init_widgets()
            self._init_widgets_register()
            self._logger.debug(f"Widgets initialized, count: {len(self.widgets.keys())}")

            # ROS2 播送初始化
            if self.ros2_export:
                self._init_ros2_export()

            while True:
                self._clock.tick(self.window_fps)
                self._screen.fill(self.palette.BACKGROUND)
                self._event_handler()
                self._update()
                self._draw()
                pygame.display.update()

                # ROS2 播送缓存
                if self.ros2_export:
                    view = self._screen.get_view('1')
                    mv_src = memoryview(view).cast('B')
                    mv_dst = memoryview(self._ros2_export_cache_msg.data)
                    mv_dst[:len(mv_src)] = mv_src
                    del mv_dst
                    del mv_src
                    del view

                # 按键退出
                if pygame.K_ESCAPE in self._keys_pressed:
                    self._logger.debug("User exit ESC")
                    break

        except KeyboardInterrupt:
            self._logger.debug("User exit Ctrl-C")
        finally:
            pygame.quit()
        self._logger.info("Goodbye")

    def _event_handler(self):
        """Pygame 事件处理程序"""
        self._keys_released.clear()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                break
            elif event.type == pygame.KEYDOWN:
                self._keys_pressed.add(event.key)
            elif event.type == pygame.KEYUP:
                self._keys_pressed.discard(event.key)
                self._keys_released.add(event.key)

    def _draw(self):
        """每个 Tick 执行一次绘制的内容, 用于展示动态对象"""
        # 按照控件的 z-index 进行升序排序
        widgets = sorted(self.widgets.values(), key=lambda x: x.z_index)

        for widget in widgets:
            widget.draw()

    def _init_widgets(self):
        """程序开始时调用一次, 用于初始化控件"""
        pass

    def _init_widgets_register(self):
        """在所有控件初始化完成后调用一次, 用于自动注册以 "W_" 开头的对象为控件"""
        for name, value in self.__dict__.items():
            if name.startswith("W_"):
                if isinstance(value, PgWidget):
                    self.widgets[name] = value
                else:
                    self._logger.warning(
                        f"Attribute '{name}' is not an instance of PgWidget and will be ignored"
                    )

    def _init_ros2_export(self):
        """初始化 ROS2 播送节点"""
        import rclpy
        from rclpy.node import Node
        from sensor_msgs.msg import Image

        rclpy.init()
        self._ros2_export_node = Node(self.ros2_export_node_name)
        self._ros2_export_publisher = self._ros2_export_node.create_publisher(
            Image,
            self.ros2_export_topic,
            self.ros2_export_qos
        )
        self._ros2_export_publisher_timer = self._ros2_export_node.create_timer(
            1.0 / self.ros2_export_fps,
            self._ros2_export_timer_callback
        )

        width, height = self._screen.get_size()

        # 构建图片缓存
        self._ros2_export_cache_msg = Image()
        self._ros2_export_cache_msg.height = height
        self._ros2_export_cache_msg.width = width
        self._ros2_export_cache_msg.encoding = "bgra8" if self._screen.get_bytesize() == 4 else "bgr8"
        self._ros2_export_cache_msg.step = self._screen.get_pitch()
        self._ros2_export_cache_msg.data = bytearray(height * self._screen.get_pitch())

        self._logger.debug(f"ROS2 export on topic '{self.ros2_export_topic}' from '{self.ros2_export_node_name}'")
        self._ros2_export_spin_thread = Thread(
            target=self._ros2_export_node_spin,
            daemon=True
        )
        self._ros2_export_spin_thread.start()

    def _ros2_export_node_spin(self):
        """ROS2 节点循环"""
        import rclpy
        self._logger.info("ROS2 Image export begin")
        try:
            rclpy.spin(self._ros2_export_node)
        except rclpy.executors.ExternalShutdownException:
            pass
        finally:
            rclpy.shutdown()
            self._logger.info("ROS2 Image export stopped")

    def _ros2_export_timer_callback(self):
        """ROS2 播送定时器回调, 用于定时发布图像消息"""
        from sensor_msgs.msg import Image

        self._ros2_export_cache_msg.header.stamp = self._ros2_export_node.get_clock().now().to_msg()
        self._ros2_export_publisher.publish(self._ros2_export_cache_msg)

    def _update(self):
        """更新, 在 ``draw_tick()`` 前被调用, 用于更新状态机"""
        pass

    def _create_logger(self) -> logging.Logger:
        """
        建立类内的日志系统
        :return: ``logging.Logger`` 实例
        """
        formatter = logging.Formatter("[bold cyan][%(name)s][/] %(message)s")
        handler = RichHandler(
            rich_tracebacks=True,
            show_time=True,
            markup=True,
        )
        handler.setFormatter(formatter)
        logger = logging.getLogger(self.logger_name)
        logger.setLevel(self.logger_level)
        logger.propagate = False
        logger.addHandler(handler)
        return logger

    @field_validator("window_title", mode="after")
    @classmethod
    def _on_field_update_window_title(cls, v: str) -> str:
        pygame.display.set_caption(v)
        return v
