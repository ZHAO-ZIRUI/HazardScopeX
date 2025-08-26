import carla

from .carla_sensor import CarlaSensor
from .carla_context import CarlaContext
from ..data import Image


class CarlaImageSensor(CarlaSensor):

    def __init__(
            self,
            world: carla.World | CarlaContext,
            blueprint: carla.ActorBlueprint | str,
            *,
            name: str | None = None,
            log_level: int | None = None,
    ) -> None:
        """
        :param world: Actor 所在的仿真世界或上下文
        :param blueprint: 蓝图
        :param name: 名称, 为 ``None`` 时自动指定
        :param log_level: 日志等级, 对日志的对象级控制
        """
        super().__init__(world, blueprint, name=name, log_level=log_level)

    def _format_incoming_data(self, data: carla.Image) -> Image:
        return Image.from_carla(data)