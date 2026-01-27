import time
from multiprocessing.shared_memory import SharedMemory
from typing import TYPE_CHECKING, Callable
from typing_extensions import Self
from logging import Logger
from threading import Thread

from shared.io import SharedMemoryAdapter, ROS2TfAdapter, ROS2SubAdapter
from shared.utils import Logging
from shared.define import TimestampSource

if TYPE_CHECKING:
    from shared.simulator import CarlaContext
    from rclpy import Node
    from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
    from shared.io import ROS2PubAdapter


class CarlaIOManager:
    
    def __init__(
        self,
        context: 'CarlaContext',
    ):
        self._logger = Logging().get_logger('IOManager')
        self._context = context
        self._config = context.configs.io_manager

        # SHM
        self._registry_shm: set[SharedMemoryAdapter] = set()

        # ROS2
        self._flag_ros2_enabled = False
        self._ros2_node: 'Node' | None = None
        self._ros2_executor = None
        self._ros2_tf_boardcaster: 'TransformBroadcaster' | None = None
        self._ros2_tf_static_boardcaster: 'StaticTransformBroadcaster' | None = None
        self._ros2_adapters: set['ROS2TfAdapter | ROS2SubAdapter | ROS2PubAdapter'] = set()
        self._thread_ros2_spin: Thread | None = None

    @property
    def logger(self) -> Logger:
        return self._logger

    def destroy_all(self) -> Self:
        self.destroy_all_shm()
        if self._flag_ros2_enabled:
            self.destroy_all_ros2()
        return self

# region: SharedMemory

    def create_shm(self, topic: str, size: int = None) -> SharedMemoryAdapter:
        """创建共享内存, 如果共享内存已存在, 则使用已存在的共享内存

        由本程序创建的共享内存, 会被标记为 host=True, 这些共享内存会在程序退出时自动销毁

        Args:
            topic (str): 共享内存的名称
            size (int): 共享内存的大小, 单位为 MB

        Returns:
            SharedMemoryAdapter: 共享内存适配器
        """
        # 提供 size 的默认值
        if size is None:
            size = self._config.shared_memory_default_size_mb

        # 提供 shm 的 domain
        if self._config.shared_memory_domain is not None and self._config.shared_memory_domain != '':
            topic = f'{self._config.shared_memory_domain}_{topic}'
        else:
            topic = topic

        # 尝试创建共享内存
        retry = 0
        while True:
            try:
                shm = SharedMemory(topic, create=True, size=size * 1024 * 1024)
                break
            except FileExistsError:
                if retry == 0:
                    self.logger.warning(f"SharedMemory with topic '{topic}' already exists, try to destroy it")
                    shm = SharedMemory(topic, create=False)
                    shm.close()
                    shm.unlink()
                    retry += 1
                    time.sleep(0.1)
                    continue
                else:
                    self.logger.critical(f"SharedMemory with topic '{topic}' already exists, and failed to destroy it")
                    raise SystemExit(321)

        # 创建适配器并注册到注册表
        adapter = SharedMemoryAdapter(self._context, shm, topic)
        self._registry_shm.add(adapter)
        self.logger.info(f"Created shared memory with topic '{topic}'")
        return adapter

    def find_shm_by_topic(self, topic: str) -> SharedMemoryAdapter | None:
        """根据共享内存的名称查找共享内存适配器"""
        for adapter in self._registry_shm:
            if adapter.topic == topic:
                return adapter
        return None

    def destroy_shm(self, shm: str | SharedMemoryAdapter) -> Self:
        """销毁共享内存

        Args:
            shm (str | SharedMemoryAdapter): 共享内存的 Topic 名称或适配器

        Returns:
            Self: 链式调用支持
        """
        # 解析共享内存到 SharedMemory 对象
        if isinstance(shm, str):
            adapter = self.find_shm_by_topic(shm)
        elif isinstance(shm, SharedMemoryAdapter):
            adapter = shm

        # 销毁共享内存
        topic = adapter.topic
        instance = adapter.shared_memory_instance
        self.logger.info(f"Destroying shared memory with topic '{topic}', managed=True")
        instance.close()
        instance.unlink()

        # 从注册表中移除
        self._registry_shm.remove(adapter)
        
        return self

    def destroy_all_shm(self) -> Self:
        """销毁所有共享内存"""
        for adapter in list(self._registry_shm):
            self.destroy_shm(adapter)
        return self

# endregion: SharedMemory

