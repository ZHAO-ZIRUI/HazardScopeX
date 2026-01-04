import carla
from dataclasses import dataclass
from typing import List, Optional, Tuple
from .object_state import PointCloud, VehicleState, CarlaStateTransformer, StaticObjectMap
import numpy as np
from .math import Vector
from shared.utils.logging import Logging

def carla_world_to_scenario_context(frame_id: int, world: carla.World, ego_vehicle: carla.Vehicle, other_vehicles: List[carla.Vehicle], points: List[carla.Location], collision_event) -> 'ScenarioContext':
    """
    将 Carla 世界转换为场景上下文
    """
    # 自车状态转换
    ego_state = CarlaStateTransformer.vehicle_to_state(ego_vehicle, frame_id)

    # 动态车辆转换
    other_vehicle_states = []
    for vehicle in other_vehicles:
        vehicle_state = CarlaStateTransformer.vehicle_to_state(vehicle, frame_id)
        other_vehicle_states.append(vehicle_state)

    # 点云获取
    point_cloud = PointCloud([Vector(p.x, p.y, p.z) for p in points])

    # 静态物体转换
    # all_static_object_states = []
    # if static_objects is not None:
    #     # 静态物体转换
    #     for s_object in static_objects:
    #         s_object_state = CarlaStateTransformer.static_object_to_state(s_object)
    #         all_static_object_states.append(s_object_state)

    # 访问 World 获取静态物体列表（碰撞箱有一定问题）
    # all_objs: List[carla.EnvironmentObject] = world.get_environment_objects()

    # objs: List[carla.EnvironmentObject] = []
    # ego_loc = ego_vehicle.get_transform().location
    # for obj in all_objs:
    #     obj_loc = obj.transform.location
    #     if ego_loc.distance_2d(obj_loc) - obj.bounding_box.extent.length() < RiskConstants.STATIC_OBJECT_DETECTION_RADIUS:
    #         objs.append(obj)
    # static_map = StaticObjectMap([CarlaStateTransformer.static_object_to_state(obj) for obj in objs])
    # static_map = StaticObjectMap()  

    return ScenarioContext(
        frame_id=frame_id,
        ego_vehicle=ego_state,
        other_vehicles=other_vehicle_states,
        static_map=None,
        point_cloud=point_cloud,
        is_collision=True if collision_event is not None else False
    )

@dataclass
class ScenarioContext:
    """
    场景上下文类
    """

    frame_id: int
    ego_vehicle: VehicleState                     # 自车状态
    other_vehicles: Optional[List[VehicleState]]  # 场景中其他车辆的状态列表
    static_map: Optional[StaticObjectMap]         # 静态物体管理器
    point_cloud: Optional[PointCloud]             # 激光雷达的点云
    is_collision: bool                            # 是否发生碰撞

    @property
    def has_target_vehicles(self):
        return self.other_vehicles is not None and len(self.other_vehicles) > 0
    
    @property
    def has_static_objects(self):
        return self.static_map is not None and len(self.static_map.get_all_static_objects()) > 0

    @property
    def has_point_cloud(self):
        return self.point_cloud is not None and len(self.point_cloud.points3d) > 0

    def euclidean_distance(self, box_included=True):
        """计算两个车辆的欧氏距离


        Args:
            box_included (bool, optional): 是否包含碰撞盒. Defaults to True.

        Raises:
            RuntimeError: 判断其他车辆是否合法

        Returns:
            float
        """
        if self.other_vehicles is None:
            raise RuntimeError("没有其他车辆，无法计算！")
        
        if len(self.other_vehicles) != 1:
            raise RuntimeError("车辆数量不为 1！")

        pv1 = self.ego_vehicle.p_vector
        pv2 = self.other_vehicles[0].p_vector

        if box_included:
            return pv1.distance(pv2) - self.ego_vehicle.length / 2  - self.other_vehicles[0].length / 2
        return pv1.distance(pv2)
    

    def dump_json(self) -> dict:
        """
        导出为 JSON 格式
        """
        return {
            'frame_id': self.frame_id,
            'ego_vehicle': self.ego_vehicle.dump_json(),
            'euclidean_distance': self.euclidean_distance() if self.other_vehicles is not None and len(self.other_vehicles) == 1 else None,
            'other_vehicles': [v.dump_json() for v in self.other_vehicles] if self.other_vehicles is not None else [],
            'static_map': self.static_map.dump_json() if self.static_map is not None else None
        }


