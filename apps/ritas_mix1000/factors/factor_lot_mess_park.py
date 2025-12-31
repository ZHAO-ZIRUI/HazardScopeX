import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorLotMessPark(Factor):
    NAME = 'F_LotMessPark'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/SUSTech_COE_ParkingLot': {
            'ego': 33
        },
    }

    def __init__(self, context: CarlaContext, vehicle: CarlaVehicle, wait_trigger_seconds: float = 5.0, triggered_seconds: float = 5.0, 
                 static_vehicle_count: int = 3, s1_left_offset: float = 2.5, s_spacing: float = 7, sn_front_offset: float = 14.0):
        super().__init__(context)
        self._ego = vehicle
        self._vehicles: list[CarlaVehicle] = []
        self._wait_trigger_seconds = wait_trigger_seconds
        self._triggered_seconds = triggered_seconds
        self._count_before_trigger = 0
        self._count_after_trigger = 0
        self._static_vehicle_count = static_vehicle_count
        self._s1_left_offset = s1_left_offset
        self._s_spacing = s_spacing
        self._sn_front_offset = sn_front_offset
        self.world = context.world
        self.debug = self.world.debug

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego

    def bringup(self) -> None:
        sa = CarlaSingleAction(self._context, self._ego, self.logger)

        # 设置 ego 位置
        spawn_point_mapping = self.MAP_SPAWN_POINT_MAPPING[self._context.map.name]
        tf_ego = self._context.spawn_points[spawn_point_mapping['ego']]
        sa.set_ego(tf_ego)
        self._vehicles.append(self._ego)

        sa.set_spectator(carla.Transform(carla.Location(x=tf_ego.location.x,y=tf_ego.location.y,z=tf_ego.location.z+1.5), tf_ego.rotation))

        static_list = sa.lotStatic_parking_car(mix_large=0.1, 
                              mix_emergency=0.1,
                              mix_head_in=0.3, 
                              mix_empty=0.3, 
                              limit_yaw=90.0, 
                              limit_drift_short=3, 
                              limit_drift_long=5)
        self._vehicles.extend(static_list)

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