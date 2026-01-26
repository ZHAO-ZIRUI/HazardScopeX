import numpy as np
import carla
import random
import math
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseBoxesFallDown(Factor):
    NAME = 'F_CaseBoxesFallDown'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town10HD_Opt': {
            'ego': 50,
            'npc': [93, 53, 56, 107, 58, 20, 11, 9, 52, 30, 40]
        },
    }

    def __init__(self, context: CarlaContext, vehicle: CarlaVehicle, wait_trigger_seconds: float = 2.0, triggered_seconds: float = 12.0):
        super().__init__(context)
        self._sa = None
        self._ego = vehicle
        self._box = None
        self._vehicles: list[CarlaVehicle] = []
        self._static_objects: list[CarlaActor] = []
        self._wait_trigger_seconds = wait_trigger_seconds
        self._triggered_seconds = triggered_seconds
        self._count_before_trigger = 0
        self._count_after_trigger = 0
        self.world = context.world
        self.debug = self.world.debug

    def __post_init__(self) -> None:
        self.hook_update.append(self.trigger)
        self.hook_update.append(self.post_trigger)
        return
    
    BOX_BLUEPRINTS = [
                'static.prop.box01',
                'static.prop.box02',
                'static.prop.box03',
            ]

    BOX_OFFSET_LIST = [
        (0.35, 10, 4.5),
        (-0.35, 10, 4.5),
        (0.0, 11.0, 4.5),
    ]

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

        self._sa.manual_control_vehicle(
            bp='vehicle.mitsubishi.fusorosa',
            transform=self._sa.transform_from_ego(left_offset=0.3, front_offset=13, height_offset=0.0, yaw_offset=0.0),
            throttle=0.3
        )

        for i, (left_offset, front_offset, height_offset) in enumerate(self.BOX_OFFSET_LIST):
             bp = random.choice(self.BOX_BLUEPRINTS)
             self._box = self._sa.create_static_object(
                 transform=self._sa.transform_from_ego(left_offset=left_offset, front_offset=front_offset, height_offset=height_offset, yaw_offset=0.0),
                 bp=bp
             )

        return super().bringup()
    
    def trigger(self) -> None:
        # 如果因子不在等待触发阶段, 则直接返回
        if self.stage != self.FactorStage.WAIT_FOR_TRIGGER:
            return
        # 如果等待触发帧数达到阈值, 则触发因子
        if self._count_before_trigger >= self._wait_trigger_seconds * self._context.fps:
            self.stage = self.FactorStage.TRIGGERED
            self.logger.warning(f'Factor {self.NAME} triggered')  # 以警告级别输出

            self.ego.set_carla_autopilot(enable=True)
            tf_ego = self._ego.tf_now_baselink
            self._sa.object_fly_away(object=self._box, 
                                     vector=self._sa.normalize_vector(tf_ego.get_forward_vector()),
                                     force=-25)

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
    