import carla
import math

from typing import TYPE_CHECKING, Callable
from typing_extensions import Self

from shared.define import TimestampSource

if TYPE_CHECKING:
    from shared.simulator import CarlaContext, CarlaTransform
    from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
    from geometry_msgs.msg import TransformStamped

class ROS2TfAdapter():

    def __init__(
        self,
        context: 'CarlaContext',
        ros2_tf_broadcaster: 'TransformBroadcaster | StaticTransformBroadcaster',
        frame_id_parent: str,
        frame_id_child: str,
        timestamp_source: TimestampSource = TimestampSource.OS,
    ):
        # 在实例化的时候执行实际引入
        from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster

        self._context = context
        self._ros2_tf_broadcaster = ros2_tf_broadcaster
        self._timestamp_source = timestamp_source
        self._frame_id_parent = frame_id_parent
        self._frame_id_child = frame_id_child

        self._is_static = isinstance(ros2_tf_broadcaster, StaticTransformBroadcaster)
        self._is_hook_registered = False
        self._relation = None
        

    def bind_relation(self, relation: carla.Transform | Callable[[], carla.Transform]) -> Self:
        # 整理输入
        # 延迟导入以避免循环引用
        from shared.simulator import CarlaTransform
        relation = relation.to_carla() if isinstance(relation, CarlaTransform) else relation
        assert isinstance(relation, carla.Transform) or callable(relation), f"Unsupported relation type: {type(relation)}"

        # 如果是静态则直接发送变换
        if self._is_static:
            relation_now = relation() if callable(relation) else relation
            self._ros2_tf_broadcaster.sendTransform(self._get_transform(relation_now))
            return self

        # 动态要求绑定必须是 Callable 的
        assert callable(relation), f"Using TransformBroadcaster binding must be a callable"
        self._relation: Callable[[], carla.Transform] = relation
        
        # 注册钩子
        self._context.hook_on_tick.append(self._hookfunc_on_tick_tf_broadcast)
        self._is_hook_registered = True

        return self

    def destroy(self) -> Self:
        # 只销毁对 hook 的影响, ROS2 的资源释放由 CarlaIOManager 负责
        if self._is_hook_registered:
            self._context.hook_on_tick.remove(self._hookfunc_on_tick_tf_broadcast)
            self._is_hook_registered = False
        return self

    def _hookfunc_on_tick_tf_broadcast(self, _: carla.WorldSnapshot) -> None:
        if self._relation is None:
            return
        relation_now = self._relation()
        self._ros2_tf_broadcaster.sendTransform(self._get_transform(relation_now))

    def _get_transform(self, relation: carla.Transform) -> 'TransformStamped':
        from geometry_msgs.msg import TransformStamped, Transform, Vector3, Quaternion
        from std_msgs.msg import Header
        from builtin_interfaces.msg import Time

        # 位置: CARLA (x, y, z) -> ROS2 (x, y, z)
        translation_carla = relation.location
        translation_ros2 = Vector3(
            x = translation_carla.x,
            y = -translation_carla.y,  # CARLA Y 轴取反
            z = translation_carla.z,
        )

        # 旋转: CARLA 欧拉角 (pitch, yaw, roll) -> ROS2 四元数
        rotation_carla = relation.rotation

        pitch_rad = math.radians(rotation_carla.pitch)
        yaw_rad = math.radians(-rotation_carla.yaw)
        roll_rad = math.radians(-rotation_carla.roll)

        cy = math.cos(yaw_rad * 0.5)
        sy = math.sin(yaw_rad * 0.5)
        cp = math.cos(pitch_rad * 0.5)
        sp = math.sin(pitch_rad * 0.5)
        cr = math.cos(roll_rad * 0.5)
        sr = math.sin(roll_rad * 0.5)

        rotation_ros2 = Quaternion(
            x = sr * cp * cy - cr * sp * sy,
            y = cr * sp * cy + sr * cp * sy,
            z = cr * cp * sy - sr * sp * cy,
            w = cr * cp * cy + sr * sp * sy,
        )

        return TransformStamped(
            header = Header(
                stamp = self._context.clock.to_ros2(Time, self._timestamp_source),
                frame_id = self._frame_id_parent,
            ),
            child_frame_id = self._frame_id_child,
            transform = Transform(
                translation = translation_ros2,
                rotation = rotation_ros2,
            )
        )
        