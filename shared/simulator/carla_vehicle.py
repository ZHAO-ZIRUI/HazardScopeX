import carla
from typing_extensions import Self
from enum import Enum

from .carla_actor import CarlaActor
from .carla_vehicle_wheel_info import VehicleWheelFactory



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
    @property
    def get_vehicle_wheels(self) -> list[carla.Location,carla.Location]:
        '''
        获取车辆车轮以计算后轮中心点
        '''
        vehicle_name = self.actor.type_id
        print("the self.vehicle_name is: ",vehicle_name)
        vehicle_wheels_info = VehicleWheelFactory[vehicle_name]
        print("the vehicle_wheels_info.REAR_OVERHANG is: ",vehicle_wheels_info.REAR_OVERHANG.value)
        return []
        # wheels = self.actor.get_physics_control().wheels # 前左、前右、后左、后右
        # try:
        #     if len(wheels) >= 2 :
        #         wheels_sorted = sorted(wheels, key=lambda w: w.location.x)
        #         rear_left_local = wheels_sorted[0].location
        #         rear_right_local = wheels_sorted[1].location

        # except RuntimeError as e:
        #     self.logger.error(f"Failed to disable autopilot before destroy: {e}")



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