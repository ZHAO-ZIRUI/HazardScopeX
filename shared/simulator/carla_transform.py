import carla
from dataclasses import dataclass
from typing_extensions import Self


@dataclass
class CarlaTransform:
    """
    carla.Transform 的外部封装
    """

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0

    def __repr__(self) -> str:
        return f"TF(X={self.x:.2f}, Y={self.y:.2f}, Z={self.z:.2f}, Yaw={self.yaw:.2f}, Pitch={self.pitch:.2f}, Roll={self.roll:.2f})"

    def to_carla(self) -> carla.Transform:
        return carla.Transform(
            location=carla.Location(x=self.x, y=self.y, z=self.z),
            rotation=carla.Rotation(yaw=self.yaw, pitch=self.pitch, roll=self.roll),
        )

    def serialize(self) -> dict[str, float]:
        return {
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'yaw': self.yaw,
            'pitch': self.pitch,
            'roll': self.roll,
        }

    @classmethod
    def from_carla(cls, carla_transform: carla.Transform) -> Self:
        return cls(
            x=carla_transform.location.x,
            y=carla_transform.location.y,
            z=carla_transform.location.z,
            yaw=carla_transform.rotation.yaw,
            pitch=carla_transform.rotation.pitch,
            roll=carla_transform.rotation.roll,
        )

    @classmethod
    def deserialize(cls, data: dict[str, float]) -> Self:
        return cls(
            x=data['x'],
            y=data['y'],
            z=data['z'],
            yaw=data['yaw'],
            pitch=data['pitch'],
            roll=data['roll'],
        )

    @staticmethod
    def quat_to_euler(quat: tuple[float, float, float, float]) -> tuple[float, float, float]:
        """四元数转欧拉角（度）

        Args:
            quat: (x, y, z, w) 格式的四元数，与 ROS2 geometry_msgs/Quaternion 一致

        Returns:
            (roll, pitch, yaw) 欧拉角，单位为度
        """
        import math
        x, y, z, w = quat

        # Roll (x-axis rotation)
        sinr_cosp = 2.0 * (w * x + y * z)
        cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
        roll = math.atan2(sinr_cosp, cosr_cosp)

        # Pitch (y-axis rotation)
        sinp = 2.0 * (w * y - z * x)
        if abs(sinp) >= 1.0:
            pitch = math.copysign(math.pi / 2, sinp)  # 万向锁
        else:
            pitch = math.asin(sinp)

        # Yaw (z-axis rotation)
        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        return (math.degrees(roll), math.degrees(pitch), math.degrees(yaw))

    @staticmethod
    def euler_to_quat(euler: tuple[float, float, float]) -> tuple[float, float, float, float]:
        """欧拉角（度）转四元数

        Args:
            euler: (roll, pitch, yaw) 欧拉角，单位为度

        Returns:
            (x, y, z, w) 格式的四元数，与 ROS2 geometry_msgs/Quaternion 一致
        """
        import math
        roll, pitch, yaw = [math.radians(a) for a in euler]

        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)

        w = cr * cp * cy + sr * sp * sy
        x = sr * cp * cy - cr * sp * sy
        y = cr * sp * cy + sr * cp * sy
        z = cr * cp * sy - sr * sp * cy

        return (x, y, z, w)