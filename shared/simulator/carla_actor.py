import carla
from typing import Dict, Any
from typing_extensions import Self


class CarlaActor:
    """
    carla.Actor 的外部封装, 用于提供高级功能或适配可重启的服务端
    """

    def __init__(
        self,
        bp: carla.ActorBlueprint,
        tf: carla.Transform,
        attach_to: carla.Actor | Self | None = None,
        **attributes: Dict[str, Any],
    ):
        self._actor: None | carla.Actor = None

    @property
    def actor(self) -> carla.Actor | None:
        """
        Returns:
            carla.Actor: 实际在 CARLA 中的 carla.Actor 对象, 如果对象不存在则为 None
        """
        return self._actor

    @actor.setter
    def actor(self, value: carla.Actor | None):
        self._actor = value