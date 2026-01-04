from abc import abstractmethod
from typing import List, Tuple
import numpy as np
from .object_state import VehicleState

class DMM():
    """
    工厂类
    """

    @abstractmethod
    def get_future_positions(self, vehicle_state: VehicleState, threshold: float = 5, resolution: float = 0.1) -> List[Tuple[float, float]]:
        """
        根据未来时刻更新车辆状态，并获取点集
        """
        pass

class ConstantAccDMM(DMM):
    """
    常加速度模型。忽略转向和航向，仅使用速度和加速度进行预测。
    """

    def get_future_positions(self, vehicle_state: VehicleState, threshold: float = 5, resolution: float = 0.1):
        # 固定值
        x_0 = vehicle_state.x
        y_0 = vehicle_state.y
        vx_0 = vehicle_state.vx
        vy_0 = vehicle_state.vy
        ax_0 = vehicle_state.ax
        ay_0 = vehicle_state.ay

        position_set = [(x_0, y_0)]
        for t in np.arange(0, threshold, resolution):
            t = float(t)
            x = x_0 + vx_0 * t + ax_0 * t * t / 2
            y = y_0 + vy_0 * t + ay_0 * t * t / 2
            
            position_set.append((x, y))

        return position_set
            

class OneTrackDMM(DMM):
    """
    单轨模型。引入了车辆的航向角和转向角，允许模拟车辆沿曲线行驶的行为。
    """

    def get_future_positions(self, vehicle_state: VehicleState, threshold: float = 5, resolution: float = 0.1):
        # 动态更新
        x = vehicle_state.x
        y = vehicle_state.y
        v = vehicle_state.speed
        psi = vehicle_state.phiv_a       # 航向角

        # 固定值
        a_long = vehicle_state.a_long
        delta = vehicle_state.steer_angle # 转向角
        length = vehicle_state.length
        delta_t = resolution

        # 
        position_set = [(x, y)]
        for t in np.arange(0, threshold, resolution):
            d_x = v * np.cos(psi)
            d_y = v * np.sin(psi)
            d_v = a_long
            d_psi = v / length * np.tan(delta)

            # 计算下一步长的各个值
            x = x + d_x * delta_t
            y = y + d_y * delta_t
            v = v + d_v * delta_t
            psi = psi + d_psi * delta_t

            position_set.append((x, y))
        
        return position_set
    

def time_to_collision(ego_vehicle: VehicleState, target_vehicle: VehicleState, dmm: DMM, threshold: float = 5.0):
    resolution = 0.1
    pos_set1 = dmm.get_future_positions(ego_vehicle, threshold, resolution)
    pos_set2 = dmm.get_future_positions(target_vehicle, threshold, resolution)
    
    assert len(pos_set1) == len(pos_set2)

    ttc = np.inf
    for i in range(len(pos_set1)):
        x1, y1 = pos_set1[i]
        x2, y2 = pos_set2[i]
        
        if (x1 - x2) ** 2 + (y1 - y2) ** 2 < ego_vehicle.radius + target_vehicle.radius:
            ttc = i * resolution
            break
    return ttc