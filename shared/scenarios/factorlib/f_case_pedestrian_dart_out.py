import numpy as np
import carla
import time
import random
import math
from shared.scenarios import Factor
from shared.simulator import *

class FactorCasePedestrianDartOut(Factor):
    NAME = 'F_CasePedestrianDartOut'

    def __init__(self, 
                 context: CarlaContext, 
                 ego_vehicle: CarlaVehicle, 
                 wait_trigger_seconds: float = 3, 
                 triggered_seconds: float = 20.0,
                 ego_init_speed: float = 10.0,
                 target_distance:float = 17.0,
                 pedestrian_appearance_distance: float = 50,
                 lane1_y = -61.00,  # lane1的Y坐标
                 lane2_y = -57.80,  # lane2的Y坐标
                 vehicle_spacing = 8.0): # 车辆间距（米）
        super().__init__(context, ego_vehicle)
        self._ego = ego_vehicle
        self._sa = CarlaSingleAction(self._context, self._ego, self.logger)
        self._vehicles: list[CarlaVehicle] = []
        self._walkers: list[CarlaActor] = []
        self._wait_trigger_seconds = wait_trigger_seconds
        self._triggered_seconds = triggered_seconds
        self._count_before_trigger = 0
        self._count_after_trigger = 0
        self.world = context.world
        self._ego_init_speed = ego_init_speed
        self._target_distance = target_distance
        self._ego_init_transform = None
        self._pedestrian_appearance_distance = pedestrian_appearance_distance
        self._lane1_y = lane1_y
        self._lane2_y = lane2_y
        self._vehicle_spacing = vehicle_spacing

    def __post_init__(self) -> None:
        self.hook_update.append(self.trigger) # type: ignore
        self.hook_update.append(self.post_trigger) # type: ignore
        return

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego
    
    @property
    def act(self) -> CarlaActor:
        return self._ped

    def bringup(self) -> None:
        # 设置 ego 位置
        self._ego_init_transform = carla.Transform(carla.Location(x=18.0+self._pedestrian_appearance_distance, y=-64.50, z=1.00),
                                carla.Rotation(pitch=0, yaw=-180, roll=0))
        self._sa.set_ego(self._ego_init_transform)
        self._vehicles.append(self._ego)
        self._sa.set_spectator(carla.Transform(carla.Location(x=self._ego_init_transform.location.x,y=self._ego_init_transform.location.y,z=self._ego_init_transform.location.z+1.5), self._ego_init_transform.rotation))

        self._ped = self._sa.generate_pedestrian(
            transform=carla.Transform(carla.Location(x=18.0, y=-60.6, z=1.00),
                                      carla.Rotation(pitch=0, yaw=-90, roll=0)),
            bp='walker.pedestrian.0001',
            destination=self._sa.transform_from_transform(transform=carla.Transform(carla.Location(x=18.0, y=-60.6, z=1.00),
                                      carla.Rotation(pitch=0, yaw=-90, roll=0)),front_offset=15),
            speed=0.0,
            jump=False,
        )
        self._walkers.append(self._ped)
        
        # Lane1 车辆组
        for i in range(12):
            npc = self._sa.manual_control_vehicle(
                transform=carla.Transform(carla.Location(x=-18.70 + i*self._vehicle_spacing, y=self._lane1_y, z=0.50),
                                                   carla.Rotation(pitch=0, yaw=0, roll=0)),
                bp=random.choice(CarlaBlueprints.vehicles("car")),
            )
            self._vehicles.append(npc)

        # Lane2 车辆组
        for i in range(12):
            npc = self._sa.manual_control_vehicle(
                transform=carla.Transform(carla.Location(x=-5.00 + i*self._vehicle_spacing, y=self._lane2_y, z=0.50),
                                                   carla.Rotation(pitch=0, yaw=0, roll=0)),
                bp=random.choice(CarlaBlueprints.vehicles("car")),
            )
            self._vehicles.append(npc)

        for vehicle in self._vehicles:
            self._sa.set_vehicle_light(vehicle, position=True, lowbeam=True, highbeam=True)

        time.sleep(1)
        tm = self._context.traffic
        tm.set_route(self._ego.actor, ['Straight']) 
        tm.auto_lane_change(self._ego.actor, False)

        self._sa.set_velocity(self._ego, velocity=self._sa.normalize_vector(self._sa.get_ego_forward_vector()) * self._ego_init_speed)
        # self._ego.set_carla_autopilot(enable=True)

        return super().bringup()
    
    def trigger(self) -> None:
        # 如果因子不在等待触发阶段, 则直接返回
        if self.stage != self.FactorStage.WAIT_FOR_TRIGGER:
            return
        # 如果等待触发帧数达到阈值, 则触发因子
        ped = self._walkers[0]
        front_offset, _, _, _ = self._sa.offsets_from_transforms(original_transform=self._ego.tf_now,result_transform=ped.tf_now)
        if self._count_before_trigger >= self._wait_trigger_seconds * self._context.fps or math.fabs(front_offset) < self._target_distance:
            self._sa.generate_pedestrian(
                pedestrain=ped,
                destination=self._sa.transform_from_transform(transform=carla.Transform(carla.Location(x=18.0, y=-60.6, z=1.00),
                                        carla.Rotation(pitch=0, yaw=-90, roll=0)),front_offset=15),
                speed=0.15,
                jump=False,
            )
            ped.actor.set_simulate_physics(True)
            ped.actor.set_enable_gravity(True)
            
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