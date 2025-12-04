import carla
from typing import TYPE_CHECKING, Any
from typing_extensions import Self, Unpack
from enum import Enum

from shared.simulator import CarlaActor, CarlaBlueprints, CarlaTransform

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


class CarlaVehicle(CarlaActor):
    """
    carla.Vehicle 的外部封装, 用于提供高级功能或适配可重启的服务端
    """

    ID_GENERATOR_HEADER = "Vehicle_"

    class ControlMode(Enum):
        NONE = 0
        CARLA_AUTOPILOT = 1

    def __init__(
        self,
        context: 'CarlaContext',
        bp: carla.ActorBlueprint | CarlaBlueprints | str,
        tf: carla.Transform | CarlaTransform,
        *,
        name: str | None = None,
        ignore_attribute_failure: bool = False,
        ignore_spawn_failure: bool = False,
        is_managed_actor: bool = True,
        **attributes: Unpack[dict[str, Any]],
    ):
        super().__init__(
            context=context,
            bp=bp,
            tf=tf,
            parent=None,
            name=name,
            ignore_attribute_failure=ignore_attribute_failure,
            ignore_spawn_failure=ignore_spawn_failure,
            is_managed_actor=is_managed_actor,
            **attributes,
        )
        self._control_mode = self.ControlMode.NONE

    @property
    def actor(self) -> carla.Vehicle:
        """carla.Vehicle 实例, 只读"""
        return super().actor

    @property
    def control_mode(self) -> ControlMode:
        """车辆的控制模式标志"""
        return self._control_mode

    @control_mode.setter
    def control_mode(self, value: ControlMode):
        self._control_mode = value
        self.logger.info(f"Set control mode to {value.name}")

    def set_carla_autopilot(self, enable: bool = True) -> Self:
        """设置 CARLA 自动驾驶模式"""
        if not self.is_alive:
            msg = f"Cannot set autopilot for vehicle '{self.name}' because it is not alive"
            self.logger.error(msg)
            raise RuntimeError(msg)
        
        if enable:
            self.control_mode = self.ControlMode.CARLA_AUTOPILOT
            self.actor.set_autopilot(True)
        else:
            self.control_mode = self.ControlMode.NONE
            self.actor.set_autopilot(False)
        return self

    def destroy(self) -> Self:
        """销毁 Vehicle 实例"""
        if self._actor_ref[0] is None:
            return self
        
        # 如果 autopilot 启用，先禁用以避免 CARLA 内部清理错误
        if self._control_mode == self.ControlMode.CARLA_AUTOPILOT:
            try:
                if self.is_alive:
                    self.actor.set_autopilot(False)
                    self._control_mode = self.ControlMode.NONE
            except RuntimeError as e:
                self.logger.warning(f"Failed to disable autopilot before destroy: {e}")
        
        return super().destroy()