import carla
from typing import Dict 
from typing_extensions import Self

from shared.simulator import CarlaActor
from shared.utils import Logging


class CarlaActorRegistry:
    """
    CARLA Actor 注册表, 用于管理 CARLA Actor 的生命周期
    """

    def __init__(self, world: carla.World):
        self._world = world
        self._actors: Dict[str, CarlaActor] = {}
        self.logger = Logging().get_logger('ActorRegistry')

    @property
    def registry(self) -> Dict[str, CarlaActor]:
        return self._actors

    def __getitem__(self, key: str) -> CarlaActor:
        return self._actors[key]

    def __len__(self) -> int:
        return len(self._actors)

    @property
    def world(self) -> carla.World:
        return self._world

    @world.setter
    def world(self, value: carla.World):
        self.logger.warning(f"World is already set. Overwriting with {value.name}")
        self._world = value
        return

    def add(self, actor: CarlaActor):
        self._actors[actor.id_local] = actor
        self.logger.info(f"Registered actor container '{actor.id_local}'")
        return

    def remove(self, actor: CarlaActor):
        if actor.id_local not in self._actors:
            raise KeyError(f"Actor '{actor.id_local}' not found in registry")
        del self._actors[actor.id_local]
        self.logger.info(f"Removed actor container '{actor.id_local}'")
        return

    def spawn_all(self) -> Self:
        for actor in self._actors.values():
            actor.spawn(self._world)
        return self

    def destroy_all(self) -> Self:
        for actor in self._actors.values():
            actor.destroy(self._world)
        return self