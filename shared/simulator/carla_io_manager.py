from multiprocessing.shared_memory import SharedMemory
from multiprocessing import resource_tracker
from typing import Dict, Tuple
from typing_extensions import Self

from shared.io import SharedMemoryAdapter, ROS2Adapter
from shared.utils import Logging
from shared.data import TimestampSource


class CarlaIOManager:
    
    def __init__(
        self,
        *,
        shm_domain: str = 'hazard_scope',
        shm_default_size_mb: int = 2,
        ros2_node_name: str = 'hazard_scope_ros2_node',
        ros2_node_qos: int = 10,
    ):
        self.logger = Logging().get_logger('IOManager')

        # SHM
        self._shm_domain = shm_domain
        self._shm_default_size_mb = shm_default_size_mb
        self._shm_registry: Dict[str, Tuple[SharedMemoryAdapter, bool]] = {}

        # ROS2
        self._ros2_node = None
        self._ros2_node_name = ros2_node_name
        self._ros2_node_qos = ros2_node_qos

    @property
    def shm_registry(self) -> Dict[str, Tuple[SharedMemoryAdapter, bool]]:
        """共享内存注册表, 用于存储共享内存的名称、适配器和是否由本程序创建

        Returns:
            Dict[str, Tuple[SharedMemoryAdapter, bool]]: 共享内存注册表, 键为共享内存的名称, 值为共享内存适配器和是否由本程序创建的元组
        """
        return self._shm_registry

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
            size = self._shm_default_size_mb

        # 提供 shm 的 domain
        if self._shm_domain is not None and self._shm_domain != '':
            topic = f'{self._shm_domain}/{topic}'
        else:
            topic = topic

        # 尝试创建共享内存
        try:
            shm = SharedMemory(topic, create=True, size=size * 1024 * 1024)
            host = True
        except FileExistsError:
            self.logger.warning(f"SharedMemory with topic '{topic}' already exists, using existing one")
            shm = SharedMemory(topic, read_only=False)
            host = False

        # 创建适配器并注册到注册表
        if topic in self.shm_registry.keys():
            return self.shm_registry[topic][0]
        adapter = SharedMemoryAdapter(shm)
        self.shm_registry[topic] = (adapter, host)
        self.logger.info(f"Created shared memory with topic '{topic}', host={host}")
        return adapter

    def destroy_shm(self, shm: str | SharedMemoryAdapter | SharedMemory) -> Self:
        """销毁共享内存

        Args:
            shm (str | SharedMemoryAdapter | SharedMemory): 共享内存的名称、适配器或共享内存本身

        Returns:
            Self: 链式调用支持
        """
        # 解析共享内存到 SharedMemory 对象
        if isinstance(shm, str):
            shm = self.shm_registry[shm][0].shm
        elif isinstance(shm, SharedMemoryAdapter):
            shm = shm.shm
        elif isinstance(shm, SharedMemory):
            pass

        # 销毁共享内存
        topic_name = shm.name
        if self.shm_registry[topic_name][1]:
            self.logger.info(f"Destroying shared memory with topic '{topic_name}', host=True")
            shm.close()
            shm.unlink()
        else:
            self.logger.info(f"Closing shared memory with topic '{topic_name}', host=False")
            resource_tracker.unregister(shm._name, 'shared_memory')  # 在 Linux 下防止 resource_tracker 清理共享内存
            shm.close()

        # 从注册表中移除
        del self.shm_registry[topic_name]
        
        return self

    def destroy_all_shm(self) -> Self:
        """销毁所有共享内存"""
        # 复制键列表，避免在迭代时修改字典
        topics = list(self.shm_registry.keys())
        for topic in topics:
            self.destroy_shm(topic)
        return self

    def create_ros2(
        self, topic: str, 
        frame_id: str = 'world', 
        timestamp_source: TimestampSource = TimestampSource.OS,
    ) -> ROS2Adapter:
        # 如果 ROS2 节点不存在, 则创建 ROS2 节点
        if self._ros2_node is None:
            self._create_ros2_node()

        # 创建 ROS2 适配器
        adapter = ROS2Adapter(topic, self._ros2_node, self._ros2_node_qos, frame_id, timestamp_source)
        return adapter

    def _create_ros2_node(self) -> Self:
        """创建 ROS2 节点"""
        import rclpy

        # 如果需要则初始化 RCLPY 环境
        if not rclpy.ok():
            rclpy.init()
            self.logger.info(f"Initialized RCLPY environment")

        # 创建 ROS2 节点
        node = rclpy.create_node(self._ros2_node_name, enable_rosout=False)
        self._ros2_node = node
        self.logger.info(f"Created ROS2 node '{self._ros2_node_name}'")
        return self

    def destroy_ros2_node(self) -> Self:
        """销毁 ROS2 节点"""
        import rclpy
        if self._ros2_node is not None:
            self.logger.info(f"Destroying ROS2 node '{self._ros2_node_name}'")
            
            for pub in self._ros2_node.publishers:
                pub.destroy()
            for sub in self._ros2_node.subscriptions:
                sub.destroy()

            self._ros2_node.destroy_node()
            self._ros2_node = None
        if rclpy.ok():
            self.logger.info(f"Shutting down RCLPY environment")
            rclpy.shutdown()
        return self