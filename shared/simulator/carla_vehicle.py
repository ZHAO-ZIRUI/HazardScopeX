import carla
import numpy as np
from typing import TYPE_CHECKING, Any
from typing_extensions import Self, Unpack
from enum import Enum

from shared.simulator import CarlaActor, CarlaBlueprints, CarlaTransform
from shared.data import VehicleDirectControl

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
        EXTERNAL_AUTOPILOT = 2
        MANUAL = 3

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

    @property
    def tf_now_baselink(self) -> carla.Transform:
        """当前帧车辆后轮中心在世界坐标系下的变换, 只读"""
        pos_wheel_bl = self.actor.get_physics_control().wheels[2].position
        pos_wheel_br = self.actor.get_physics_control().wheels[3].position

        pos_baselink = (pos_wheel_bl + pos_wheel_br) / 2 / 100.0  # cm -> m
        return carla.Transform(
            location = pos_baselink,
            rotation = self.actor.get_transform().rotation,
        )

    @control_mode.setter
    def control_mode(self, value: ControlMode):
        self._control_mode = value
        self.logger.info(f"Set control mode to {value.name}")

    @property
    def velocity(self) -> carla.Vector3D:
        """当前帧车辆在世界坐标系下的速度, 只读"""
        return self.actor.get_velocity()

    @property
    def velocity_self(self) -> carla.Vector3D:
        """当前帧车辆在自身坐标系下的速度, 只读"""
        vel = self.velocity
        yaw = np.radians(self.tf_now.rotation.yaw)
        cos_yaw = np.cos(yaw)
        sin_yaw = np.sin(yaw)
        # 世界坐标系到车辆坐标系的旋转 (绕Z轴旋转-yaw)
        return carla.Vector3D(
            x = vel.x * cos_yaw + vel.y * sin_yaw,
            y = -vel.x * sin_yaw + vel.y * cos_yaw,
            z = vel.z,
        )

    @property
    def angular_velocity(self) -> carla.Vector3D:
        """当前帧车辆在世界坐标系下的角速度, 只读"""
        return self.actor.get_angular_velocity()

    @property
    def speed_kmh(self) -> float:
        """当前帧车辆的表显速度, 单位: km/h, 只读"""
        return self.velocity.length() * 3.6

    @property
    def speed_ms(self) -> float:
        """当前帧车辆的表显速度, 单位: m/s, 只读"""
        return self.velocity.length()

    @property
    def control(self) -> carla.VehicleControl:
        """当前帧车辆的控制, 只读"""
        return self.actor.get_control()

    def apply_direct_control(self, control: carla.VehicleControl | VehicleDirectControl) -> Self:
        self.actor.apply_control(control.to_carla() if isinstance(control, VehicleDirectControl) else control)
        return self

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

    # def get_vehicle_center_to_baselink_transform_matrix(self) -> np.ndarray:
    #     """计算从车辆中心在世界坐标系下的变换到后轮中心在世界坐标系下的变换的变换矩阵
        
    #     返回 4x4 齐次变换矩阵，表示从车辆中心在世界坐标系下的变换到后轮中心在世界坐标系下的变换的变换矩阵
    #     旋转部分为单位矩阵，仅包含平移
        
    #     Returns:
    #         np.ndarray: 4x4 变换矩阵
    #     """
    #     # 获取世界坐标系下的变换矩阵
    #     T_world_center = np.array(self.tf_now.get_matrix())
    #     T_world_baselink = np.array(self.tf_now_baselink.get_matrix())
        
    #     # 计算从车辆中心到后轮中心的相对变换矩阵
    #         # center -> baselink
    #     T_baselink_center = np.linalg.inv(T_world_baselink) @ T_world_center
        
    #     # # 提取平移向量
    #     # translation = T_baselink_center[:3, 3]

    #     # 构建新的变换矩阵，旋转部分为单位矩阵
    #     T_result = np.eye(4)
    #     T_result[:3, 3] = T_baselink_center[:3, 3]
        
    #     return T_result

    def get_vehicle_center_to_baselink_transform_matrix(self) -> np.ndarray:
        """计算从车辆中心在世界坐标系下的变换到后轮中心在世界坐标系下的变换的变换矩阵
        
        返回 4x4 齐次变换矩阵，表示从车辆中心在世界坐标系下的变换到后轮中心在世界坐标系下的变换的变换矩阵
        旋转部分为单位矩阵，仅包含平移
        
        Returns:
            np.ndarray: 4x4 变换矩阵
        """
        # 获取世界坐标系下的变换矩阵
        T_center_world = np.array(self.tf_now.get_matrix())
        T_baselink_world = np.array(self.tf_now_baselink.get_matrix())
        
        # 计算从车辆中心到后轮中心的相对变换矩阵
        # T_center_baselink = T_center_world @ inv(T_baselink_world)
        T_world_baselink = np.linalg.inv(T_baselink_world)
        T_center_baselink = T_center_world @ T_world_baselink
        
        # 提取平移向量
        translation = T_center_baselink[:3, 3]
        
        # 构建新的变换矩阵，旋转部分为单位矩阵
        T_result = np.eye(4)
        T_result[:3, 3] = translation
        
        return T_result

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

    @classmethod
    def from_carla(cls, context: 'CarlaContext', actor: carla.Vehicle) -> Self:
        instance = cls(
            context=context,
            bp=actor.type_id,
            tf=actor.get_transform(),
            name=actor.attributes.get('role_name', None),
            ignore_attribute_failure=False,
            ignore_spawn_failure=False,
            is_managed_actor=False,
        )
        instance._actor_ref[0] = actor
        return instance