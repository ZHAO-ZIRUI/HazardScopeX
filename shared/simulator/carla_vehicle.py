import carla
from typing_extensions import Self
from enum import Enum

from shared.simulator import CarlaActor


class CarlaVehicle(CarlaActor):
    """
    carla.Vehicle 的外部封装, 用于提供高级功能或适配可重启的服务端
    """

    class ControlMode(Enum):
        NONE = 0
        CARLA_AUTOPILOT = 1

    def __init__(
        self,
        bp: carla.ActorBlueprint,
        name: str = '',
        actor: carla.Actor | None = None,
    ):
        super().__init__(bp=bp, name=name, actor=actor)
        self._control_mode = self.ControlMode.NONE

    @property
    def control_mode(self) -> ControlMode:
        return self._control_mode

    @control_mode.setter
    def control_mode(self, value: ControlMode):
        self._control_mode = value
        self.logger.info(f"Set control mode to {value.name}")
        return

    def set_carla_autopilot(self, enable: bool = True) -> Self:
        if enable:
            self.control_mode = self.ControlMode.CARLA_AUTOPILOT
            self.actor.set_autopilot(True)
        else:
            self.control_mode = self.ControlMode.NONE
            self.actor.set_autopilot(False)
        return self

    def destroy(self) -> Self:
        if self._actor is None:
            return self
        
        # 如果 autopilot 启用，先禁用以避免 CARLA 内部清理错误
        if self._control_mode == self.ControlMode.CARLA_AUTOPILOT:
            try:
                if self._actor.is_alive:
                    self._actor.set_autopilot(False)
                    self._control_mode = self.ControlMode.NONE
            except RuntimeError as e:
                self.logger.warning(f"Failed to disable autopilot before destroy: {e}")
        
        return super().destroy()