class ScenarioContextAdapter:
    """
    场景上下文适配器基类
    """

    def __init__(self) -> None:
        self._logger = Logging().get_logger('ScenarioContextAdapter')

    def adapt(self, scenario_context: ScenarioContext) -> ScenarioContext:
        """
        适配场景上下文
        """
        return scenario_context

    
class ScenarioContextSingleTargetVehicleFilterAdapter(ScenarioContextAdapter):
    """
    场景上下文单个目标车辆过滤适配器
    """
    def __init__(self, carla_map: carla.Map) -> None:
        super().__init__()
        self.carla_map = carla_map

    def adapt(self, scenario_context: ScenarioContext) -> ScenarioContext:
        """
        过滤场景上下文中的其他车辆
        """
        filtered_vehicles = self._filter_vehicles(scenario_context)
        return ScenarioContext(
            frame_id=scenario_context.frame_id,
            ego_vehicle=scenario_context.ego_vehicle,
            other_vehicles=filtered_vehicles,
            static_map=None,
            point_cloud=None,
            is_collision=scenario_context.is_collision
        )
    
    def get_forward_connected_wps(self, wp) -> list[carla.Waypoint]:
        """
        获取航点所在道路 相邻道路航点的方法
        """
        forward_connected_wps = []

        topology = self.carla_map.get_topology()
        for start_wp, end_wp in topology:
            if start_wp.road_id == wp.road_id and start_wp.lane_id == wp.lane_id:
                # print(f"当前道路 (Road {wp.road_id}) 连接到 Road {end_wp.road_id}")

                # if end_wp.is_junction:
                #     # 你找到了下一个连接的道路的入口 Waypoint
                #     print(f"  --> 这是一个路口连接。下一个路口 Waypoint ID: {end_wp.id}")
                    
                #     # 通过 next_until_lane_change 或 next_waypoints 
                #     # 可以进一步探索路口内部和后续道路信息
                # else:
                #     print(f"这不是一个路口！")
                
                forward_connected_wps.append(end_wp)
                # world.debug.draw_point(end_wp.transform.location)
                # print(end_wp.id, end_wp.lane_id, end_wp.road_id, end_wp.is_junction, end_wp.junction_id)
        return forward_connected_wps
    
    def _filter_vehicles(self, scenario_context: ScenarioContext) -> Optional[List[VehicleState]]:
        """
        过滤其他车辆的具体实现，子类需重写此方法
        """
        if not scenario_context.has_target_vehicles:
            self._logger.debug("场景中除自车外没有其他车辆，无法过滤！")
            return None
        assert scenario_context.other_vehicles is not None

        other_vehicles = scenario_context.other_vehicles

        ego_location = CarlaStateTransformer.get_carla_location_from_state(scenario_context.ego_vehicle)

        ego_wp = self.carla_map.get_waypoint(ego_location)

        # 获取额外航点
        forward_wps = self.get_forward_connected_wps(ego_wp)
        forward_wps.append(ego_wp)

        min_dis_vehicle = None
        min_dis = np.inf
        for npc_vehicle in other_vehicles:
            npc_location = CarlaStateTransformer.get_carla_location_from_state(npc_vehicle)

            wp = self.carla_map.get_waypoint(npc_location)

            # 仅考虑车辆不在交叉口处的情况
            # 需要额外考虑一个前方道路
            # if ego_wp.is_junction == False:
            is_same_lane = (wp.lane_id == ego_wp.lane_id and wp.road_id in [wp.road_id for wp in forward_wps])
            # else:
                # is_same_lane = False

            p1 = ego_location
            p2 = npc_location
            delta_p = p2 - p1
            ego_v = CarlaStateTransformer.get_carla_velocity_from_state(scenario_context.ego_vehicle)
            if delta_p.dot(ego_v) > 0 and ego_v.length() > 1e-6 and is_same_lane:
                distance = p1.distance_2d(p2)
                if min_dis > distance:
                    min_dis = distance
                    min_dis_vehicle = npc_vehicle
        
        # Update all_vehicles
        if min_dis_vehicle is not None:
            
            self._target_vehicle = min_dis_vehicle
            return [min_dis_vehicle]
        else:
            self._target_vehicle = None
            return None
    
class ScenarioContextClosestStaticObjectFilterAdapter(ScenarioContextSingleTargetVehicleFilterAdapter):
    """
    场景上下文最近静态物体过滤适配器
    """

    def adapt(self, scenario_context: ScenarioContext) -> ScenarioContext:
        """
        过滤场景上下文中的所有静态物体，仅保留与自车最近的静态物体相关车辆
        """
        raise NotImplementedError("该适配器尚未实现。")