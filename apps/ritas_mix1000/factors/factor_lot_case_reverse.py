import numpy as np
import carla
import time
from shared.scenarios import Factor
from shared.simulator import *


class FactorLotCaseReverse(Factor):
    NAME = 'F_LotCaseReverse'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/SUSTech_COE_ParkingLot': {
            'ego': 33,
            'npc': [1, 12, 15, 18, 25, 45]
        },
        'Carla/Maps/Town10HD_Opt': {
            'ego': 50, # 12   4   50 
            'npc': [93, 53, 56, 107, 58, 11, 1, 9, 90]
        },
    }

    def __init__(self, context: CarlaContext, vehicle: CarlaVehicle, wait_trigger_seconds: float = 2.0, triggered_seconds: float = 10.0):
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


        tf_act = self._sa.transform_from_waypoint(transform=tf_ego,front_offset=25,left_offset=-0.5)
        # print("tf_ego:",tf_ego," act tf:",tf_act)
        self._act = self._sa.manual_control_vehicle(
            transform=tf_act,
            bp='vehicle.tesla.model3',
        )
        self._vehicles.append(self._act)

        # print("self._sa.get_ego_forward_vector():",self._sa.get_ego_forward_vector())
        v = self._sa.get_ego_forward_vector() * 5
        # print("v:",v)
        # v = carla.Vector3D(x=-2, y=-0.002779, z=0.000000)
        # print("v:",v)
        time.sleep(1)
        # self._sa.set_constant_velocity(self._act, flag=True, velocity=v)
        # self._sa.set_constant_velocity(self._ego, flag=True, velocity=v)

        self._sa.set_velocity_along_the_road(self._act, 30)
        self._sa.set_velocity_along_the_road(self._ego, 30)
        self._act.set_carla_autopilot(enable=True)
        self._ego.set_carla_autopilot(enable=True)
        

        return super().bringup()
    
    def trigger(self) -> None:
        # 如果因子不在等待触发阶段, 则直接返回
        if self.stage != self.FactorStage.WAIT_FOR_TRIGGER:
            return
        # 如果等待触发帧数达到阈值, 则触发因子
        if self._count_before_trigger >= self._wait_trigger_seconds * self._context.fps:
            # self.ego.set_carla_autopilot(enable=True)
            # print("self._sa.get_ego_forward_vector():",self._sa.get_ego_forward_vector())
            # self._sa.set_constant_velocity(self._act, carla.Vector3D(self._sa.get_ego_forward_vector().x * -1, self._sa.get_ego_forward_vector().y * -1, self._sa.get_ego_forward_vector().z))
            # print("self._sa.get_ego_forward_vector():",self._sa.get_ego_forward_vector())
            self._sa.set_constant_velocity(self._act, flag=False)
            self._sa.set_constant_velocity(self._ego, flag=False)
            self._act.set_carla_autopilot(enable=False)
            self._ego.set_carla_autopilot(enable=True)
            self._act = self._sa.manual_control_vehicle(
                vehicle=self._act,
                throttle=1.0,
                reverse=True
            )

            self.stage = self.FactorStage.TRIGGERED
            self.logger.warning(f'Factor {self.NAME} triggered')  # 以警告级别输出
        # print("tf_ego:",self.ego.actor.get_transform())
        # print("ego v:",self.ego.actor.get_velocity())
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