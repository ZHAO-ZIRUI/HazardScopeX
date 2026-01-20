from typing import TYPE_CHECKING, Callable, Generic, TypeVar
from typing_extensions import Self

if TYPE_CHECKING:
    from shared.simulator import CarlaContext
    from rclpy.subscription import Subscription

MsgT = TypeVar('MsgT')

class ROS2SubAdapter(Generic[MsgT]):
    """ROS2 订阅适配器，支持延迟绑定回调函数"""
    
    def __init__(
        self,
        context: 'CarlaContext',
        ros2_sub: 'Subscription',
        message_type: type[MsgT],
    ):
        self._context = context
        self._ros2_sub = ros2_sub
        self._user_callbacks: list[Callable[[MsgT], None]] = []
        self._message_type = message_type

    def _internal_callback(self, msg: MsgT) -> None:
        """内部回调函数，转发消息到用户回调"""
        for callback in self._user_callbacks:
            callback(msg)

    def bind_callback(self, callback: Callable[[MsgT], None]) -> Self:
        """设置接收消息时的回调函数"""
        self._user_callbacks.append(callback)
        return self

    def destroy(self) -> Self:
        # 只销毁对 hook 的影响, ROS2 的资源释放由 CarlaIOManager 负责
        pass