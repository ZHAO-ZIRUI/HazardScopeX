import numpy as np
import carla
import math
from shared.scenarios import Factor
from shared.simulator import *


class FactorLotCaseRearEnd(Factor):
    NAME = 'F_LotCaseRearEnd'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/SUSTech_COE_ParkingLot': {
            'ego': 44,
            'act': 44,
            'npc': [3, 4, 8, 9, 10, 13]
        },
    }

    def __init__(self, context: CarlaContext, ego: CarlaVehicle, *, distance_offset: float = 10.0, act_speed_kmh: float = 70.0, ego_speed_kmh: float = 30.0, brake_threshold: float = 6, brake_strength: float = 0.25):
        super().__init__(context)
        self._ego = ego
        self._act: CarlaVehicle | None = None
        self._distance_offset = distance_offset
        self._act_speed_kmh = act_speed_kmh
        self._ego_speed_kmh = ego_speed_kmh
        self._current_ticks = 0
        self._brake_threshold = brake_threshold  # 刹车保持距离阈值，单位米
        self._brake_strength = brake_strength
        self._brake_flag = False
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
        # self.debug.draw_point(tf_ego.location,size=0.1,color=carla.Color(255,0,0),life_time=1000)
        self._ego.actor.set_transform(tf_ego)
        self._vehicles.append(self._ego)

        # 计算 act 位置
        ego_yaw_rad = np.radians(tf_ego.rotation.yaw)
        tf_act = carla.Transform(
            carla.Location(
                x=tf_ego.location.x - self._distance_offset * np.cos(ego_yaw_rad),
                y=tf_ego.location.y - self._distance_offset * np.sin(ego_yaw_rad),
                z=tf_ego.location.z
            ), 
            tf_ego.rotation
        )
        # self.debug.draw_point(tf_act.location,size=0.1,color=carla.Color(0,255,0),life_time=1000)

        spectator = self.world.get_spectator()
        tf_spec = carla.Transform(carla.Location(x=tf_ego.location.x,y=tf_ego.location.y,z=tf_ego.location.z+1.5), tf_ego.rotation)
        spectator.set_transform(tf_spec)

        self._act = self._context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_MERCEDES_SPRINTER,
            tf=tf_act,
            name='ACT',
        )
        self._act.spawn()
        self._vehicles.append(self._act)

        # 创建 npc
        for npc_sp_idx in spawn_point_mapping['npc']:
            npc_tf = self._context.spawn_points[npc_sp_idx]
            npc = self._context.actors.create_vehicle(
                bp=CarlaBlueprints.VEHICLE_MERCEDES_SPRINTER,
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
        self._ego.set_carla_autopilot(enable=True)
        for vehicle in spawned_actors:
            if vehicle != self._act:
                tm.auto_lane_change(vehicle.actor, False)
                vehicle.set_carla_autopilot(enable=True)
        
        # 设置 act 的速度高于 ego
        if self._act is not None and self._act.actor is not None:
            act_speed_ms = self._act_speed_kmh / 3.6
            tm.set_desired_speed(self._act.actor, act_speed_ms)
            control = carla.VehicleControl(throttle=0.75, brake=0.0, steer=0.0)
            self._act.actor.apply_control(control)
            self.logger.info(f'ACT target speed set to {self._act_speed_kmh:.1f} km/h')
        
        if self._ego.actor is not None:
            ego_speed_ms = self._ego_speed_kmh / 3.6
            tm.set_desired_speed(self._ego.actor, ego_speed_ms)
            # 让ego对碰撞的响应更不灵敏
            tm.ignore_vehicles_percentage(self._ego.actor, 80.0)  # 80% 忽略其他车辆，降低碰撞响应灵敏度
            self.logger.info(f'EGO target speed set to {self._ego_speed_kmh:.1f} km/h, collision response reduced')
        
        self._context.hook_on_tick.append(self.tick)

        return super().bringup()
    # TODO: Refactor according to the new code framework

    def tick(self, snapshot) -> None:
        self._current_ticks += 1
        
        # 检测 act 和 ego 在朝向方向上的距离
        if (self._act is not None and self._act.actor is not None and self._act.actor.is_alive and
            self._ego.actor is not None and self._ego.actor.is_alive) and self._brake_flag == False:
            
            act_location = self._act.actor.get_location()
            ego_location = self._ego.actor.get_location()
            ego_transform = self._ego.actor.get_transform()
            
            # 计算从 ego 到 act 的向量
            dx = act_location.x - ego_location.x
            dy = act_location.y - ego_location.y
            
            # 计算 ego 的朝向向量（单位向量）
            ego_yaw_rad = np.radians(ego_transform.rotation.yaw)
            forward_x = np.cos(ego_yaw_rad)
            forward_y = np.sin(ego_yaw_rad)
            
            # 计算投影距离（在朝向方向上的距离）
            projection_distance = dx * forward_x + dy * forward_y
            
            if math.fabs(projection_distance) < self._brake_threshold:
                # 让 act 刹车，保持距离
                control = carla.VehicleControl(throttle=0.0, brake=self._brake_strength, steer=0.0)
                self._act.actor.apply_control(control)
                self._brake_flag = True
                self.logger.debug(f'ACT braking to maintain distance, projection_distance={projection_distance:.2f} m')
        
        return super().update()

    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        if self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            self._act.set_carla_autopilot(enable=False)
            self._act.destroy()
        return super().teardown()