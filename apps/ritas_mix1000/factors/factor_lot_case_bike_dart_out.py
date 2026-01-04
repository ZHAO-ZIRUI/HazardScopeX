import numpy as np
import carla
import time
from shared.scenarios import Factor
from shared.simulator import *


class FactorLotCaseBikeDartOut(Factor):
    NAME = 'F_LotCaseBikeDartOut'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/SUSTech_COE_ParkingLot': {
            'ego': 8,
            'npc': [1, 6, 12, 15, 18]
        },
    }

    def __init__(self, context: CarlaContext, vehicle: CarlaVehicle, wait_trigger_seconds: float = 0.5, triggered_seconds: float = 7.0):
        super().__init__(context)
        self._ego = vehicle
        self._sa = None
        self._act = None
        self._vehicles: list[CarlaVehicle] = []
        self._wait_trigger_seconds = wait_trigger_seconds
        self._triggered_seconds = triggered_seconds
        self._count_before_trigger = 0
        self._count_after_trigger = 0
        self.world = context.world
        self.debug = self.world.debug
        self.step = 0

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
        spawn_point_mapping = self.MAP_SPAWN_POINT_MAPPING[self._context.map.name]
        tf_ego = self._context.spawn_points[spawn_point_mapping['ego']]
        self._sa.set_ego(tf_ego)
        self._vehicles.append(self._ego)

        self._sa.set_spectator(carla.Transform(carla.Location(x=tf_ego.location.x,y=tf_ego.location.y,z=tf_ego.location.z+1.5), tf_ego.rotation))

        static_list = self._sa.lotStatic_parking_car(
                              distance=15,
                              mix_large=1.0, 
                              mix_emergency=0.0,
                              mix_head_in=0.1, 
                              mix_empty=0.0, 
                              limit_yaw=0.0, 
                              limit_drift_short=0.0, 
                              limit_drift_long=0.0)
        self._vehicles.extend(static_list)

        vehicles = self._sa.autopilot_traffic(
            nums=30,
            distance=40,
            spawn_point_list=spawn_point_mapping['npc'],
            mix_car=0.7,
            mix_large=0.1,
            mix_emergency=0.1,
            mix_2wheel=0.1,
        )
        self._vehicles.extend(vehicles)

        tf_act = self._sa.transform_from_ego(front_offset=13, left_offset=-6, yaw_offset=-90)
        act = self._sa.manual_control_vehicle(
            transform=tf_act,
            bp='vehicle.yamaha.yzf',
            throttle=0.4,
            reverse=False
        )
        self._vehicles.append(act)
        
        time.sleep(3.5)
        self.ego.set_carla_autopilot(enable=True)

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