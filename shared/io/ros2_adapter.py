from typing_extensions import Self
from typing import TYPE_CHECKING

from shared.io import IOAdapter
from shared.simulator import CarlaSensor
from shared.data import TimestampSource

if TYPE_CHECKING:
    from rclpy.node import Node
    from rclpy.publisher import Publisher
    from rclpy.subscription import Subscription


class ROS2Adapter(IOAdapter):
    """
    ROS2 适配器, 用于将仿真器的数据转换为 ROS2 数据
    """

    def __init__(
        self, topic_name: str, 
        node: "Node", 
        qos: int = 10, 
        frame_id: str = 'world',
        timestamp_source: TimestampSource = TimestampSource.OS,
    ):
        super().__init__()
        self._topic_name = topic_name
        self._pubsub: "Publisher | Subscription" | None = None
        self._node: "Node" = node
        self._qos = qos
        self._frame_id = frame_id
        self._timestamp_source = timestamp_source

    @property
    def topic_name(self) -> str:
        return self._topic_name

    @property
    def node(self) -> "Node":
        return self._node

    @property
    def pubsub(self) -> "Publisher | Subscription":
        return self._pubsub

    def bind_sensor_output(self, sensor: CarlaSensor) -> Self:
        # 确定传感器对应的 ROS2 消息类型
        if sensor.bp.id.lower().startswith('sensor.camera.'):
            from sensor_msgs.msg import Image
            message_type = Image
        elif sensor.bp.id.lower().startswith('sensor.lidar.'):
            from sensor_msgs.msg import PointCloud2
            message_type = PointCloud2
        else:
            raise ValueError(f"Unsupported sensor type: {sensor.bp.id}")

        # 创建 Publisher 或 Subscription
        if self._pubsub is None:
            self._pubsub = self._node.create_publisher(
                message_type,
                self._topic_name,
                self._qos,
            )
        
        sensor.hook_sensor_data_ready.append(
            lambda data: self._safe_publish(data)
        )
        return self
    
    def _safe_publish(self, data) -> None:
        """安全发布消息"""
        if self._pubsub is None:
            return
        
        try:
            self._pubsub.publish(data.to_ros2(frame_id=self._frame_id, timestamp_source=self._timestamp_source))
        except Exception:
            # context 已被销毁或其他错误，静默忽略
            pass