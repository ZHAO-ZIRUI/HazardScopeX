import carla
from typing_extensions import Self
from enum import Enum
import numpy as np

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
    
    def get_vehicle_center_to_rear_transform_matrix(self) -> np.ndarray:
        '''
        获取车辆车轮以计算后轮中心点,对应于自车坐标系(x向前，y向右，z向上,左手坐标系) 此处 转换与y轴坐标系方向无关，故不需考虑左右手坐标系
        '''
        vehicle_name = self.actor.type_id
        vehicle_wheels_info = VehicleWheelFactory[vehicle_name]
        vehicle_length = vehicle_wheels_info.VEHICLE_LENGTH.value
        # 计算车辆后轮的位置 车辆中心后移一定位置至后轮中心
        vehicle_rear_wheel_center_x = -vehicle_length / 2.0 + vehicle_wheels_info.REAR_OVERHANG.value
        dx = -vehicle_rear_wheel_center_x
        vehicle_rear_wheel_center_z_offset = -(vehicle_wheels_info.VEHICLE_HEIGHT.value / 2.0 - vehicle_wheels_info.WHEEL_RADIUS.value)
        dz = -vehicle_rear_wheel_center_z_offset
        # 构造 4x4 齐次矩阵
        T_R_C = np.eye(4,dtype=float)
        T_R_C[0,3] = dx # 方向平移
        T_R_C[2,3] = dz# z 方向平移
        return T_R_C

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