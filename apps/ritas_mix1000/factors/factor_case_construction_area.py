import numpy as np
import carla
import random
import time
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseConstructionArea(Factor):
    NAME = 'F_CaseConstructionArea'

    # ego: 50 52 60 70
    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town10HD_Opt': {
            'ego': 50,
            'npc': [93, 53, 56, 107, 58],
            'start_spawn_point': 4,
        },
    }

    def __init__(self, context: CarlaContext, vehicle: CarlaVehicle, wait_trigger_seconds: float = 0.5, triggered_seconds: float = 9000.0, start_location: carla.Location = None, distance: float = 50.0, interval: float = 4.0):
        super().__init__(context)
        self._ego = vehicle
        self._vehicles: list[CarlaVehicle] = []
        self._static_objects: list[CarlaActor] = []
        self._wait_trigger_seconds = wait_trigger_seconds
        self._triggered_seconds = triggered_seconds
        self._count_before_trigger = 0
        self._count_after_trigger = 0
        self.world = context.world
        self.debug = self.world.debug
        self._start_location = start_location
        # self._start_location = carla.Location(x=20,y=13,z=0)
        self._distance = distance
        self._interval = interval

    def __post_init__(self) -> None:
        self.hook_update.append(self.trigger)
        self.hook_update.append(self.post_trigger)
        return

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

        if self._start_location is not None:
            start_tf = self.world.get_map().get_waypoint(self._start_location, project_to_road=True).transform
        else:
            start_tf = self._context.spawn_points[spawn_point_mapping['start_spawn_point']]
        static_waypoint_list = sa.get_path_by_start_point(start_location=start_tf.location, distance=self._distance, interval=self._interval)
        end_tf = static_waypoint_list[-1].transform
        # print("start tf:",start_tf, " end tf:",end_tf)
        # self.debug.draw_point(start_tf.location,size=0.3,color=carla.Color(255,0,0),life_time=1000)
        # self.debug.draw_point(end_tf.location,size=0.3,color=carla.Color(0,0,255),life_time=1000)
        sa.set_spectator(start_tf)

        bp = 'static.prop.streetbarrier'
        for waypoint in static_waypoint_list:
            print(waypoint.transform)
            static_object = sa.create_static_object(
                transform=sa.transform_from_transform(waypoint.transform, left_offset=1.95, front_offset=0, yaw_offset=0),
                bp=bp,
            )
            self._static_objects.append(static_object)
            static_object = sa.create_static_object(
                transform=sa.transform_from_transform(waypoint.transform, left_offset=-1.95, front_offset=0, yaw_offset=0),
                bp=bp,
            )
            self._static_objects.append(static_object)

        static_object = sa.create_static_object(
                transform=sa.transform_from_transform(static_waypoint_list[0].transform, left_offset=1.0, front_offset=-3, yaw_offset=90),
                bp=bp,
        )
        self._static_objects.append(static_object)
        static_object = sa.create_static_object(
                transform=sa.transform_from_transform(static_waypoint_list[0].transform, left_offset=-1.0, front_offset=-3, yaw_offset=90),
                bp=bp,
        )
        self._static_objects.append(static_object)
        print("end point:")
        static_object = sa.create_static_object(
                transform=sa.transform_from_transform(static_waypoint_list[-1].transform, left_offset=1.0, front_offset=3, yaw_offset=90),
                bp=bp,
        )
        self._static_objects.append(static_object)
        static_object = sa.create_static_object(
                transform=sa.transform_from_transform(static_waypoint_list[-1].transform, left_offset=-1.0, front_offset=3, yaw_offset=90),
                bp=bp,
        )
        self._static_objects.append(static_object)



        # create warning
        static_object = sa.create_static_object(
            transform=sa.transform_from_transform(start_tf, left_offset=0, front_offset=-10, yaw_offset=90),
            bp='static.prop.warningconstruction',
        )
        self._static_objects.append(static_object)
        static_object = sa.create_static_object(
            transform=sa.transform_from_transform(end_tf, left_offset=0, front_offset=10, yaw_offset=-90),
            bp='static.prop.warningconstruction',
        )
        self._static_objects.append(static_object)

        # create emergency vehicle
        truck = sa.manual_control_vehicle(
            transform=sa.transform_from_transform(start_tf, left_offset=3.6, front_offset=2, height_offset=0.5, yaw_offset=0),
            bp='vehicle.carlamotors.european_hgv',
            throttle=0.0,
            reverse=True
        )
        self._vehicles.append(truck)
        emergency = sa.manual_control_vehicle(
            transform=sa.transform_from_transform(end_tf, left_offset=3.95, front_offset=-2, height_offset=0.5, yaw_offset=0),
            bp='vehicle.carlamotors.firetruck',
            throttle=0.0,
            reverse=True
        )
        self._vehicles.append(emergency)
        self.debug.draw_point(sa.transform_from_transform(start_tf, left_offset=3.6, front_offset=2, height_offset=0.5, yaw_offset=0).location,size=0.3,color=carla.Color(255,0,0),life_time=1000)
        self.debug.draw_point(sa.transform_from_transform(end_tf, left_offset=3.95, front_offset=-2, height_offset=0.5, yaw_offset=0).location,size=0.3,color=carla.Color(0,0,255),life_time=1000)


        # self.ego.set_carla_autopilot(enable=True)

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