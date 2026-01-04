from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

import carla
import numpy as np

from . import risk
from .constant import RiskConstants
from .dmm import DMM, time_to_collision
from .object_state import VehicleState
from .scenario_context import ScenarioContext, ScenarioContextAdapter, ScenarioContextSingleTargetVehicleFilterAdapter

from shared.utils import Logging

def calculate_risk_value(ego_vehicle: VehicleState, all_vehicle_states: List[VehicleState], X, Y):
        """
        计算单个车辆的风险值

        param X: X 网格
        param Y: Y 网格
        param all_vehicle_states: 所有车辆状态列表
        param ego_id: 自车 ID
        """

        z_prob = calculate_risk_probability(
            ego_vehicle, X, Y
        )
        scene_cost = risk.generate_scene_cost_by_vehicle_states(X, Y, all_vehicle_states, ego_vehicle.vehicle_id)
        
        risk_qrf = np.sum(z_prob)
        
        # return risk_qrf
        # 计算量化感知风险
        z = np.dot(z_prob.flatten(), scene_cost.flatten())
        return z

def calculate_risk_probability(vehicle_state: VehicleState, X, Y):
    """
    计算单个车辆的风险概率分布

    param vehicle_state: 车辆状态
    param X: X 网格
    param Y: Y 网格
    """
    x, y = vehicle_state.x, vehicle_state.y
    speed = vehicle_state.speed

    delta_fut_h = (np.pi / 180) * RiskConstants.STEERING_ANGLE / RiskConstants.SR
    phiv_a = vehicle_state.phiv_a

    delta = risk.gs_delta(delta_fut_h)
    phiv = risk.gs_phiv(phiv_a)
    dla = risk.gs_dla(RiskConstants.TLA, speed)
    R = risk.gs_R(RiskConstants.L, delta)
    xc, yc = risk.gs_center(x, y, phiv, delta, R)
    mexp1 = risk.gs_mexp(RiskConstants.KEXP1, RiskConstants.MCEXP, delta, speed)
    mexp2 = risk.gs_mexp(RiskConstants.KEXP2, RiskConstants.MCEXP, delta, speed)
    arc_len = risk.gs_arclen(X, Y, x, y, delta, xc, yc, R)
    a = risk.gs_a(arc_len, RiskConstants.PAR1, dla)
    sigma1 = risk.gs_sigma(arc_len, mexp1, RiskConstants.CEXP)
    sigma2 = risk.gs_sigma(arc_len, mexp2, RiskConstants.CEXP)
    z_prob = risk.gs_z(X, Y, xc, yc, R, a, sigma1, sigma2)
    return z_prob


