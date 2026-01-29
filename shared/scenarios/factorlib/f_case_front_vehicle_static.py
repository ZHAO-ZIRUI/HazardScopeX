import numpy as np
import carla
import time
import math
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseFrontVehicleStatic(Factor):
    NAME = 'F_CaseFrontVehicleStatic'

    def __init__(self, 
                 context: CarlaContext, 
                 ego_vehicle: CarlaVehicle, 
                 wait_trigger_seconds: float = 1.8, 
                 triggered_seconds: float = 20.0,
                 ego_init_speed: float = 10.0,
                 act_init_speed: float = 20.0,
                 act_init_left_offset: float = 2.4, 
                 act_init_front_offset: float = 70.0, 
                 act_init_yaw_offset: float = 3.5,
                 background_vehicle_speed = 0.2): 
        super().__init__(context, ego_vehicle)
        self._ego = ego_vehicle
        self._act = None
        self._sa = CarlaSingleAction(self._context, self._ego, self.logger)
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
        self._background_vehicle_speed = background_vehicle_speed

    def __post_init__(self) -> None:
        self.hook_update.append(self.trigger) # type: ignore
        self.hook_update.append(self.post_trigger) # type: ignore
        return

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego
    
    @property
    def act(self) -> CarlaVehicle:
        if self._act is None:
            raise ValueError("Actor vehicle has not been initialized yet.")
        return self._act

    def bringup(self) -> None:
        # 设置 ego 位置
        self._ego_init_transform = carla.Transform(carla.Location(x=71.50, y=-64.30, z=0.50),
                                carla.Rotation(pitch=0, yaw=-180, roll=0))
        self._sa.set_ego(self._ego_init_transform)
        self._context.wait_ticks(1)
        # self._sa.set_spectator(carla.Transform(carla.Location(x=self._ego_init_transform.location.x,y=self._ego_init_transform.location.y,z=self._ego_init_transform.location.z+1.5), self._ego_init_transform.rotation))

        # 静止车辆1（前方70m）
        static_npc = self._sa.manual_control_vehicle(
            name='ACT',
            transform=carla.Transform(carla.Location(x=71.50-self._act_init_front_offset, y=-65.00, z=0.50),
                               carla.Rotation(pitch=0, yaw=-180, roll=0)),
            bp='vehicle.tesla.model3',
            throttle=0.0
        )
        self._factor_actors["ACT"] = static_npc
        self._act = static_npc

        # 静止车辆2
        static_npc = self._sa.manual_control_vehicle(
            name='NPC_VEHICLE_idx2',
            transform=carla.Transform(carla.Location(x=2.90, y=-68.00, z=0.50),
                               carla.Rotation(pitch=0, yaw=180, roll=0)),
            bp='vehicle.tesla.model3',
            throttle=0.0
        )
        self._factor_actors["NPC_VEHICLE_idx2"] = static_npc

        # 静止车辆3
        static_npc = self._sa.manual_control_vehicle(
            name='NPC_VEHICLE_idx3',
            transform=carla.Transform(carla.Location(x=-7.80, y=-68.10, z=0.50),
                               carla.Rotation(pitch=0, yaw=180, roll=0)),
            bp='vehicle.tesla.model3',
            throttle=0.0
        )
        self._factor_actors["NPC_VEHICLE_idx3"] = static_npc

        # 匀速前进车辆1
        npc = self._sa.manual_control_vehicle(
            name='NPC_VEHICLE_idx4',
            transform=carla.Transform(carla.Location(x=-5.00, y=-57.80, z=0.50),
                               carla.Rotation(pitch=0, yaw=0, roll=0)),
            bp='vehicle.tesla.model3',
            throttle=self._background_vehicle_speed
        )
        self._factor_actors["NPC_VEHICLE_idx4"] = npc

        # 匀速前进车辆2
        npc = self._sa.manual_control_vehicle(
            name='NPC_VEHICLE_idx5',
            transform=carla.Transform(carla.Location(x=-18.70, y=-61.00, z=0.50),
                               carla.Rotation(pitch=0, yaw=0, roll=0)),
            bp='vehicle.tesla.model3',
            throttle=self._background_vehicle_speed
        )
        self._factor_actors["NPC_VEHICLE_idx5"] = npc

        for vehicle in self._factor_actors.values():
            self._sa.set_vehicle_light(vehicle, position=True, lowbeam=True, highbeam=True)

        time.sleep(1)
        tm = self._context.traffic
        tm.set_route(self._ego.actor, ['Straight']) 
        tm.auto_lane_change(self._ego.actor, False)

        self._sa.set_velocity(self._ego, velocity=self._sa.normalize_vector(self._sa.get_ego_forward_vector()) * self._ego_init_speed)


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
        # for vehicle in self._factor_actors.values():
        #     if vehicle is not None and vehicle.actor.is_alive:
        #         vehicle.destroy()
        
        return super().teardown()