# region: ROS2

    def create_ros2_pub(
        self,
        topic: str,
        msg: type,
        qos: int = 10,
        frame_id: str = 'UNDEFINED',
        timestamp_source: TimestampSource = TimestampSource.OS,
    ) -> 'ROS2PubAdapter':
        from shared.io import ROS2PubAdapter
        
        self._init_ros2_if_not_initialized()

        ros2_pub = self._ros2_node.create_publisher(msg, topic, qos)

        adapter = ROS2PubAdapter(self._context, ros2_pub, topic, msg, frame_id, timestamp_source, qos)
        self._ros2_adapters.add(adapter)
        return adapter

    def create_ros2_tf(
        self,
        frame_id_parent: str,
        frame_id_child: str,
        timestamp_source: TimestampSource = TimestampSource.OS,
        *,
        use_static: bool = True
    ) -> ROS2TfAdapter:
        from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster

        self._init_ros2_if_not_initialized()

        # 确保建立 Broadcaster
        if use_static and self._ros2_tf_static_boardcaster is None:
            self._ros2_tf_static_boardcaster = StaticTransformBroadcaster(self._ros2_node)
        if not use_static and self._ros2_tf_boardcaster is None:
            self._ros2_tf_boardcaster = TransformBroadcaster(self._ros2_node)

        adapter = ROS2TfAdapter(
            context=self._context,
            ros2_tf_broadcaster=self._ros2_tf_boardcaster if not use_static else self._ros2_tf_static_boardcaster,
            frame_id_parent=frame_id_parent,
            frame_id_child=frame_id_child,
            timestamp_source=timestamp_source,
        )

        self._ros2_adapters.add(adapter)
        return adapter
        

    def create_ros2_sub(
        self,
        topic: str,
        msg: type,
        qos: int = 10,
    ) -> ROS2SubAdapter:
        self._init_ros2_if_not_initialized()

        # 先创建 adapter
        adapter = ROS2SubAdapter(self._context, None, msg)

        # 创建订阅器，使用 adapter 的内部回调
        ros2_sub = self._ros2_node.create_subscription(
            msg, topic, adapter._internal_callback, qos
        )
        adapter._ros2_sub = ros2_sub

        self._ros2_adapters.add(adapter)
        return adapter

    def destroy_all_ros2(self) -> Self:
        """销毁所有 ROS2 资源"""
        if not self._flag_ros2_enabled:
            return self

        import rclpy

        # 销毁所有适配器
        for adapter in list(self._ros2_adapters):
            adapter.destroy()
        self._ros2_adapters.clear()

        # 停止 executor，这会使 spin 线程退出
        if self._ros2_executor is not None:
            self._ros2_executor.shutdown()

        # 等待 spin 线程结束
        if self._thread_ros2_spin is not None:
            self._thread_ros2_spin.join(timeout=2.0)
            if self._thread_ros2_spin.is_alive():
                self._logger.warning("ROS2 spin thread did not stop in time")
            self._thread_ros2_spin = None

        # 从 executor 移除并销毁 node
        if self._ros2_node is not None:
            if self._ros2_executor is not None:
                self._ros2_executor.remove_node(self._ros2_node)
            self._ros2_node.destroy_node()
            self._ros2_node = None
            self._logger.debug("Destroyed ROS2 node")

        # 清理 executor
        self._ros2_executor = None

        # 关闭 rclpy
        if rclpy.ok():
            rclpy.shutdown()
            self._logger.info("ROS2 shutdown completed")

        self._flag_ros2_enabled = False
        return self

    def _init_ros2_if_not_initialized(self):
        """延迟初始化 ROS2 资源"""
        if self._flag_ros2_enabled:
            return

        import rclpy
        from rclpy.executors import SingleThreadedExecutor

        self._flag_ros2_enabled = True

        # rclpy 初始化
        if not rclpy.ok():
            rclpy.init()

        # node 初始化
        node_name = self._config.ros2_node_name
        self._ros2_node = rclpy.create_node(node_name, enable_rosout=False)
        self._logger.info(f"Created ROS2 node '{node_name}'")

        # executor 初始化并添加 node
        self._ros2_executor = SingleThreadedExecutor()
        self._ros2_executor.add_node(self._ros2_node)

        # spin 线程初始化
        self._thread_ros2_spin = Thread(target=self._threadfunc_ros2_spin, daemon=True)
        self._thread_ros2_spin.start()

    def _threadfunc_ros2_spin(self):
        """ROS2 spin 线程函数"""
        try:
            self._ros2_executor.spin()
        except Exception as e:
            self._logger.debug(f"ROS2 spin stopped: {e}")
        finally:
            self._logger.info("ROS2 spin thread stopped")

# endregion: ROS2 High Performance