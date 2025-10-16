import carla

from shared.simulator import CarlaActor


class CarlaSensor(CarlaActor):
    """
    carla.Sensor 的外部封装, 用于提供高级功能或适配可重启的服务端
    """

    def __init__(
        self,
        bp: carla.ActorBlueprint,
        name: str = '',
        actor: carla.Actor | None = None,
    ):
        super().__init__(bp=bp, name=name, actor=actor)