class RiskMetricComputer(ABC):
    """
    使用不同指标，计算自车发生碰撞前的风险情况。此类不能直接计算指标
    """

    def __init__(self, fixed_delta_time: float, name: str):
        self.__raw_value = 0.0
        self.__risk_value = 0.0
        self.__accumulate_risk = 0.0
        self.__scenario_context: Optional[ScenarioContext] = None
        self._adapter: Optional[ScenarioContextAdapter] = None
        self.fixed_delta_time = fixed_delta_time
        self.name = name

        # 静态变量
        self._risk_norm_behaviour: Optional[RiskNormalizationBehaviour] = None
        self.DEFAULT_RAW_VALUE = 0.0
        self.DEFAULT_RISK_VALUE = 0.0

        # 日志
        self._logger = Logging().get_logger('RiskComputer')

    def register_norm_behaviour(self, safe_threshold, critical_threshold, risk_bound, inverse: bool = False):
        """风险归一化执行器.默认风险越大越危险。如果 inverse 为真，则风险越小越危险。
        """
        self._risk_norm_behaviour = RiskNormalizationBehaviour(
            safe_threshold=safe_threshold,
            critical_threshold=critical_threshold,
            risk_bound=risk_bound,
            inverse=inverse
        )

    def register_adapter(self, adapter: 'ScenarioContextAdapter'):
        """
        注册场景上下文适配器
        """
        if self._adapter is not None:
            self._logger.warning(f"覆盖已注册的场景上下文适配器: {self._adapter.__class__.__name__} 在 {self.__class__.__name__}")
        self._logger.debug(f"注册场景上下文适配器: {adapter.__class__.__name__} 在 {self.__class__.__name__}")
        self._adapter = adapter

    @property
    def risk_norm_behaviour(self):
        if self._risk_norm_behaviour == None:
            raise RuntimeError("未注册风险归一化执行器！")
        return self._risk_norm_behaviour

    @property
    def RISK_BOUND(self):
        return self.risk_norm_behaviour.RISK_BOUND

    @property
    def raw_value(self):
        if self.__raw_value == np.inf:
            return 1e6
        else:
            return self.__raw_value;

    @property
    def risk_value(self):
        return self.__risk_value

    @property
    def accumulate_risk(self):
        return self.__accumulate_risk
    
    def dump_json(self) -> Dict[str, Any]:
        return {
            'raw_value': self.raw_value,
            'risk': self.risk_value,
            'acc_risk': self.accumulate_risk,
            'scenario_context': self.__scenario_context.dump_json() if self.__scenario_context is not None else None
        }
    
    def __update_metric_value(self, raw_value, risk_value):
        """
        更新指标：原始值、当前风险、累计风险
        """
        self.__raw_value = raw_value
        self.__risk_value = risk_value
        self.__accumulate_risk += self.fixed_delta_time * risk_value

    @abstractmethod
    def is_valid_context(self, scenario_context: ScenarioContext) -> Tuple[bool, str]:
        """
        判断场景上下文是否有效
        """
        if scenario_context.has_target_vehicles == False and scenario_context.has_static_objects == False:
            return False, f"{self.__class__.__name__}: 没有可供计算的车辆或物体"
        return True, f"{self.__class__.__name__}: 场景上下文有效"
    
    def update_metric(self, scenario_context: ScenarioContext):
        """
        根据车辆与环境状态计算当前帧的指标结果

        本方法仅用于实时指标的计算
        """
        if self._adapter is not None:
            scenario_context = self._adapter.adapt(scenario_context)

        flag, msg = self.is_valid_context(scenario_context)
        if flag is False:
            self._logger.debug(msg)
            self.__update_metric_value(self.DEFAULT_RAW_VALUE, self.DEFAULT_RISK_VALUE)
        else:
            self._logger.debug(msg)
            raw_value = self._calculate_raw_value(scenario_context)
            risk = self._calculate_risk(raw_value)
            self.__update_metric_value(raw_value, risk)


    @abstractmethod
    def _calculate_raw_value(self, scenario_context: ScenarioContext):
        """
        计算指标的原始结果
        param scenario_context: 场景上下文
        return: 原始指标结果
        """
        pass

    def _calculate_risk(self, raw_value):
        """
        根据原始结果计算实时风险：通过安全阈值、极限阈值标定风险区间和范围。该方法默认原始值越大越危险
        """
        return self.risk_norm_behaviour.action(raw_value)
    
class DynamicRiskComputer(RiskMetricComputer):
    """
    动态多目标风险计算器基类
    """

    def __init__(self, fixed_delta_time: float, name: str):
        super().__init__(fixed_delta_time, name)
    
    def is_valid_context(self, scenario_context: ScenarioContext) -> Tuple[bool, str]:
        """
        判断场景上下文是否有效
        """
        if not scenario_context.has_target_vehicles:
            return False, f"{self.__class__.__name__}: 没有可供计算的车辆"
        return True, f"{self.__class__.__name__}: 场景上下文有效"


class SingleTargetDynamicRiskComputer(DynamicRiskComputer):
    """
    单目标动态风险计算器基类。注册了单目标过滤适配器
    """

    def __init__(self, fixed_delta_time: float, name: str, carla_map: carla.Map):
        super().__init__(fixed_delta_time, name)
        self._target_vehicle = None
        self.register_adapter(ScenarioContextSingleTargetVehicleFilterAdapter(carla_map))
    
    def is_valid_context(self, scenario_context: ScenarioContext) -> Tuple[bool, str]:
        flag, msg = super().is_valid_context(scenario_context)
        if flag is False:
            return flag, msg
        elif len(scenario_context.other_vehicles) != 1: # pyright: ignore[reportArgumentType]
            return False, f"{self.__class__.__name__}: 单目标风险计算器需要且仅需要一个目标车辆"
        return True, f"{self.__class__.__name__}: 场景上下文有效"

    @property
    def target_vehicle(self):
        return self._target_vehicle

