import carla
from typing_extensions import Self

from .carla_actor import CarlaActor
from .carla_context import CarlaContext


class CarlaSensor(CarlaActor):
    """
    对 ``carla.Sensor`` 的高级行为进行二次封装
    """

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

    @property
    def actor(self) -> carla.Sensor:
        """
        :return: 当前封装类所对应的 ``carla.Sensor`` 实例, Actor 未 Spawn 或者已经被销毁时返回 ``None``
        """
        return super()._actor

    def destroy(self) -> None:
        """
        从 CARLA Server 中销毁当前 Sensor, 如果 Sensor 还在监听数据, 先停止监听避免可能的错误.
        """
        if self.is_alive and self.actor.is_listening():
            self.actor.stop()
        return super().destroy()

    def spawn(
            self,
            transform: carla.Transform | None = None,
            *,
            x: float = None,
            y: float = None,
            z: float = None,
            yaw: float = None,
            pitch: float = None,
            roll: float = None,
            attach: carla.Actor | Self = None,
    ) -> Self:
        super().spawn(transform, x=x, y=y, z=z, yaw=yaw, pitch=pitch, roll=roll, attach=attach)
        self.actor.listen(lambda data: self._listen_callback(data))
        return self

    def _resolve_blueprint(self, bp: carla.ActorBlueprint | str) -> carla.ActorBlueprint:
        blueprint = super()._resolve_blueprint(bp)
        if not str(blueprint.id).startswith('sensor.'):
            msg = f"Failed on blueprint resolve: required blueprint ({str(blueprint.id)}) is not a sensor."
            self.logger.error(msg)
            raise AttributeError(msg)
        return blueprint

    def _listen_callback(self, data: carla.SensorData):
        """
        数据监听的回调函数
        :param data: ``carla.SensorData`` 类型
        """
        raise NotImplementedError()