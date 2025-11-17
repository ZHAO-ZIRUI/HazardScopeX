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