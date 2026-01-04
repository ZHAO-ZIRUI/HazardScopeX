
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np

import carla
from .math.mathlib2d import ConvexHull, Point2D, create_vector2d_with_angle, distance_to_hull
from .math.mathlib import Vector

@dataclass
class VehicleState:
    """
    车辆状态类，z轴不参与计算
    """

    frame_id: int
    vehicle_id: int
    x: float  # 位置 x
    y: float  # 位置 y
    z: float  # 位置 z，默认为0
    vx: float # 速度 vx
    vy: float # 速度 vy
    vz: float # 速度 vz
    ax: float # 加速度 ax
    ay: float # 加速度 ay
    az: float # 加速度 az
    length: float # 车辆长度
    width: float  # 车辆宽度
    heading: float # 车辆航向角（角度）
    
    @property
    def p_vector(self) -> Vector:
        return Vector(self.x, self.y, self.z)
    
    @property
    def v_vector(self) -> Vector:
        return Vector(self.vx, self.vy, self.vz)
    
    @property
    def a_vector(self) -> Vector:
        return Vector(self.ax, self.ay, self.az)
    
    @property
    def convex_hull(self) -> ConvexHull:
        long_v = create_vector2d_with_angle(angle_by_degree=self.heading)
        later_v = create_vector2d_with_angle(angle_by_degree=self.heading+90)
        d4 = [
            (1, 1),
            (1, -1),
            (-1, 1),
            (-1, -1)
        ]

        points = []
        for d in d4:
            v = long_v * d[0] * self.length / 2 + later_v * d[1] * self.width / 2
            p = Point2D(self.x, self.y) + v
            points.append(p)
        return ConvexHull(points)

    @property
    def speed(self) -> float:
        """
        速度（标量）
        """
        return np.sqrt(self.vx ** 2 + self.vy ** 2)

    @property
    def radius(self) -> float:
        """
        车辆半径
        """
        return np.sqrt(self.width ** 2 + self.length ** 2) / 2

    @property
    def phiv_a(self) -> float:
        """
        航向角（弧度）
        """
        return (np.pi / 180) * self.heading
    
    @property
    def v_long(self) -> float:
        """
        平行于车辆行进方向的速度（前为正）
        """
        return self.vx * np.cos(self.phiv_a) + self.vy * np.sin(self.phiv_a)
    
    @property
    def v_later(self) -> float:
        """
        垂直于车辆行进方向的速度（左为正）
        """
        return -self.vx * np.sin(self.phiv_a) + self.vy * np.cos(self.phiv_a)

    @property
    def a_long(self) -> float:
        """
        平行于车辆行进方向的加速度（前为正）
        """
        return self.ax * np.cos(self.phiv_a) + self.ay * np.sin(self.phiv_a)
    
    @property
    def a_later(self) -> float:
        """
        垂直于车辆行进方向的速度（左为正）
        """
        return -self.ax * np.sin(self.phiv_a) + self.ay * np.cos(self.phiv_a)

    @property
    def steer_angle(self) -> float:
        """
        转向角（相对于车辆）
        """
        if self.speed < 5:
            return 0.0
        else:
            return np.arctan(self.length * self.a_later / self.speed / self.speed)

    def to_array(self) -> np.ndarray:
        return np.array([self.frame_id, self.vehicle_id, self.x, self.y,
                         self.length, self.width, self.vx, self.vy, self.heading])
    
    def dump_json(self) -> dict:
        """
        导出为 JSON 格式
        """
        return {
            'frame_id': self.frame_id,
            'vehicle_id': self.vehicle_id,
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'vx': self.vx,
            'vy': self.vy,
            'vz': self.vz,
            'ax': self.ax,
            'ay': self.ay,
            'az': self.az,
            'length': self.length,
            'width': self.width,
            'heading': self.heading,
            'speed': self.speed,
            'v_long': self.v_long,
            'a_long': self.a_long,
            'steer_angle': self.steer_angle
        }

@dataclass
class DynamicObjectState:
    """
    动态物体状态类（弱势交通参与者）
    """

    vehicle_state: VehicleState

@dataclass
class VehicleTrajectory:

    vehicle_id: int
    states: List[VehicleState] # 车辆状态列表

    def add_sigle_frame(self, state: VehicleState):
        self.states.append(state)

    def get_single_frame(self, frame_id: int) -> VehicleState:
        """
        获取某一帧的车辆状态
        """
        for state in self.states:
            if state.frame_id == frame_id:
                return state
        raise ValueError(f"Frame ID {frame_id} not found for vehicle ID {self.vehicle_id}")
    
    def get_frames(self, start_frame: int, end_frame: int) -> List[VehicleState]:
        """
        获取某一范围内的车辆状态列表
        """
        return [state for state in self.states if start_frame <= state.frame_id <= end_frame]
    
    def dump_json(self) -> dict:
        """
        导出为 JSON 格式
        """
        return {
            'vehicle_id': self.vehicle_id,
            'states': [s.dump_json() for s in self.states]
        }
    
