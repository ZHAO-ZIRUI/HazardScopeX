import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorLotCaseFrontAeb(Factor):
    NAME = 'F_LotCaseFrontAeb'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/SUSTech_COE_ParkingLot': {
            'ego': 3,
            'act': 37,
            'npc': [11, 14, 27, 42, 43]
        },
    }

    def __init__(self, context: CarlaContext, ego: CarlaVehicle, *, distance_offset: float = 15.0, brake_delay_seconds: float = 2.5):
        super().__init__(context)
        self._ego = ego
        self._act: CarlaVehicle | None = None
        self._distance_offset = distance_offset
        self._brake_delay_ticks = int(brake_delay_seconds * self._context.fps)
        self._current_ticks = 0
        self._act_braked = False
        self._vehicles: list[CarlaVehicle] = []
        self.world = context.world
        self.debug = context.world.debug

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego

    @property
    def act(self) -> CarlaVehicle:
        return self._act

    def bringup(self) -> None:
        spawn_point_mapping = self.MAP_SPAWN_POINT_MAPPING[self._context.map.name]
        # 设置 ego 位置
        tf_ego = self._context.spawn_points[spawn_point_mapping['ego']]
        ego_yaw_rad = np.radians(tf_ego.rotation.yaw)
        tf_ego.location.x -= 0.25 * self._distance_offset * np.cos(ego_yaw_rad)
        tf_ego.location.y -= 0.25 * self._distance_offset * np.sin(ego_yaw_rad)
        self._ego.actor.set_transform(tf_ego)
        self._vehicles.append(self._ego)

        spectator = self.world.get_spectator()
        spectator.set_transform(tf_ego)

        # 计算 act 位置
        tf_act = self._context.spawn_points[spawn_point_mapping['act']]
        tf_act.location.x -= 1.5 * self._distance_offset * np.cos(ego_yaw_rad)
        tf_act.location.y -= 1.5 * self._distance_offset * np.sin(ego_yaw_rad)
        self._act = self._context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_TESLA_MODEL3,
            tf=tf_act,
            name='ACT',
        )
        self._act.spawn()
        self._vehicles.append(self._act)

        # 创建 npc
        for npc_sp_idx in spawn_point_mapping['npc']:
            npc_tf = self._context.spawn_points[npc_sp_idx]
            npc = self._context.actors.create_vehicle(
                bp=CarlaBlueprints.VEHICLE_AUDI_A2,
                tf=npc_tf,
                name=f'NPC_{npc_sp_idx}',
                ignore_spawn_failure=True
            )
            npc.spawn()
            self._vehicles.append(npc)

        self._context.tick()

        # 收集所有成功spawn的actors
        spawned_actors = []
        for vehicle in self._vehicles:
            if vehicle.actor is not None and vehicle.actor.is_alive:
                spawned_actors.append(vehicle)
        if spawned_actors:
            self._context.actors.wait_stable(*spawned_actors)

        # 使用 Traffic Manager 控制车辆直行
        tm = self._context.traffic
        for vehicle in spawned_actors:
            tm.auto_lane_change(vehicle.actor, False)
            vehicle.set_carla_autopilot(enable=True)
        
        self._context.hook_on_tick.append(self.tick)

        return super().bringup()

    # TODO: Refactor according to the new code framework
    def tick(self, snapshot) -> None:
        self._current_ticks += 1
        
        # 在指定时间后让 act 强行刹停
        if not self._act_braked and self._current_ticks >= self._brake_delay_ticks:
            if self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
                self._act_braked = True
                self._act.set_carla_autopilot(enable=False)
                self.logger.info(f'ACT braked after {self._brake_delay_ticks / self._context.fps:.1f} seconds')
        
        # 如果已经刹停，持续应用刹车控制
        if self._act_braked and self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            control = carla.VehicleControl(throttle=0.0, brake=1.0, steer=0.0)
            self._act.actor.apply_control(control)
        
        return super().update()

    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        if self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            self._act.set_carla_autopilot(enable=False)
            self._act.destroy()
        return super().teardown()