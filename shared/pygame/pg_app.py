import pygame
import logging
import threading

from shared.utils import Logging, PostInitMeta
from shared.pygame import PgColor, PgPos, PgWidget, PgRefSurface

class PgApp(metaclass=PostInitMeta):
    """PgApp 的基类"""
    
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

    ):
        self._logger = Logging(level=log_level).get_logger(log_name or self.__class__.__name__)

        # 窗口参数
        self._window_width = window_width
        self._window_height = window_height
        self._window_title = window_title or self.__class__.__name__
        self._window_fps = window_fps

        # 键盘事件
        self._key_pressed = set[str]()
        self._key_released = set[str]()

        # ROS2 播送
        self._flag_ros2_enabled = False
        if ros2_topic:
            self._flag_ros2_enabled = True
            # 导入 ROS2 相关模块
            import rclpy
            from rclpy.node import Node
            from sensor_msgs.msg import Image
            from rclpy.publisher import Publisher

            self._ros2_export_topic = ros2_topic
            self._ros2_export_qos = 10
            self._ros2_export_node: Node | None = None
            self._ros2_export_publisher: Publisher[Image] | None = None
            self._ros2_export_spin_thread: threading.Thread | None = None
            self._ros2_export_cache_msg: Image | None = None

        # 其他成员
        self._frame = 0
        self._clock = pygame.time.Clock()
        self._ref_surface: PgRefSurface = PgRefSurface(None)
        self._widgets: list[PgWidget] = []

    def __post_init__(self):
        self.__init_widgets__()

    def __init_widgets__(self) -> None:
        """PgWidget 控件的声明与初始化"""
        pass

    @property
    def frame(self) -> int:
        return self._frame

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def width(self) -> int:
        return self._window_width

    @property
    def height(self) -> int:
        return self._window_height

    @property
    def center_pos(self) -> PgPos:
        return PgPos(
            x=self._window_width / 2,
            y=self._window_height / 2,
        )

    @property
    def surface(self) -> pygame.Surface:
        return self._ref_surface()

    @property
    def ref_surface(self) -> PgRefSurface:
        return self._ref_surface

    @property
    def widgets(self) -> list[PgWidget]:
        return self._widgets

    def update(self) -> None:
        """更新应用程序状态"""
        pass

    def run(self) -> None:
        """阻塞执行 pygame 主循环"""
        # 初始化 pygame 窗口
        pygame.init()
        pygame.font.init()
        self._ref_surface.surface = pygame.display.set_mode((self.width, self.height))
        self.logger.info(f'Window initialized.')

        # 主循环
        try:

            if self._flag_ros2_enabled:
                self._init_ros2_export()

            while True:
                # Tick
                self._clock.tick(self._window_fps)
                self._frame += 1

                # 绘制程序背景
                self.surface.fill(PgColor.BACKGROUND)

                # 事件处理
                events = pygame.event.get()
                self._handle_keyboard_event(events)
                self._handle_exit_event(events)

                # 更新
                self.update()

                # 控件绘制
                sorted_widgets = self._get_sorted_widgets()
                for widget in sorted_widgets:
                    widget.set_ref_surface(self.ref_surface)
                    widget.draw()

                # 画面更新
                pygame.display.set_caption(self._window_title)
                pygame.display.update()

                # ROS2 播送
                if self._flag_ros2_enabled:
                    view = self.surface.get_view('1')
                    mv_src = memoryview(view).cast('B')
                    mv_dst = memoryview(self._ros2_export_cache_msg.data)
                    mv_dst[:len(mv_src)] = mv_src
                    del mv_dst
                    del mv_src
                    del view

        except KeyboardInterrupt:
            self.logger.warning('Spin stopped by keyboard interrupt')
        finally:
            pygame.quit()
            self.close()
            self.logger.info('GOODBYE.')
    
    def close(self) -> None:
        pass

    def _handle_keyboard_event(self, events: list[pygame.event.Event]) -> None:
        self._key_released.clear()
        for event in events:
            if event.type == pygame.KEYDOWN:
                self._key_pressed.add(event.key)
            if event.type == pygame.KEYUP:
                self._key_released.add(event.key)
                self._key_pressed.discard(event.key)

    def _handle_exit_event(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.QUIT:
                self.logger.warning('Spin stopped by pygame quit event')
                raise SystemExit(0)
            if pygame.K_ESCAPE in self._key_released:
                self.logger.warning('Spin stopped by escape key')
                raise SystemExit(0)

    def _get_sorted_widgets(self) -> list[PgWidget]:
        """对控件树进行深度优先遍历，并按照 z_index 排序, 大在前
        
        返回:
            list[PgWidget]: 排序后的控件列表
        """
        if not self._widgets:
            return []
        
        sorted_widgets: list[PgWidget] = []
        def dfs(widget: PgWidget) -> None:
            sorted_widgets.append(widget)
            for child in widget.childrens:
                dfs(child)
        
        # 遍历所有根控件
        for root_widget in self._widgets:
            dfs(root_widget)
        
        return sorted(sorted_widgets, key=lambda x: x.z_index, reverse=True)

# region: ROS2 播送

    def _init_ros2_export(self):
        """初始化 ROS2 播送节点"""
        import rclpy
        from rclpy.node import Node
        from sensor_msgs.msg import Image
        from rclpy.publisher import Publisher

        if not rclpy.ok():
            rclpy.init()
        node_name = f"{self.__class__.__name__}_ros2_export"
        self._ros2_export_node = Node(node_name)
        self._ros2_export_publisher = self._ros2_export_node.create_publisher(
            Image,
            self._ros2_export_topic,
            self._ros2_export_qos
        )
        self._ros2_export_publisher_timer = self._ros2_export_node.create_timer(
            1.0 / self._window_fps,
            self._ros2_export_timer_callback
        )

        width, height = self.width, self.height

        # 构建图片缓存
        self._ros2_export_cache_msg = Image()
        self._ros2_export_cache_msg.height = height
        self._ros2_export_cache_msg.width = width
        self._ros2_export_cache_msg.encoding = "bgra8" if self.surface.get_bytesize() == 4 else "bgr8"
        self._ros2_export_cache_msg.step = self.surface.get_pitch()
        self._ros2_export_cache_msg.data = bytearray(height * self.surface.get_pitch())

        self._logger.debug(f"ROS2 export on topic '{self._ros2_export_topic}' from '{node_name}'")
        self._ros2_export_spin_thread = threading.Thread(
            target=self._ros2_export_node_spin,
            daemon=True
        )
        self._ros2_export_spin_thread.start()

    def _ros2_export_node_spin(self):
        """ROS2 节点循环"""
        import rclpy
        self._logger.info("ROS2 export begin")
        try:
            rclpy.spin(self._ros2_export_node)
        except rclpy.executors.ExternalShutdownException:
            pass
        finally:
            self._logger.info("ROS2 export stopped")

    def _ros2_export_timer_callback(self):
        """ROS2 播送定时器回调, 用于定时发布图像消息"""
        from sensor_msgs.msg import Image

        self._ros2_export_cache_msg.header.stamp = self._ros2_export_node.get_clock().now().to_msg()
        self._ros2_export_publisher.publish(self._ros2_export_cache_msg)

# endregion: ROS2 播送