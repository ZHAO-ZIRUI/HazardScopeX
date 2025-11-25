import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseHighwayMissExit(Factor):
    NAME = 'F_CaseHighwayMissExit'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town04': {
            'ego': 110,
            'act': 289,
            'npc': [108, 113, 114, 117]
        },
    }

    def __init__(
        self, context: CarlaContext, ego: CarlaVehicle, *,
        distance_offset: float = 15.0,
        brake_delay_seconds: float = 15.0,
        release_delay_seconds: float = 1.0,
        target_speed_kmh: float = 100.0,
    ):
        super().__init__(context)
        self._ego = ego
        self._act: CarlaVehicle | None = None
        self._distance_offset = distance_offset
        self._brake_delay_ticks = int(brake_delay_seconds * self._context.fps)
        self._release_delay_ticks = int(release_delay_seconds * self._context.fps)
        self._current_ticks = 0
        self._act_manual_control_started = False
        self._act_released = False
        self._vehicles: list[CarlaVehicle] = []

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego

    @property
    def act(self) -> CarlaVehicle:
        return self._act

    def setup(self) -> None:
        spawn_point_mapping = self.MAP_SPAWN_POINT_MAPPING[self._context.map_name]
        # 设置 ego 位置
        tf_ego = self._context.spawn_points[spawn_point_mapping['ego']]
        self._ego.actor.set_transform(tf_ego)
        self._vehicles.append(self._ego)

        # 计算 act 位置
        tf_act = self._context.spawn_points[spawn_point_mapping['act']]
        ego_yaw_rad = np.radians(tf_ego.rotation.yaw)
        tf_act.location.x -= self._distance_offset * np.cos(ego_yaw_rad)
        tf_act.location.y -= self._distance_offset * np.sin(ego_yaw_rad)
        self._act = self._context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_TESLA_MODEL3,
            tf=tf_act,
            name='ACT',
        )
        self._act.spawn(self._context.world)
        self._vehicles.append(self._act)

        # 创建 npc
        for npc_sp_idx in spawn_point_mapping['npc']:
            npc_tf = self._context.spawn_points[npc_sp_idx]
            npc = self._context.actors.create_vehicle(
                bp=CarlaBlueprints.VEHICLE_MERCEDES_SPRINTER,
                tf=npc_tf,
                name=f'NPC_{npc_sp_idx}',
            )
            npc.spawn(self._context.world, ignore_spawn_failure=True)
            self._vehicles.append(npc)

        self._context.tick()
        self._context.actors.wait_stable()

        # 使用 Traffic Manager 控制车辆直行
        tm = self._context.traffic_manager
        # tm.set_route(self._ego.actor, ['Straight'] * 9999)
        target_speed_kmh = 90.0
        target_speed_ms = target_speed_kmh / 3.6
        for vehicle in self._vehicles:
            tm.auto_lane_change(vehicle.actor, False)
            vehicle.set_carla_autopilot(enable=True)
            tm.set_desired_speed(vehicle.actor, target_speed_ms)
        
        self.logger.info(f'All vehicles target speed set to {target_speed_kmh:.1f} km/h')
        return super().setup()

    def tick(self) -> None:
        self._current_ticks += 1
        
        self._context.traffic_manager.set_route(self._ego.actor, ['Straight'] * 9999)

        if self._act is None or self._act.actor is None or not self._act.actor.is_alive:
            return super().tick()
        
        # 阶段1：5s后，act退出AP，手动控制（向右打0.2方向，刹车0.01）
        if not self._act_manual_control_started and self._current_ticks >= self._brake_delay_ticks:
            self._act_manual_control_started = True
            self._act.set_carla_autopilot(enable=False)
            self.logger.info(f'ACT manual control started after {self._brake_delay_ticks / self._context.fps:.1f} seconds')
        
        # 阶段2：再过1s后，所有控制归零
        if self._act_manual_control_started and not self._act_released:
            if self._current_ticks >= self._brake_delay_ticks + self._release_delay_ticks:
                self._act_released = True
                self.logger.info(f'ACT control released after {self._release_delay_ticks / self._context.fps:.1f} seconds')
        
        # 应用控制
        if self._act_manual_control_started:
            if not self._act_released:
                # 阶段1：向右打0.2方向，刹车0.01
                control = carla.VehicleControl(throttle=0.3, brake=0.0, steer=0.2)
            else:
                # 阶段2：所有控制归零
                control = carla.VehicleControl(throttle=0.0, brake=0.0, steer=0.0)
            self._act.actor.apply_control(control)
        
        return super().tick()

    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        if self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            self._act.set_carla_autopilot(enable=False)
            self._act.destroy()
        return super().teardown()