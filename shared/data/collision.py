import carla
from typing_extensions import Self

from shared.data import SimulatorOutput


class Collision(SimulatorOutput):
    """
    碰撞数据
    """
    def __init__(
        self, 
        sim_frame: int, 
        sim_timestamp: float,
        other_actor_id: int,
        other_actor_bp_name: str,
    ):
        super().__init__(sim_frame, sim_timestamp)
        self._raw = (other_actor_id, other_actor_bp_name)

    @property
    def other_actor_id(self) -> int:
        """碰撞对象的ID, 该 ID 为 CARLA 中对象的 ID"""
        return self._raw[0]
    
    @property
    def other_actor_bp_name(self) -> str:
        """碰撞对象的蓝图名称"""
        return self._raw[1]

    @classmethod
    def from_carla(cls, carla_input: carla.CollisionEvent) -> Self:
        return cls(
            sim_frame=carla_input.frame,
            sim_timestamp=carla_input.timestamp,
            other_actor_id=carla_input.other_actor.id,
            other_actor_bp_name=carla_input.other_actor.type_id,
        )