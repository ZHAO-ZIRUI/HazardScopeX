from typing import List
from typing_extensions import Self
import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseVehicleFollow(Factor):
    NAME = 'F_CaseVehicleFollow'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town10HD_Opt': {
            'ego': 101,
            'npc': [93, 53, 56, 107, 58]
        },
    }

    WAYPOINTS = [
        carla.Location(x=-3.97,y=28.104,z=0.6),
        carla.Location(x=3,y=28.104,z=0.6),
        carla.Location(x=10,y=28.104,z=0.6),
        carla.Location(x=17.091217, y=28.104216, z=0.6),

        # carla.Location(x=33.091217, y=31.104216, z=0.6),
        # carla.Location(x=38.091217, y=36.104216, z=0.6),
        # carla.Location(x=40.389641, y=41.945496, z=0.6),
        # carla.Location(x=40.389641, y=48, z=0.6),

        carla.Location(x=36,y=28.104,z=0.6),
        carla.Location(x=55,y=28.104,z=0.6),
        carla.Location(x=74.798752, y=28.343533, z=0.6),
        carla.Location(x=74.798752, y=28.343533, z=0.6),
        carla.Location(x=90,y=30,z=0.6),
        carla.Location(x=97,y=34,z=0.6),
        carla.Location(x=99.078560, y=42.141800, z=0.6),
        carla.Location(x=98.800659, y=56.890846, z=0.6),
        carla.Location(x=98.800659, y=69.890846, z=0.6),
        carla.Location(x=98.800659, y=82.890846, z=0.6),
        carla.Location(x=98.800659, y=90.890846, z=0.6),
    ]

    EGO_TRANSFORM_START = carla.Transform(
        carla.Location(x=-16,y=28.104,z=0.6),
        carla.Rotation(pitch=0,yaw=0,roll=0)
    )
    
    ACT_TRANSFORM_START = carla.Transform(
        carla.Location(x=-5,y=28.104,z=0.6),
        carla.Rotation(pitch=0,yaw=0,roll=0)
    )

    def __init__(self, context: CarlaContext, ego_vehicle: CarlaVehicle, shared_path: List[carla.Location] | None = None):
        super().__init__(context)
        self._ego = ego_vehicle
        self._act = None

        if shared_path is not None:
            self._waypoints = shared_path
        else:
            self._waypoints = self.WAYPOINTS

        self._vehicles: list[CarlaVehicle] = []
        self.world = context.world
        self.debug = self.world.debug

        self._ego_path_id = 0
        self._act_path_id = 0

    @property
    def ego_path_id(self) -> int:
        return self._ego_path_id
    
    @property
    def act_path_id(self) -> int:
        return self._act_path_id

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego
    
    @property
    def act(self) -> CarlaVehicle:
        if self._act is None:
            raise RuntimeError("Act vehicle has not been initialized yet.")
        return self._act
    
    @property
    def waypoints(self) -> list[carla.Location]:
        return self._waypoints

    def bringup(self) -> None:

        # 设置 ego 位置
        tf_ego = self.EGO_TRANSFORM_START
        self._ego.actor.set_transform(tf_ego)
        self._vehicles.append(self._ego)

        tf_act = self.ACT_TRANSFORM_START
        act_vehicle = self._context.actors.create_vehicle(
                bp=CarlaBlueprints.VEHICLE_MERCEDES_SPRINTER,
                tf=tf_act,
                name=f'ACT',
                ignore_spawn_failure=True
            )
        act_vehicle.spawn()
        self._act = act_vehicle
        self._vehicles.append(self._act)

        # spectator = self.world.get_spectator()
        # tf_spec = carla.Transform(carla.Location(x=tf_ego.location.x,y=tf_ego.location.y,z=tf_ego.location.z+1.5), tf_ego.rotation)
        # spectator.set_transform(tf_spec)
        
        i = 0
        for location in self.waypoints:
            self.debug.draw_point(location,size=0.3,color=carla.Color(255 - 10 * i,10 * i,10 * i),life_time=1000)
            i += 1

        tm = self._context.traffic
        tm.set_path(self.ego.actor, [self.waypoints[self.ego_path_id]])
        tm.set_path(self.act.actor, [self.waypoints[self.act_path_id]])

        tm.vehicle_percentage_speed_difference(self.ego.actor, -100)
        
        self.ego.set_carla_autopilot(enable=True)
        self.act.set_carla_autopilot(enable=True)
        
        return super().bringup()
    
    def __post_init__(self) -> Self:
        self.hook_update.append(self.trigger)
        self.hook_update.append(self.shift_waypoint)
        self.hook_update.append(self.post_trigger)
        return self

    def shift_waypoint(self) -> None:
        """当自车或目标车接近当前目标点时, 切换到下一个目标点"""
        if self.stage != self.FactorStage.TRIGGERED:
            return

        # 获取位姿
        ego_transform = self.ego.actor.get_transform()
        act_transform = self.act.actor.get_transform()

        # 获取当前目标点
        ego_target_wp = self.waypoints[self.ego_path_id]
        act_target_wp = self.waypoints[self.act_path_id]

        if ego_transform.location.distance(ego_target_wp) < 5.0:
            if self.ego_path_id < len(self.waypoints) - 1:
                self._ego_path_id += 1
                self.logger.info(f'Ego vehicle reached waypoint {self.ego_path_id}, shifting to next waypoint')
                tm = self._context.traffic
                tm.set_path(self.ego.actor, [self.waypoints[self.ego_path_id]])
            if self.ego_path_id == 4:
                self.ego.actor.set_target_velocity(self.ego.actor.get_transform().get_forward_vector() * 17.0)

        if act_transform.location.distance(act_target_wp) < 5.0:
            if self.act_path_id < len(self.waypoints) - 1:
                self._act_path_id += 1
                self.logger.info(f'Act vehicle reached waypoint {self.act_path_id}, shifting to next waypoint')
                tm = self._context.traffic
                tm.set_path(self.act.actor, [self.waypoints[self.act_path_id]])
        
        return
    
    def trigger(self) -> None:
        # 如果因子不在等待触发阶段, 则直接返回
        if self.stage != self.FactorStage.WAIT_FOR_TRIGGER:
            return
        # 如果等待触发帧数达到阈值, 则触发因子
        # if self._count_before_trigger >= self._wait_trigger_seconds * self._context.fps:
        #     self.stage = self.FactorStage.TRIGGERED
        #     self.logger.warning(f'Factor {self.NAME} triggered')  # 以警告级别输出
        # self._count_before_trigger += 1
        self.stage = self.FactorStage.TRIGGERED
        return

    def post_trigger(self) -> None:
        # 如果因子不在触发阶段, 则直接返回
        if self.stage != self.FactorStage.TRIGGERED:
            return
        # 如果触发帧数达到阈值, 则完成因子
        # if self._count_after_trigger >= self._triggered_seconds * self._context.fps:
        #     self.stage = self.FactorStage.COMPLETED
        #     self.logger.warning(f'Factor {self.NAME} completed')  # 以警告级别输出
        # self._count_after_trigger += 1
        ego_transform = self.ego.actor.get_transform()
        last_wp = self.waypoints[-1]

        if last_wp.distance(ego_transform.location) < 3.0:
            self.stage = self.FactorStage.COMPLETED
            self.logger.info(f'Factor {self.NAME} completed')

        return

    def teardown(self) -> None:
        for vehicle in self._vehicles:
            if vehicle is not None and vehicle.is_alive:
                vehicle.set_carla_autopilot(enable=False)
        
        return super().teardown()