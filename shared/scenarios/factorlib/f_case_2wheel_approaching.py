import numpy as np
import carla
import time
import math
from shared.scenarios import Factor
from shared.simulator import *


class FactorCase2WheelApproaching(Factor):
    NAME = 'F_LotCaseReverse'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/SUSTech_COE_ParkingLot': {
            'ego': 33,
            'npc': [1, 12, 15, 18, 25, 45]
        },
        'Carla/Maps/Town10HD_Opt': {
            'ego': 50, # 12      50 
            'npc': [93, 53, 56, 107, 58, 11, 1, 9, 90]
        },
    }

    def __init__(self, 
                 context: CarlaContext, 
                 ego_vehicle: CarlaVehicle, 
                 wait_trigger_seconds: float = 1.8, 
                 triggered_seconds: float = 20.0,
                 ego_init_speed: float = 10.0,
                 act_init_speed: float = 20.0,
                 act_init_left_offset: float = 2.4, 
                 act_init_front_offset: float = -10.0, 
                 act_init_yaw_offset: float = 3.5,
                 target_distance: float = 1.2,
                 background_vehicle_speed = 0.2): 
        super().__init__(context, ego_vehicle)
        self._ego = ego_vehicle
        self._act = None
        self._sa = CarlaSingleAction(self._context, self._ego, self.logger)
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
        self._ego_init_transform = carla.Transform(carla.Location(x=50, y=-67.70, z=1.00),
                                carla.Rotation(pitch=0, yaw=-180, roll=0))
        self._target_distance = target_distance
        self._background_vehicle_speed = background_vehicle_speed

    def __post_init__(self) -> None:
        self.hook_update.append(self.trigger) # type: ignore
        self.hook_update.append(self.post_trigger) # type: ignore
        return

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego

    def bringup(self) -> None:
        self._sa.set_ego(self._ego_init_transform)
        self._vehicles.append(self._ego)
        self._sa.set_spectator(carla.Transform(carla.Location(x=self._ego_init_transform.location.x,y=self._ego_init_transform.location.y,z=self._ego_init_transform.location.z+1.5), self._ego_init_transform.rotation))

        tf_act = carla.Transform(carla.Location(x=50 - self._act_init_front_offset, y=-64.60, z=0.50),
                                    carla.Rotation(pitch=0, yaw=-180, roll=0))
        self._act = self._sa.manual_control_vehicle(
            transform=self._sa.transform_from_transform(transform=tf_act, yaw_offset=self._act_init_yaw_offset),
            bp='vehicle.harley-davidson.low_rider',
            throttle=0.0
        )
        self._vehicles.append(self._act)

        # 匀速前进车辆1
        npc = self._sa.manual_control_vehicle(
            transform=carla.Transform(carla.Location(x=-5.00, y=-57.80, z=0.50),
                               carla.Rotation(pitch=0, yaw=0, roll=0)),
            bp='vehicle.tesla.model3',
            throttle=self._background_vehicle_speed
        )
        self._vehicles.append(npc)

        # 匀速前进车辆2
        npc = self._sa.manual_control_vehicle(
            transform=carla.Transform(carla.Location(x=-18.70, y=-61.00, z=0.50),
                               carla.Rotation(pitch=0, yaw=0, roll=0)),
            bp='vehicle.tesla.model3',
            throttle=self._background_vehicle_speed
        )
        self._vehicles.append(npc)

        for vehicle in self._vehicles:
            self._sa.set_vehicle_light(vehicle, position=True, lowbeam=True, highbeam=True)

        time.sleep(1)
        tm = self._context.traffic
        tm.set_route(self._ego.actor, ['Straight']) 
        tm.auto_lane_change(self._ego.actor, False)

        self._sa.set_velocity(self._ego, velocity=self._sa.normalize_vector(self._sa.get_ego_forward_vector()) * self._ego_init_speed)
        self._sa.set_velocity(self._act, velocity=self._sa.normalize_vector(self._sa.get_forward_vector(self._act)) * self._act_init_speed)


        return super().bringup()
    
    def trigger(self) -> None:
        # 如果因子不在等待触发阶段, 则直接返回
        if self.stage != self.FactorStage.WAIT_FOR_TRIGGER:
            return
        # 如果等待触发帧数达到阈值, 则触发因子
        assert self._act is not None
        front_offset, left_offset, height_offset, yaw_offset = self._sa.offsets_from_transforms(original_transform=self._ego_init_transform,result_transform=self._act.tf_now_baselink)
        if self._count_before_trigger >= self._wait_trigger_seconds * self._context.fps or math.fabs(left_offset) < self._target_distance:
            tm = self._context.traffic
            tm.set_route(self._act.actor, ['Straight']) 
            tm.auto_lane_change(self._act.actor, False)
            self._act.set_carla_autopilot(enable=True)
            self._sa.set_velocity_along_the_road(self._act, speed=self._act_init_speed)
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