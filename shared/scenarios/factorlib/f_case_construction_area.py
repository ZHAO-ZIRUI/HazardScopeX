import math

import carla
from typing_extensions import Self

from shared.scenarios import Factor
from shared.simulator import CarlaContext, CarlaVehicle, CarlaActor


class FactorCaseConstructionArea(Factor):
    NAME = 'F_CaseConstructionArea'

    MAPPING_WORLD_LOCATION = {
        'Carla/Maps/Town10HD_Opt': {
            Factor.K_EGO: 100,
            Factor.K_OBSTACLE: 4,
            Factor.K_NPC_VEHICLE: [11, 12, 13, 14, 5],
        },
    }

    def __init__(
        self,
        context: CarlaContext,
        ego_vehicle: CarlaVehicle,
        wait_trigger_seconds: float = 0.5,
        triggered_seconds: float = 5.0,
        start_location: carla.Location | None = None,
        distance: float = 50.0,
        interval: float = 4.0,
        *,
        ignore_factor_ego_control: bool = False,
    ):
        super().__init__(
            context,
            ego_vehicle,
            ignore_factor_ego_control=ignore_factor_ego_control,
            keepalive_after_triggered_seconds=int(triggered_seconds),
        )
        self._wait_trigger_seconds = wait_trigger_seconds
        self._start_location = start_location
        self._distance = distance
        self._interval = interval

        self._world = context.world
        self._debug = self._world.debug

        self._count_before_trigger = 0
        self._static_index = 0

    def __post_init__(self) -> Self:
        # 初始化阶段钩子
        self.hook_bringup.append(self.move_ego_vehicle_to_init_tf)
        self.hook_bringup.append(self._create_construction_area_actors)
        self.hook_bringup.append(self.create_npc_vehicles)
        self.hook_bringup.append(self.spawn_all_factor_actors)
        self.hook_bringup.append(self.apply_npc_vehicles_carla_autopilot)
        # self.hook_bringup.append(self._apply_ego_vehicle_carla_autopilot)

        # 运行阶段钩子
        self.hook_update.append(self._update_trigger_by_time)
        self.hook_update.append(self.keepalive_after_triggered)

        # 销毁阶段钩子
        self.hook_teardown.append(self._disable_ego_autopilot)

        return super().__post_init__()

    def _create_construction_area_actors(self) -> None:
        """创建施工区域内的静态物体和应急车辆。"""
        start_tf = self._get_start_transform()
        static_waypoint_list = self._get_path_by_start_point(
            start_location=start_tf.location,
            distance=self._distance,
            interval=self._interval,
        )

        if not static_waypoint_list:
            self.logger.warning('No waypoints found for construction area, skip creating construction actors')
            return

        end_tf = static_waypoint_list[-1].transform

        # 设置观测视角
        # spectator = self._world.get_spectator()
        # spectator.set_transform(start_tf)

        bp_barrier = 'static.prop.streetbarrier'
        # 沿路径两侧布置路障
        for waypoint in static_waypoint_list:
            left_tf = self._transform_from_transform(
                transform=waypoint.transform,
                left_offset=1.95,
                front_offset=0.0,
                height_offset=0.0,
                yaw_offset=0.0,
            )
            right_tf = self._transform_from_transform(
                transform=waypoint.transform,
                left_offset=-1.95,
                front_offset=0.0,
                height_offset=0.0,
                yaw_offset=0.0,
            )
            self._create_static_object(left_tf, bp_barrier)
            self._create_static_object(right_tf, bp_barrier)

        # 入口路障
        self._create_static_object(
            self._transform_from_transform(
                transform=static_waypoint_list[0].transform,
                left_offset=1.0,
                front_offset=-3.0,
                height_offset=0.0,
                yaw_offset=90.0,
            ),
            bp_barrier,
        )
        self._create_static_object(
            self._transform_from_transform(
                transform=static_waypoint_list[0].transform,
                left_offset=-1.0,
                front_offset=-3.0,
                height_offset=0.0,
                yaw_offset=90.0,
            ),
            bp_barrier,
        )

        # 出口路障
        self._create_static_object(
            self._transform_from_transform(
                transform=static_waypoint_list[-1].transform,
                left_offset=1.0,
                front_offset=3.0,
                height_offset=0.0,
                yaw_offset=90.0,
            ),
            bp_barrier,
        )
        self._create_static_object(
            self._transform_from_transform(
                transform=static_waypoint_list[-1].transform,
                left_offset=-1.0,
                front_offset=3.0,
                height_offset=0.0,
                yaw_offset=90.0,
            ),
            bp_barrier,
        )

        # 施工警示牌
        bp_warning = 'static.prop.warningconstruction'
        self._create_static_object(
            self._transform_from_transform(
                transform=start_tf,
                left_offset=0.0,
                front_offset=-10.0,
                height_offset=0.0,
                yaw_offset=90.0,
            ),
            bp_warning,
        )
        self._create_static_object(
            self._transform_from_transform(
                transform=end_tf,
                left_offset=0.0,
                front_offset=10.0,
                height_offset=0.0,
                yaw_offset=-90.0,
            ),
            bp_warning,
        )

        # 应急车辆：施工卡车和消防车（静止停放）
        # truck_tf = self._transform_from_transform(
        #     transform=start_tf,
        #     left_offset=3.6,
        #     front_offset=2.0,
        #     height_offset=0.5,
        #     yaw_offset=0.0,
        # )
        # firetruck_tf = self._transform_from_transform(
        #     transform=end_tf,
        #     left_offset=3.95,
        #     front_offset=-2.0,
        #     height_offset=0.5,
        #     yaw_offset=0.0,
        # )

        # truck = self._context.actors.create_vehicle(
        #     bp='vehicle.carlamotors.european_hgv',
        #     tf=truck_tf,
        #     name='CONSTRUCTION_TRUCK',
        # )
        # firetruck = self._context.actors.create_vehicle(
        #     bp='vehicle.carlamotors.firetruck',
        #     tf=firetruck_tf,
        #     name='CONSTRUCTION_FIRETRUCK',
        # )

        # self._factor_actors['CONSTRUCTION_TRUCK'] = truck
        # self._factor_actors['CONSTRUCTION_FIRETRUCK'] = firetruck

        # 可视化调试点
        # self._debug.draw_point(
        #     truck_tf.location,
        #     size=0.3,
        #     color=carla.Color(255, 0, 0),
        #     life_time=1000,
        # )
        # self._debug.draw_point(
        #     firetruck_tf.location,
        #     size=0.3,
        #     color=carla.Color(0, 0, 255),
        #     life_time=1000,
        # )

    def _get_start_transform(self) -> carla.Transform:
        """获取施工区域路径的起始 Transform。"""
        if self._start_location is not None:
            waypoint = self._world.get_map().get_waypoint(self._start_location, project_to_road=True)
            return waypoint.transform

        spawn_point_mapping = self.MAPPING_WORLD_LOCATION[self._context.map_name]
        return self._context.spawn_points[spawn_point_mapping[Factor.K_OBSTACLE]]

    def _get_path_by_start_point(
        self,
        *,
        start_location: carla.Location,
        distance: float,
        interval: float,
    ) -> list[carla.Waypoint]:
        """
        从起点开始规划一条确定的 Waypoint 路径。
        逻辑参考 CarlaSingleAction.get_path_by_start_point, 但不依赖 CarlaSingleAction。
        """
        if start_location is None:
            self.logger.error('Initial location is not passed in.')
            return []

        carla_map = self._world.get_map()
        current_wp = carla_map.get_waypoint(start_location, project_to_road=True)

        if current_wp is None:
            self.logger.error('Cannot find waypoint for start location.')
            return []

        path: list[carla.Waypoint] = []
        for _ in range(int(distance / interval)):
            path.append(current_wp)

            next_wps = current_wp.next(interval)
            if not next_wps:
                self.logger.warning('Road ends when generating construction area waypoints')
                break

            next_wp = next_wps[0]
            if current_wp.is_junction and len(next_wps) > 1:
                # 路口时简化为选择第一个出口
                next_wp = next_wps[0]

            current_wp = next_wp

        return path

    def _transform_from_transform(
        self,
        *,
        transform: carla.Transform,
        left_offset: float = 0.0,
        front_offset: float = 0.0,
        height_offset: float = 0.0,
        yaw_offset: float = 0.0,
    ) -> carla.Transform:
        """在给定 Transform 基础上施加横向/纵向/高度偏移。"""
        ego_location = transform.location
        ego_rotation = transform.rotation
        yaw_rad = math.radians(ego_rotation.yaw)

        forward_x = math.cos(yaw_rad) * front_offset
        forward_y = math.sin(yaw_rad) * front_offset

        left_x = math.cos(yaw_rad - math.pi / 2.0) * left_offset
        left_y = math.sin(yaw_rad - math.pi / 2.0) * left_offset

        total_offset_x = forward_x + left_x
        total_offset_y = forward_y + left_y

        result_location = carla.Location(
            x=ego_location.x + total_offset_x,
            y=ego_location.y + total_offset_y,
            z=ego_location.z + height_offset,
        )

        rotation = carla.Rotation(
            pitch=transform.rotation.pitch,
            yaw=transform.rotation.yaw + yaw_offset,
            roll=transform.rotation.roll,
        )
        return carla.Transform(location=result_location, rotation=rotation)

    def _create_static_object(self, transform: carla.Transform, bp: str) -> None:
        """创建静态物体并登记到因子 Actor 列表中。"""
        name = f'STATIC_{self._static_index:03d}'
        self._static_index += 1

        static_object: CarlaActor = self._context.actors.create_actor(
            bp=bp,
            tf=transform,
            name=name,
        )
        self._factor_actors[name] = static_object

    def _apply_ego_vehicle_carla_autopilot(self) -> None:
        """为 ego 车辆开启 Carla 自动驾驶。"""
        if self.vehicle_ego is None or not self.vehicle_ego.is_alive:
            return
        self.vehicle_ego.set_carla_autopilot(enable=True)
        self._context.traffic.auto_lane_change(self.vehicle_ego.actor, False)

    def _disable_ego_autopilot(self) -> None:
        """在因子销毁时关闭 ego 自动驾驶。"""
        if self.vehicle_ego is None or not self.vehicle_ego.is_alive:
            return
        self.vehicle_ego.set_carla_autopilot(enable=False)

    def _update_trigger_by_time(self) -> None:
        """基于时间的触发逻辑, 参考原始实现。"""
        if self.stage != self.FactorStage.WAIT_FOR_TRIGGER:
            return

        if self._count_before_trigger >= self._wait_trigger_seconds * self._context.fps:
            self.stage = self.FactorStage.TRIGGERED
            self.logger.warning(f'Factor {self.NAME} triggered')

        self._count_before_trigger += 1