class PointCloud:
    """
    点云管理类
    """

    def __init__(self, points3d: List[Vector]) -> None:
        self.points3d = points3d

    def get_closest_points(self, point3d: Vector) -> Tuple[Optional[Vector], float]:
        """获取点云中距离目标点最近的点，并输出距离值

        Args:
            point3d (Vector): 目标点

        Returns:
            Tuple[Optional[Vector], float]: 最近的点
        """
        closest_p = None
        min_distance = np.inf
        for p in self.points3d:
            if p.distance(point3d) < min_distance:
                min_distance = p.distance(point3d)
                closest_p = p
        return closest_p, float(min_distance)
    
    def get_closest_points_with_hull(self, hull: ConvexHull) -> Tuple[Optional[Vector], float]:
        """获取点云中距离目标凸包最近的点，并输出距离值

        Args:
            hull (ConvexHull): 目标凸包（二维）

        Raises:
            RuntimeError: _description_
            RuntimeError: _description_

        Returns:
            Tuple[Optional[Vector], float]: 最近的点，距离值
        """
        closest_p = None
        min_distance = np.inf
        for p in self.points3d:
            distance = distance_to_hull(hull, Point2D(p.x, p.y))
            if distance < min_distance:
                min_distance = distance
                closest_p = p
        return closest_p, float(min_distance)

@dataclass
class StaticObjectState:
    """
    静态物体状态类
    """

    object_id: int
    x: float  # 位置 x
    y: float  # 位置 y
    z: float  # 位置 z
    length: float # 物体长度
    width: float  # 物体宽度
    height: float # 物体高度
    heading: float # 物体航向角（角度）

    @property
    def phiv_a(self) -> float:
        """
        航向角（弧度）
        """
        return (np.pi / 180) * self.heading
    
    def dump_json(self) -> dict:
        """
        导出为 JSON 格式
        """
        return {
            'object_id': self.object_id,
            'x': self.x,
            'y': self.y,
            'length': self.length,
            'width': self.width,
            'heading': self.heading
        }

class StaticObjectMap:
    """
    静态物体地图管理类
    """

    def __init__(self, objects: List[StaticObjectState]):
        self.static_objects: List[StaticObjectState] = objects

    def get_all_static_objects(self) -> List[StaticObjectState]:
        return self.static_objects
    
    def find_nearest_object(self, vehicle: VehicleState) -> Optional[StaticObjectState]:
        """
        查找离车辆最近的静态物体
        """
        if self.static_objects is None or len(self.static_objects) == 0:
            raise RuntimeError("Static object map is empty.")

        x, y = vehicle.x, vehicle.y

        min_distance = float('inf')
        nearest_object = None
        for obj in self.static_objects:
            distance = np.sqrt((obj.x - x) ** 2 + (obj.y - y) ** 2)
            if distance < min_distance:
                min_distance = distance
                nearest_object = obj
        return nearest_object
    
    def get_nearest_objects(self, vehicle: VehicleState, radius: float) -> List[StaticObjectState]:
        """
        获取一定半径范围内的静态物体列表
        """
        if self.static_objects is None or len(self.static_objects) == 0:
            raise RuntimeError("Static object map is empty.")

        x, y = vehicle.x, vehicle.y

        nearby_objects = []
        for obj in self.static_objects:
            distance = np.sqrt((obj.x - x) ** 2 + (obj.y - y) ** 2)
            if distance <= radius:
                nearby_objects.append(obj)
        return nearby_objects
    
    def dump_json(self) -> dict:
        """
        导出为 JSON 格式
        """
        return {
            'static_objects': [obj.dump_json() for obj in self.static_objects]
        }

class CarlaStateTransformer():
    """
    Carla 状态转换器: 将 Carla 物体转换为状态信息类
    """

    @staticmethod
    def get_carla_location_from_state(state: VehicleState) -> carla.Location:
        """从 VehicleState 获取 Carla Location"""
        return carla.Location(x=state.x, y=state.y, z=state.z)
    
    @staticmethod
    def get_carla_velocity_from_state(state: VehicleState) -> carla.Vector3D:
        """从 VehicleState 获取 Carla Velocity"""
        return carla.Vector3D(x=state.vx, y=state.vy, z=state.vz)

    @staticmethod
    def vehicle_to_state(vehicle: carla.Vehicle, frame_id: int) -> VehicleState:
        """将 Carla Vehicle 转换为 VehicleState"""
        transform = vehicle.get_transform()
        velocity = vehicle.get_velocity()
        acc = vehicle.get_acceleration()

        location = transform.location
        rotation = transform.rotation

        return VehicleState(
            frame_id=frame_id,
            vehicle_id=vehicle.id,
            x=location.x,
            y=location.y,
            z=location.z,
            vx=velocity.x,
            vy=velocity.y,
            vz=velocity.z,
            ax=acc.x,
            ay=acc.y,
            az=acc.z,
            length=4.5,  # 假设车辆长度为4.5米
            width=2.0,   # 假设车辆宽度为2.0米
            heading=rotation.yaw
        )
    
    @staticmethod
    def static_object_to_state(object: carla.EnvironmentObject | carla.Actor) -> StaticObjectState:
        """将 Carla 物体转换为 StaticObjectState"""
        if isinstance(object, carla.Actor):
            transform = object.get_transform()
        elif isinstance(object, carla.EnvironmentObject):
            transform = object.transform
        return StaticObjectState(
            object_id=object.id,
            x=transform.location.x,
            y=transform.location.y,
            z=transform.location.z,
            length=object.bounding_box.extent.x * 2,
            width=object.bounding_box.extent.y * 2,
            height=object.bounding_box.extent.z * 2,
            heading=transform.rotation.yaw
        )
    
    @staticmethod
    def dynamic_object_to_state(vehicle: carla.Vehicle, frame_id: int) -> DynamicObjectState:
        """将 Carla Vehicle 转换为 DynamicObjectState"""
        vehicle_state = CarlaStateTransformer.vehicle_to_state(vehicle, frame_id)
        return DynamicObjectState(vehicle_state=vehicle_state)