import time
from multiprocessing.shared_memory import SharedMemory
from typing import TYPE_CHECKING
from typing_extensions import Self
from logging import Logger
from threading import Thread
from typing import Callable

from shared.io import SharedMemoryAdapter, ROS2PublishAdapter, ROS2TfAdapter
from shared.utils import Logging
from shared.data import TimestampSource

if TYPE_CHECKING:
    from shared.simulator import CarlaContext
    from rclpy import Node
    from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster


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
        self._flag_ros2_enabled: bool = False
        self._registry_ros2: set[ROS2PublishAdapter] = set()

        self._node_tf: 'Node' | None = None
        self._node_tf_executor = None
        self._node_tf_broadcaster: 'TransformBroadcaster' | None = None
        self._node_tf_static_broadcaster: 'StaticTransformBroadcaster' | None = None
        self._node_tf_spin_thread: Thread | None = None
        self._registry_ros2_tf: set[ROS2TfAdapter] = set()
        self._registry_ros2_tf_static: set[ROS2TfAdapter] = set()
        self._hook_ros2_tf_broadcast: Callable[[], None] = None

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
        msg: type | None = None,
        shm_topic: str = '',
        ros_node_name: str = ROS2PublishAdapter.DEFAULT_ROS_NODE_NAME,
        ros_node_qos: int = 10,
        frame_id: str = 'world',
        timestamp_source: TimestampSource = TimestampSource.OS,
    ) -> ROS2PublishAdapter:
        """创建 ROS2 发布高性能适配器"""
         # 标记启用 ROS2
        self._flag_ros2_enabled = True

        # 先创建 SHM
        if shm_topic is None or shm_topic == '':
            shm_topic = topic
        shm = self.create_shm(shm_topic.replace("/", "_"))

        # 创建 ROS2 高性能适配器
        adapter = ROS2PublishAdapter(
            context=self._context,
            shm_adapter=shm,
            ros_message_type=msg,
            ros_topic_name=topic,
            ros_node_name=ros_node_name,
            ros_qos=ros_node_qos,
            ros_frame_id=frame_id,
            timestamp_source=timestamp_source,
        )
        self._registry_ros2.add(adapter)
        return adapter

    def create_ros2_tf_static(self, frame_id_parent: str, frame_id_child: str) -> ROS2TfAdapter:
        # 如果 TF 节点不存在, 则创建 TF 节点并启动
        self._create_ros2_tf_node_if_not_exists()

        adapter = ROS2TfAdapter(
            context=self._context,
            frame_id_parent=frame_id_parent,
            frame_id_child=frame_id_child,
            tf_broadcaster=self._node_tf_static_broadcaster,
        )

        self._registry_ros2_tf_static.add(adapter)
        return adapter

    def create_ros2_tf(self, frame_id_parent: str, frame_id_child: str) -> ROS2TfAdapter:
        # 如果 TF 节点不存在, 则创建 TF 节点并启动
        self._create_ros2_tf_node_if_not_exists()

        # 注册 TF 广播钩子
        if self._hook_ros2_tf_broadcast is None:
            self._hook_ros2_tf_broadcast = self._hookfunc_ros2_tf_broadcast
            self._context.hook_on_tick.append(self._hook_ros2_tf_broadcast)

        adapter = ROS2TfAdapter(
            context=self._context,
            frame_id_parent=frame_id_parent,
            frame_id_child=frame_id_child,
            tf_broadcaster=self._node_tf_broadcaster,
        )

        self._registry_ros2_tf.add(adapter)
        return adapter

    def destroy_all_ros2(self) -> Self:
        """销毁所有 ROS2 高性能适配器"""
        for adapter in list(self._registry_ros2):
            adapter.stop_sensor_worker()
            adapter.stop_clock_worker()
        self._registry_ros2.clear()

        # TF NODE
        self._registry_ros2_tf.clear()
        self._registry_ros2_tf_static.clear()
        if self._node_tf_executor is not None:
            self._node_tf_executor.shutdown()
        if self._node_tf_spin_thread is not None:
            self._node_tf_spin_thread.join(timeout=2.0)
            self._node_tf_spin_thread = None
        if self._node_tf is not None:
            self._node_tf.destroy_node()
            self._node_tf = None
        self._node_tf_executor = None
        return self

    def _create_ros2_tf_node_if_not_exists(self):
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster

        if not rclpy.ok():
            rclpy.init()

        if self._node_tf is None:
            self._node_tf = rclpy.create_node('HazardScopeROS2_TF', enable_rosout=False)
            self.logger.debug(f"Created ROS2 TF node 'HazardScopeROS2_TF'")

        if self._node_tf_executor is None:
            self._node_tf_executor = SingleThreadedExecutor()
            self._node_tf_executor.add_node(self._node_tf)

        if self._node_tf_broadcaster is None:
            self._node_tf_broadcaster = TransformBroadcaster(self._node_tf)
            self.logger.debug(f"Created ROS2 TF broadcaster")

        if self._node_tf_static_broadcaster is None:
            self._node_tf_static_broadcaster = StaticTransformBroadcaster(self._node_tf)
            self.logger.debug(f"Created ROS2 TF static broadcaster")

        if self._node_tf_spin_thread is None or not self._node_tf_spin_thread.is_alive():
            if self._node_tf_spin_thread is not None:
                self._node_tf_executor.shutdown()
                self._node_tf_spin_thread.join(timeout=1.0)
                self._node_tf_spin_thread = None
                self._node_tf_executor = SingleThreadedExecutor()
                self._node_tf_executor.add_node(self._node_tf)
            self._node_tf_spin_thread = Thread(target=self._threadfunc_ros2_tf_spin, daemon=True)
            self._node_tf_spin_thread.start()
            self.logger.debug(f"Started ROS2 TF spin thread")

    def _threadfunc_ros2_tf_spin(self) -> None:
        try:
            self._node_tf_executor.spin()
        except Exception:
            pass

    def _hookfunc_ros2_tf_broadcast(self, _) -> None:
        for adapter in self._registry_ros2_tf:
            self._node_tf_broadcaster.sendTransform(adapter.tf_stamped)

# endregion: ROS2 High Performance