class CRIComputer(DynamicRiskComputer):
    """
    CRI是一个基于势能场的风险评估模型，依靠二维高斯场来实时计算在预期时间内周围车辆与自车的风险情况。

    x_range 和 y_range 表示车辆的计算高斯场的范围。
    """
    def __init__(self, fixed_delta_time, name, x_range: float = 50.0, y_range: float = 50.0, resolution: float = 1.0):
        CRI_SAFE_THRESHOLD = 3.0
        CRI_CIRTICAL_THRESHOLD = 6.0
        CRI_RISK_BOUND = 1e2
        super().__init__(fixed_delta_time, name)
        self.register_norm_behaviour(CRI_SAFE_THRESHOLD, CRI_CIRTICAL_THRESHOLD, CRI_RISK_BOUND)
        self.x_range = x_range
        self.y_range = y_range
        self.resolution = resolution
        self.X = None
        self.Y = None

    
    def set_eval_area_by_ego(self, ego_x, ego_y):
        """以自车位置为中心设置评估区域"""

        zone_x_min = ego_x - self.x_range / 2
        zone_x_max = ego_x + self.x_range / 2
        zone_y_min = ego_y - self.y_range / 2
        zone_y_max = ego_y + self.y_range / 2

        grid_x = np.arange(zone_x_min, zone_x_max + self.resolution, self.resolution)
        grid_y = np.arange(zone_y_min, zone_y_max + self.resolution, self.resolution)
        self.X, self.Y = np.meshgrid(grid_x, grid_y)


    def _calculate_raw_value(self, scenario_context: ScenarioContext):
        assert scenario_context.other_vehicles is not None

        ego_vehicle = scenario_context.ego_vehicle
        other_vehicles = scenario_context.other_vehicles

        self.set_eval_area_by_ego(ego_vehicle.x, ego_vehicle.y)

        all_vehicles = []
        all_vehicles.extend(other_vehicles)
        all_vehicles.append(ego_vehicle)
        risk = calculate_risk_value(
            ego_vehicle,
            all_vehicles,
            self.X,
            self.Y
        )
        self._logger.debug(f"Other Size: {len(other_vehicles)}")
        return risk
    
    def _calculate_risk(self, raw_value):
        risk = np.log10(raw_value+1)
        return super()._calculate_risk(risk)
    
class TTCRiskComputer(SingleTargetDynamicRiskComputer):
    """
    无 DMM 的 TTC (Time to collision) 计算与前车的相对距离和速度来计算碰撞时间
    """

    def __init__(self, fixed_delta_time, name: str, carla_map: carla.Map, dmm: Optional[DMM] = None):
        TTC_SAFE_THRESHOLD = 3.0        # ttc 安全阈值
        TTC_CRITICAL_THRESHOLD = 1.22   # ttc 极限阈值
        TTC_RISK_BOUND = 1e2            # 风险上界
        super().__init__(fixed_delta_time, name, carla_map)
        self.register_norm_behaviour(TTC_SAFE_THRESHOLD, TTC_CRITICAL_THRESHOLD, TTC_RISK_BOUND, True)
        self.DEFAULT_RAW_VALUE = np.inf
        self.dmm = dmm

    def _calculate_raw_value(self, scenario_context: ScenarioContext):
        ego_vehicle = scenario_context.ego_vehicle
        other_vehicles = scenario_context.other_vehicles
        assert other_vehicles is not None

        target_vehicle = other_vehicles[0]
        
        if self.dmm is not None:
            ttc = time_to_collision(ego_vehicle, target_vehicle, self.dmm)
        else:
            # 位置向量
            distance = scenario_context.euclidean_distance()

            # 垂直速度标量
            v_long = ego_vehicle.v_long - target_vehicle.v_long

            # 自车与前车相对静止或前车速度比自车快
            if v_long < RiskConstants.SPEED_THRESHOLD:
                ttc = self.DEFAULT_RAW_VALUE
            # 两车相撞
            elif distance < 0:
                ttc = 0
            else:
                # 两标量相除
                ttc = distance / v_long

                if abs(ttc) < 5.0:
                    self._logger.debug(
                        f'自驾车辆位置和速度信息： x={ego_vehicle.x:.2f}, y={ego_vehicle.y:.2f}, vx={ego_vehicle.vx:.2f}, vy={ego_vehicle.vy:.2f}',
                    )
                    self._logger.debug(
                        f'目标车辆位置和速度信息： x={target_vehicle.x:.2f}, y={target_vehicle.y:.2f}, vx={target_vehicle.vx:.2f}, vy={target_vehicle.vy:.2f}', 
                    )
                    self._logger.info(f'碰撞时间： {ttc:.2f}')
                if abs(ttc) < 0.01:
                    self._logger.warning(f'TTC 数据异常：{ttc:.2f}')
            
        return ttc
    

