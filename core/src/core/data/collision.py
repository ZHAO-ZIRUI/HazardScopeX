import carla
from typing_extensions import Self

from core.data import SimulatorOutput


class Collision(SimulatorOutput):
    """
    碰撞传感器的数据
    """
    def __init__(
            self,
            frame_id: int,
            timestamp_sim: float,
            other_actor_id: int,
            other_actor_bp_name: str,
    ) -> None:
        super().__init__(frame_id, timestamp_sim)
        self._data = (other_actor_id, other_actor_bp_name)

    @property
    def other_id(self) -> int:
        """碰撞目标的 Actor ID"""
        return self._data[0]

    @property
    def other_bp_name(self) -> str:
        """碰撞目标的蓝图 ID"""
        return self._data[1]

    @property
    def is_collision_with_vehicle(self) -> bool:
        return self.other_bp_name.startswith("vehicle.")

    @classmethod
    def from_carla(cls, data: carla.CollisionEvent) -> Self:
        target: carla.Actor = data.other_actor
        instance = cls(
            frame_id=data.frame,
            timestamp_sim=data.timestamp,
            other_actor_id=target.id,
            other_actor_bp_name=target.type_id
        )
        return instance