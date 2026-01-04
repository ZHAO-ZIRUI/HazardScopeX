import os
import sys

from .risk.dmm import OneTrackDMM

sys.path.append(os.path.join(os.path.dirname(__file__)))

from typing import Dict, List
import carla
from .risk import *
from .carla_adapter import CarlaEvaluatorAdapter

from shared.utils import Logging

class EvalManager:

    METRICS_CLASS_DICT: Dict[str, RiskMetricComputer.__class__] = {
        'ttc': TTCRiskComputer,
        'dst': DSTRiskComputer,
        'rla': RLARiskComputer,
        'cri': CRIComputer,
        'dce': DCERiskComputer,
        'ic': ICRiskComputer
    }
    
    def __init__(self, carla_adapter: CarlaEvaluatorAdapter, ego_vehicle: carla.Vehicle) -> None:
        """
        评估管理对象
        param ego_vehicle: 自车 Carla 车辆对象
        """
        self.carla_adapter = carla_adapter
        self.ego_vehicle = ego_vehicle

        # 通知者
        self.debugger = None
        self.computers: List[RiskMetricComputer] = []

        self._scenario_context = None
        self._logger = Logging().get_logger('EvalManager')

    @property
    def normalized_risk_value(self) -> float:
        """获取单帧的归一化风险值

        Raises:
            RuntimeError: 如果没有注册风险指标，返回报错信息

        Returns:
            float: 归一化风险值
        """
        if len(self.computers) > 0:
            res = 0
            # 如果 IC 为真，则直接赋值为1
            for comp in self.computers:
                if isinstance(comp, ICRiskComputer):
                    if comp.raw_value == 1:
                        self._logger.debug(f'发生碰撞！风险值为 1.')
                        return 1.0
                    
            # 否则加权计算风险值并归一化
            for comp in self.computers:
                p = comp.risk_value / comp.RISK_BOUND # [0, 1]
                res += p
            res /= len(self.computers)
            self._logger.debug(f'归一化风险值为 {res:.2f}.')
        else:
            raise RuntimeError("Risk computer is not registered.")
        return res

    @property
    def risk_value(self) -> Dict[str, float]:
        """获取单帧的风险值字典，包含注册的风险指标

        Raises:
            RuntimeError: 如果没有注册风险指标，返回报错信息

        Returns:
            Dict[str, float]: 风险值字典，包含注册的风险指标及风险值
        """
        if len(self.computers) > 0:
            return {computer.name: computer.risk_value for computer in self.computers}
        else:
            raise RuntimeError("Risk computer is not registered.")
    
    @property
    def accumulate_risk_value(self)-> Dict[str, float]:
        """获取累计帧数下的风险值字典，包含注册的风险指标

        Raises:
            RuntimeError: 如果没有注册风险指标，返回报错信息

        Returns:
            Dict[str, float]: 风险值字典，包含注册的风险指标及风险值
        """
        if len(self.computers) > 0:
            return {computer.name: computer.accumulate_risk for computer in self.computers}
        else:
            raise RuntimeError("Risk computer is not registered.")

    @property
    def scenario_context(self):
        return self._scenario_context

    @property
    def single_target_scenario_context(self):
        if self.scenario_context is None:
            return None
        return ScenarioContextSingleTargetVehicleFilterAdapter(self.carla_adapter.world.get_map()).adapt(self.scenario_context)

    def dump_risk_metrics(self) -> Dict[str, Dict[str, float]]:
        if len(self.computers) > 0:
            return {computer.name: computer.dump_json() for computer in self.computers}
        else:
            raise RuntimeError("Risk computer is not registered.")

    def register_world_debugger(self, debugger):
        """注册世界调试器"""
        self.debugger = debugger

    def unregister_world_debugger(self):
        """注销世界调试器"""
        self.debugger = None

    def register_risk_computer(self, metric_name: str, fixed_delta_time: float):
        """注册风险计算器"""

        if self.METRICS_CLASS_DICT.get(metric_name):
            _class = self.METRICS_CLASS_DICT[metric_name]
            if issubclass(_class, SingleTargetDynamicRiskComputer):
                self.computers.append(_class(fixed_delta_time, metric_name, self.carla_adapter.world.get_map()))
            elif issubclass(_class, ICRiskComputer):
                self.computers.append(_class(fixed_delta_time, metric_name))
                # 对自车注册碰撞传感器
                self.carla_adapter.register_collision_sensor(self.ego_vehicle)
            else:
                self.computers.append(_class(fixed_delta_time, metric_name))

    def unregister_risk_computer(self, metrics_name: str):
        """注销风险计算器"""
        rm_c = None
        for c in self.computers:
            if c.name == metrics_name:
                rm_c = c
        if rm_c is not None:
            self.computers.remove(rm_c)

    def run_evaluation_in_frame(self, frame_id: int):
        """执行一帧的评估流程"""
        world = self.carla_adapter.world
        ego_vehicle = self.ego_vehicle
        other_vehicles = self.carla_adapter.select_vehicles(ego_vehicle.id)
        collision_event = self.carla_adapter.get_collision_event()           # 如果注册了碰撞检测器，则可能有碰撞事件

        # 场景上下文
        self._scenario_context = carla_world_to_scenario_context(frame_id, world, self.ego_vehicle, other_vehicles, self.carla_adapter.lidar_cast_ray(self.ego_vehicle), collision_event)
        
        risk_values = []

        if len(self.computers) is not None:
            for computer in self.computers:
                computer.update_metric(self._scenario_context)
                risk_values.append(computer.risk_value)
        else:
            raise RuntimeError("Risk computer is not registered.")