class DSTRiskComputer(SingleTargetDynamicRiskComputer):
    """
    假定目标车速度不变，在当前相对状态下，自车必须以多大的恒定减速度，
    才能在追尾目标车之前，将两车的间距维持在设定的安全时距 ts

    如果 t_s = 1.0： 这意味着系统要求，一旦自车减速到与目标车速度一致，它们之间的距离必须至少保证目标车行驶 1.0 秒所走的距离。
    """

    
    def __init__(self, fixed_delta_time, name: str, carla_map: carla.Map):
        DST_SAFE_THRESHOLD = 4.0        # 安全刹车减速度
        DST_CRITICAL_THRESHOLD  = 6.0   # 最大刹车减速度
        DST_RISK_BOUND = 1e2            # 风险上界
        super().__init__(fixed_delta_time, name, carla_map)
        self.register_norm_behaviour(DST_SAFE_THRESHOLD, DST_CRITICAL_THRESHOLD, DST_RISK_BOUND)
        self.t_s = 0.0                  # 安全时距

    def _calculate_raw_value(self, scenario_context: ScenarioContext):
        ego_vehicle = scenario_context.ego_vehicle
        other_vehicles = scenario_context.other_vehicles
        assert other_vehicles is not None
        
        target_vehicle = other_vehicles[0]

        delta_p = scenario_context.euclidean_distance()

        vv = (ego_vehicle.v_long - target_vehicle.v_long) * abs(ego_vehicle.v_long - target_vehicle.v_long)

        v2_long = target_vehicle.v_long

        delta_d = 2 * (delta_p - v2_long * self.t_s)

        # 计算 dst
        if delta_d <= 0:
            dst = np.inf
        else:
            dst = max(vv / delta_d, 0)

        return dst


class RLARiskComputer(SingleTargetDynamicRiskComputer):
    """
    对于当前时间点的两个车辆对象，计算自车避免碰撞所需的最大纵向减加速度。
    """

    def __init__(self, fixed_delta_time: float, name: str, carla_map: carla.Map):
        RLA_SAFE_THRESHOLD = -4
        RLA_CRITICAL_THRESHOLD = -8
        RLA_RISK_BOUND = 1e2            # 风险上界
        super().__init__(fixed_delta_time, name, carla_map)
        self.register_norm_behaviour(RLA_SAFE_THRESHOLD, RLA_CRITICAL_THRESHOLD, RLA_RISK_BOUND, True)

    def _calculate_raw_value(self, scenario_context: ScenarioContext):
        ego_vehicle = scenario_context.ego_vehicle
        other_vehicles = scenario_context.other_vehicles
        assert other_vehicles is not None
        
        target_vehicle = other_vehicles[0]

        v1_long = ego_vehicle.v_long
        v2_long = target_vehicle.v_long

        distance = scenario_context.euclidean_distance()

        a2_long = target_vehicle.a_long

        rla = min(a2_long - (v1_long - v2_long) * abs(v1_long - v2_long) / 2 / distance, 0)
        
        self._logger.info(f"需求纵向加速度为：{rla:.2f}")
        return rla
 

# ====================================================
# 静态风险计算
# ====================================================

class StaticRiskComputer(RiskMetricComputer):
    """
    静态环境风险计算器基类。采用模拟激光雷达的点云进行计算
    """

    def __init__(self, fixed_delta_time: float, name: str):
        super().__init__(fixed_delta_time, name)
    
    def is_valid_context(self, scenario_context: ScenarioContext) -> Tuple[bool, str]:
        """
        判断场景上下文是否有效
        """
        if not scenario_context.has_point_cloud:
            return False, f"{self.__class__.__name__}: 点云中没有可供计算的点"
        return True, f"{self.__class__.__name__}: 场景上下文有效"


class DCERiskComputer(StaticRiskComputer):
    """
    对于当前时间点下的自车对象，计算自车对象一定范围内和环境物体的最短距离。
    """

    def __init__(self, fixed_delta_time: float, name: str='dce'):
        DCE_SAFE_THRESHOLD = 3.0
        DCE_CRITICAL_THRESOLD = 1.0
        DCE_RISK_BOUND = 1e2
        super().__init__(fixed_delta_time, name)
        self.register_norm_behaviour(DCE_SAFE_THRESHOLD, DCE_CRITICAL_THRESOLD, DCE_RISK_BOUND, True)
        self.DEFAULT_RAW_VALUE = np.inf

    def _calculate_raw_value(self, scenario_context: ScenarioContext):
        assert scenario_context.point_cloud is not None, "场景上下文缺少点云"

        p, min_distance = scenario_context.point_cloud.get_closest_points_with_hull(scenario_context.ego_vehicle.convex_hull)
        self._logger.debug(f"车辆位置为 {scenario_context.ego_vehicle.p_vector}，获取距离最近点的位置为 {p}")
        return min_distance


