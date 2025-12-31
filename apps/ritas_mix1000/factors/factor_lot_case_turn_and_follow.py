import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorLotCaseTurnandFollow(Factor):
    NAME = 'F_LotCaseTurnandFollow'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/SUSTech_COE_ParkingLot': {
            'ego': 44,
            'act': 38,
            'npc': [3, 4, 8, 9, 42, 51, 59]
        },
    }

    def __init__(self, context: CarlaContext, ego: CarlaVehicle, *, distance_offset: float = 10.0, left_offset: float = 2.3, cutin_distance_threshold: float = 1.0, act_speed_kmh: float = 30.0, ego_speed_kmh: float = 30.0):
        super().__init__(context)
        self._ego = ego
        self._act: CarlaVehicle | None = None
        self._distance_offset = distance_offset
        self._left_offset = left_offset
        self._cutin_distance_threshold = cutin_distance_threshold
        self._act_speed_kmh = act_speed_kmh
        self._ego_speed_kmh = ego_speed_kmh
        self._current_ticks = 0
        self._act_cutin = False  # 是否正在变道
        self._act_cutin_done = False  # 是否已完成变道（确保只发生一次）
        self._cutin_start_ticks = -1
        self._cutin_duration_ticks = int(1.4 * self._context.fps)  # 变道持续时间1.4秒
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
        # self.debug.draw_point(tf_ego.location,size=0.2,color=carla.Color(255,0,0),life_time=1000)
        self._ego.actor.set_transform(tf_ego)
        self._vehicles.append(self._ego)

        # 计算 act 位置
        tf_act = self._context.spawn_points[spawn_point_mapping['act']]
        # self.debug.draw_point(tf_act.location,size=0.2,color=carla.Color(0,255,0),life_time=1000)
        self._act = self._context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_TESLA_MODEL3,
            tf=tf_act,
            name='ACT',
        )
        self._act.spawn()
        self._act.actor.set_transform(tf_act)
        self._vehicles.append(self._act)

        spectator = self.world.get_spectator()
        spectator.set_transform(tf_act)

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
            if vehicle.is_alive:
                spawned_actors.append(vehicle)
        if spawned_actors:
            self._context.actors.wait_stable(*spawned_actors)

        # 使用 Traffic Manager 控制车辆
        tm = self._context.traffic
        tm.auto_lane_change(self._ego.actor, False)
        tm.set_route(self._ego.actor,["Straight","Straight","Straight"])
        self._ego.set_carla_autopilot(enable=True)
        tm.set_route(self._act.actor,["Left","Left","Left"])
        self._act.set_carla_autopilot(enable=True)
        for vehicle in spawned_actors:
            tm.auto_lane_change(vehicle.actor, False)
            vehicle.set_carla_autopilot(enable=True)
        
        if self._act is not None and self._act.actor is not None:
            act_speed_ms = self._act_speed_kmh / 3.6
            tm.set_desired_speed(self._act.actor, act_speed_ms)
            self.logger.info(f'ACT target speed set to {self._act_speed_kmh:.1f} km/h')
        
        if self._ego.actor is not None:
            ego_speed_ms = self._ego_speed_kmh / 3.6
            tm.set_desired_speed(self._ego.actor, ego_speed_ms)
            # 让ego对碰撞的响应更不灵敏
            tm.ignore_vehicles_percentage(self._ego.actor, 80.0)  # 80% 忽略其他车辆，降低碰撞响应灵敏度
            self.logger.info(f'EGO target speed set to {self._ego_speed_kmh:.1f} km/h, collision response reduced')
        
        self._context.hook_on_tick.append(self.tick)

        return super().bringup()

    def tick(self, snapshot) -> None:
        self._current_ticks += 1
        return super().update()

    # TODO: Refactor according to the new code framework
    
    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        if self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            self._act.set_carla_autopilot(enable=False)
            self._act.destroy()
        return super().teardown()