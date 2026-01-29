import numpy as np
import carla
import time
import math
import random
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseHighwayMerge(Factor):
    NAME = 'F_CaseHighWayMerge'

    def __init__(self, 
                 context: CarlaContext, 
                 vehicle: CarlaVehicle, 
                 wait_trigger_seconds: float = 1.8, 
                 triggered_seconds: float = 20.0,
                 ego_init_speed: float = 10.0,
                 act_init_speed: float = 20.0,
                 act_init_left_offset: float = 2.4, 
                 act_init_front_offset: float = -10.0, 
                 act_init_yaw_offset: float = 3.5,
                 ego_distance_to_merge: float = 56,  # ego车辆离汇入点距离（米）
                 merge_vehicle_speed: float = 60,  # 汇入车辆速度（km/h)
                 merge_point_x: float = -16.6,
                 merge_point_y: float = -54.8):
        super().__init__(context)
        self._ego = vehicle
        self._act = None
        self._sa = None
        self._vehicles: list[CarlaVehicle] = []
        self._wait_trigger_seconds = wait_trigger_seconds
        self._triggered_seconds = triggered_seconds
        self._count_before_trigger = 0
        self._count_after_trigger = 0
        self.world = context.world
        self.debug = self.world.debug
        self._ego_init_speed = ego_init_speed
        self._act_init_speed = act_init_speed
        self._act_init_left_offset = act_init_left_offset
        self._act_init_front_offset = act_init_front_offset
        self._act_init_yaw_offset = act_init_yaw_offset
        self._ego_init_transform = None
        self._ego_distance_to_merge = ego_distance_to_merge
        self._merge_vehicle_speed = merge_vehicle_speed
        self._merge_point_x = merge_point_x
        self._merge_point_y = merge_point_y


    def __post_init__(self) -> None:
        self.hook_update.append(self.trigger)
        self.hook_update.append(self.post_trigger)
        return

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego

    def bringup(self) -> None:
        self._sa = CarlaSingleAction(self._context, self._ego, self.logger)

        # 设置 ego 位置
        self._ego_init_transform = carla.Transform(
            carla.Location(x=self._merge_point_x, y=self._merge_point_y - self._ego_distance_to_merge, z=1.0),
            carla.Rotation(pitch=0, yaw=90, roll=0)
        )
        self._sa.set_ego(self._ego_init_transform)
        self._vehicles.append(self._ego)
        self._sa.set_spectator(carla.Transform(carla.Location(x=self._ego_init_transform.location.x,y=self._ego_init_transform.location.y,z=self._ego_init_transform.location.z+1.5), self._ego_init_transform.rotation))

        # tf_act = carla.Transform(
        #     carla.Location(x=-46.1, y=-95.3, z=1.0),
        #     carla.Rotation(pitch=0, yaw=24.999969, roll=0)
        # )
        # self._act = self._sa.manual_control_vehicle(
        #     transform=self._sa.transform_from_transform(transform=tf_act, yaw_offset=self._act_init_yaw_offset),
        #     bp=random.choice(CarlaBlueprints.vehicles("car")),
        #     throttle=0.0
        # )
        # self._vehicles.append(self._act)
        # map = self.world.get_map()
        # merge_waypoint = map.get_waypoint(self._act.get_location(), project_to_road=True)
        # if merge_waypoint:
        #     # 将汇入车辆移动到最近的waypoint上
        #     self._act.set_transform(carla.Transform(merge_waypoint.transform.location + carla.Location(z=0.5), 
        #                                             merge_waypoint.transform.rotation))


        map = self.world.get_map()
        merge_waypoint = map.get_waypoint(carla.Location(x=-46.1, y=-95.3, z=1.0), project_to_road=True)
        if merge_waypoint:
            # 将汇入车辆移动到最近的waypoint上
            tf_act = carla.Transform(merge_waypoint.transform.location + carla.Location(z=0.5), 
                                                    merge_waypoint.transform.rotation)
        else:
            tf_act = carla.Transform(
            carla.Location(x=-46.1, y=-95.3, z=1.0),
            carla.Rotation(pitch=0, yaw=24.999969, roll=0)
        )
        self._act = self._sa.manual_control_vehicle(
            transform=tf_act,
            bp=random.choice(['vehicle.tesla.model3' ]),
            throttle=0.0
        )
        self._vehicles.append(self._act)


        time.sleep(1)
        tm = self._context.traffic
        tm.set_route(self._ego.actor, ['Straight']) 
        tm.set_desired_speed(self._act.actor, self._merge_vehicle_speed)
        tm.set_desired_speed(self._ego.actor, self._merge_vehicle_speed)
        tm.ignore_lights_percentage(self._act.actor, 100)  # 忽略红绿灯
        tm.ignore_vehicles_percentage(self._act.actor, 100)
        tm.ignore_vehicles_percentage(self._ego.actor, 100)
        tm.set_global_distance_to_leading_vehicle(2.5)
        tm.auto_lane_change(self._ego.actor, False)
        self._act.set_carla_autopilot(enable=True)
        self._ego.set_carla_autopilot(enable=True)

        return super().bringup()
    
    def trigger(self) -> None:
        # 如果因子不在等待触发阶段, 则直接返回
        if self.stage != self.FactorStage.WAIT_FOR_TRIGGER:
            return
        # 如果等待触发帧数达到阈值, 则触发因子
        if self._count_before_trigger >= self._wait_trigger_seconds * self._context.fps:
            self.stage = self.FactorStage.TRIGGERED
            self.logger.warning(f'Factor {self.NAME} triggered')  # 以警告级别输出
        self._count_before_trigger += 1
        return

    def post_trigger(self) -> None:
        # 如果因子不在触发阶段, 则直接返回
        if self.stage != self.FactorStage.TRIGGERED:
            return
        # 如果触发帧数达到阈值, 则完成因子
        if self._count_after_trigger >= self._triggered_seconds * self._context.fps:
            self.stage = self.FactorStage.COMPLETED
            self.logger.warning(f'Factor {self.NAME} completed')  # 以警告级别输出
        self._count_after_trigger += 1
        return

    def teardown(self) -> None:
        for vehicle in self._vehicles:
            if vehicle is not None and vehicle.is_alive:
                vehicle.set_carla_autopilot(enable=False)
        
        return super().teardown()