class ICRiskComputer(RiskMetricComputer):

    def __init__(self, fixed_delta_time: float, name: str):
        super().__init__(fixed_delta_time, name)
        self.register_norm_behaviour(0.0, 0.0, 1e2)

    def _calculate_raw_value(self, scenario_context: ScenarioContext):
        if scenario_context.is_collision:
            return 1
        else:
            return 0
        
    def is_valid_context(self, scenario_context: ScenarioContext) -> Tuple[bool, str]:
        return True, f"{self.__class__.__name__}: 上下文有效"
        
    def _calculate_risk(self, raw_value):
        if raw_value == 0:
            return 0
        else:
            return self.risk_norm_behaviour.RISK_BOUND


class TTCStaticRiskComputer(StaticRiskComputer):
    """
    基于静态物体的 TTC (Time to collision) 计算与静态物体的相对距离和速度来计算碰撞时间
    """

    def __init__(self, fixed_delta_time, name: str, dmm: Optional[DMM] = None):
        TTC_SAFE_THRESHOLD = 3.0        # ttc 安全阈值
        TTC_CRITICAL_THRESHOLD = 1.22   # ttc 极限阈值
        TTC_RISK_BOUND = 1e2            # 风险上界
        super().__init__(fixed_delta_time, name)
        self.register_norm_behaviour(TTC_SAFE_THRESHOLD, TTC_CRITICAL_THRESHOLD, TTC_RISK_BOUND, True)
        self.DEFAULT_RAW_VALUE = np.inf
        self.dmm = dmm

    def _calculate_raw_value(self, scenario_context: ScenarioContext):
        ego_vehicle = scenario_context.ego_vehicle
        assert scenario_context.static_map is not None
        static_object = scenario_context.static_map.find_nearest_object(ego_vehicle)

        if static_object is None:
            self._logger.warning("未找到最近的静态物体，返回默认 TTC 值。")
            return self.DEFAULT_RAW_VALUE
        min_ttc = np.inf

        # 位置向量
        pos_x = ego_vehicle.x - static_object.x
        pos_y = ego_vehicle.y - static_object.y
        vp = carla.Location(pos_x, pos_y)

        # 垂直速度标量
        speed = ego_vehicle.speed

        # 自车与静态物体相对静止
        if speed < RiskConstants.SPEED_THRESHOLD:
            ttc = self.DEFAULT_RAW_VALUE
        # 两车相撞
        elif vp.length() - ego_vehicle.length / 2 - max(static_object.length, static_object.width) / 2 < 0:
            ttc = 0
        else:
            # 两标量相除
            ttc = (vp.length() - ego_vehicle.length / 2 - max(static_object.length, static_object.width) / 2) / speed

        if ttc < min_ttc:
            min_ttc = ttc
        
        return min_ttc
    
class RiskNormalizationBehaviour:
    """风险归一化执行器.默认风险越大越危险。如果 inverse 为真，则风险越小越危险。
    """

    def __init__(self, safe_threshold, critical_threshold, risk_bound, inverse: bool = False) -> None:
        self.SAFE_THRESHOLD = safe_threshold
        self.CRITICAL_THRESHOLD = critical_threshold
        self.RISK_BOUND = risk_bound
        self.inverse = inverse
        

    def action(self, raw_value) -> float:
        """
        根据原始结果计算实时风险：通过安全阈值、极限阈值标定风险区间和范围。
        """
        if not self.inverse:
            if raw_value < self.SAFE_THRESHOLD:
                risk = 0
            elif raw_value < self.CRITICAL_THRESHOLD:
                risk = self.RISK_BOUND * ((raw_value - self.SAFE_THRESHOLD) / (self.CRITICAL_THRESHOLD - self.SAFE_THRESHOLD)) ** 2
            else:
                risk = self.RISK_BOUND
            return risk
        else:
            if raw_value > self.SAFE_THRESHOLD:
                risk = 0
            elif raw_value > self.CRITICAL_THRESHOLD:
                risk = self.RISK_BOUND * ((raw_value - self.SAFE_THRESHOLD) / (self.CRITICAL_THRESHOLD - self.SAFE_THRESHOLD)) ** 2
            else:
                risk = self.RISK_BOUND
            return risk
