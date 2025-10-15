import carla
from typing import Dict
from typing_extensions import Self

from shared.simulator import CarlaActor, CarlaVehicle, CarlaSensor


class CarlaFactory:
    """
    CARLA 工厂, 用于创建 CARLA Actor
    """

    def __init__(
        self,
        world: carla.World,
        blueprint_library: carla.BlueprintLibrary,
    ):
        self._world = world
        self._blueprint_library = blueprint_library
        self._registry: Dict[str, CarlaActor] = {}

    def create_actor(self) -> CarlaActor:
        pass

    def create_vehicle(self) -> CarlaVehicle:
        pass
    
    def create_sensor(self) -> CarlaSensor:
        pass

    def spawn(self, actor: CarlaActor) -> Self:
        pass

    def destroy(self, actor: CarlaActor) -> Self:
        pass

    def spawn_all(self) -> Self:
        pass

    def destroy_all(self) -> Self:
        pass

    def _process_blueprint(self, blueprint: str | carla.Blueprint) -> carla.Blueprint:
        pass