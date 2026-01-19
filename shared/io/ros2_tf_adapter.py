import math
from typing import TYPE_CHECKING
from typing_extensions import Self

from shared.io import AbstractIOAdapter
from shared.simulator import CarlaSensor


if TYPE_CHECKING:
    from shared.simulator import CarlaContext
    from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
    from geometry_msgs.msg import TransformStamped

class ROS2TfAdapter(AbstractIOAdapter):
    
    def __init__(
        self, 
        context: 'CarlaContext', 
        frame_id_parent: str, 
        frame_id_child: str,
        tf_broadcaster: 'TransformBroadcaster | StaticTransformBroadcaster',
    ):
        super().__init__(context)
        self._frame_id_parent = frame_id_parent
        self._frame_id_child = frame_id_child
        self._tf_broadcaster = tf_broadcaster
        self._tf_stamped = None

    @property
    def tf_stamped(self) -> 'TransformStamped':
        return self._tf_stamped

    def bind_sensor(self, sensor: CarlaSensor) -> Self:
        from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
        from geometry_msgs.msg import TransformStamped, Transform, Vector3
        from std_msgs.msg import Header

        tf_init = sensor.tf_init
        
        # 位置: CARLA (x, y, z) -> ROS2 (x, y, z)
        translation = Vector3(
            x=tf_init.location.x,
            y=-tf_init.location.y,  # CARLA Y 轴取反
            z=tf_init.location.z,
        )
        
        # 旋转: CARLA 欧拉角 (pitch, yaw, roll) -> ROS2 四元数
        rotation = self._carla_rotation_to_quaternion(
            pitch=tf_init.rotation.pitch,
            yaw=tf_init.rotation.yaw,
            roll=tf_init.rotation.roll,
        )

        self._tf_stamped = TransformStamped(
            header=Header(frame_id=self._frame_id_parent),
            child_frame_id=self._frame_id_child,
            transform=Transform(translation=translation, rotation=rotation),
        )

        # 如果是静态 TF 广播器, 则直接发送变换
        # 如果是动态 TF 广播器, 则将变换添加到缓冲区
        if isinstance(self._tf_broadcaster, StaticTransformBroadcaster):
            self._tf_broadcaster.sendTransform(self._tf_stamped)
        return self

    @staticmethod
    def _carla_rotation_to_quaternion(pitch: float, yaw: float, roll: float):
        """将 CARLA 欧拉角转换为 ROS2 四元数
        
        CARLA 使用 UE4 坐标系 (左手系, 度数), ROS2 使用右手系
        """
        from geometry_msgs.msg import Quaternion
        
        # 转换为弧度
        pitch_rad = math.radians(pitch)
        yaw_rad = math.radians(-yaw)  # CARLA yaw 取反
        roll_rad = math.radians(-roll)  # CARLA roll 取反
        
        # 欧拉角 (ZYX 顺序) 转四元数
        cy = math.cos(yaw_rad * 0.5)
        sy = math.sin(yaw_rad * 0.5)
        cp = math.cos(pitch_rad * 0.5)
        sp = math.sin(pitch_rad * 0.5)
        cr = math.cos(roll_rad * 0.5)
        sr = math.sin(roll_rad * 0.5)

        return Quaternion(
            x=sr * cp * cy - cr * sp * sy,
            y=cr * sp * cy + sr * cp * sy,
            z=cr * cp * sy - sr * sp * cy,
            w=cr * cp * cy + sr * sp * sy,
        )