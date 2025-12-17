import numpy as np
import carla
import math
from shared.scenarios import Factor
from shared.simulator import *


class FactorLotCaseForceCutin(Factor):
    NAME = 'F_LotCaseForceCutin'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/SUSTech_COE_ParkingLot': {
            'ego': 44,
            'act': 44,
            'npc': [3, 4, 8, 31, 42, 47]
        },
    }

    def __init__(self, context: CarlaContext, ego: CarlaVehicle, *, distance_offset: float = 10.0, left_offset: float = 2.3, cutin_distance_threshold: float = 0.65, act_speed_kmh: float = 70.0, ego_speed_kmh: float = 30.0):
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
        self._act_cutin_stage = 0
        self._cutin_start_ticks = -1
        self._vehicles: list[CarlaVehicle] = []
        self._init_vertical_distance = 0.0
        self.world = context.world
        self.debug = context.world.debug

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego

    @property
    def act(self) -> CarlaVehicle:
        return self._act
    
    def get_vertical_distance(self, ego_transform: carla.Transform, act_location: carla.Location) -> float:
        # 计算从 ego 到 act 的向量
        ego_location = ego_transform.location
        dx = act_location.x - ego_location.x
        dy = act_location.y - ego_location.y
        
        # 计算 ego 的朝向向量（单位向量）
        ego_yaw_rad = np.radians(ego_transform.rotation.yaw)
        forward_x = np.cos(ego_yaw_rad)
        forward_y = np.sin(ego_yaw_rad)
        
        # 计算投影距离（在朝向方向上的距离）
        vertical_distance = dx * forward_y + dy * forward_x

        return vertical_distance

    def setup(self) -> None:
        spawn_point_mapping = self.MAP_SPAWN_POINT_MAPPING[self._context.map_name]
        # 设置 ego 位置
        tf_ego = self._context.spawn_points[spawn_point_mapping['ego']]
        self._ego.actor.set_transform(tf_ego)
        self._vehicles.append(self._ego)

        # 计算 act 位置
        ego_yaw_rad = np.radians(tf_ego.rotation.yaw)

        tf_act = carla.Transform(
            carla.Location(
                x=tf_ego.location.x + self._left_offset * np.sin(ego_yaw_rad) - self._distance_offset * np.cos(ego_yaw_rad),
                y=tf_ego.location.y + self._left_offset * np.cos(ego_yaw_rad) - self._distance_offset * np.sin(ego_yaw_rad),
                z=tf_ego.location.z
            ), 
            tf_ego.rotation
        )
        self._act = self._context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_TESLA_MODEL3,
            tf=tf_act,
            name='ACT',
        )
        self._act.spawn(self._context.world)
        self._vehicles.append(self._act)

        self._init_vertical_distance = self.get_vertical_distance(tf_ego, tf_act.location)

        spectator = self.world.get_spectator()
        tf_spec = carla.Transform(carla.Location(x=tf_ego.location.x,y=tf_ego.location.y,z=tf_ego.location.z+1.5), tf_ego.rotation)
        spectator.set_transform(tf_spec)

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
        # 收集所有成功spawn的actors
        spawned_actors = []
        for vehicle in self._vehicles:
            if vehicle.actor is not None and vehicle.actor.is_alive:
                spawned_actors.append(vehicle)
        if spawned_actors:
            self._context.actors.wait_stable(*spawned_actors)

        # 使用 Traffic Manager 控制车辆
        tm = self._context.traffic_manager
        tm.set_route(self._ego.actor,["Straight"])
        self._ego.set_carla_autopilot(enable=True)
        control = carla.VehicleControl(throttle=0.5, brake=0.0, steer=0.0)
        self._act.actor.apply_control(control)
        for vehicle in spawned_actors:
            if vehicle != self._act:
                tm.auto_lane_change(vehicle.actor, False)
                vehicle.set_carla_autopilot(enable=True)
        
        # 设置 act 的速度高于 ego
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
        
        return super().setup()

    def tick(self) -> None:
        self._current_ticks += 1
        
        # 如果已经完成变道，不再检测和处理
        if self._act_cutin_stage == 3:
            return super().tick()
        
        v = self._act.actor.get_velocity()
        if math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z) >= self._act_speed_kmh / 3.6:
            control = carla.VehicleControl(throttle=0.0, brake=0.0, steer=0.0)
            self._act.actor.apply_control(control)
            self.logger.info(f'Act vehicle stops accelerating.')        

        # 检测 act 和 ego 在朝向方向上的距离
        if (self._act is not None and self._act.actor is not None and self._act.actor.is_alive and
            self._ego.actor is not None and self._ego.actor.is_alive):
            
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

            # 如果距离大于阈值，开始向右变道（只发生一次）
            if not self._act_cutin and projection_distance > self._cutin_distance_threshold:
                self.logger.info("Starting cutin ...")
                self._act_cutin = True
                self._cutin_start_ticks = self._current_ticks
                self._act.set_carla_autopilot(enable=False)
                self.logger.info(f'ACT cutin right at projection distance {projection_distance:.2f}m (threshold: {self._cutin_distance_threshold}m)')

        # 如果正在变道，应用手动控制（向右打方向盘）
        if self._act_cutin and self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            vertical_distance = self.get_vertical_distance(ego_transform, act_location)

            if vertical_distance > 0.6 * self._init_vertical_distance and self._act_cutin_stage == 0:
                control = carla.VehicleControl(throttle=0.5, brake=0.0, steer=0.2)  # 打0.2方向
                self._act.actor.apply_control(control)
                self._act_cutin_stage = 1
            elif vertical_distance < 0.6 * self._init_vertical_distance and self._act_cutin_stage == 1:
                control = carla.VehicleControl(throttle=0.5, brake=0.0, steer=-0.2)  # 打0.2方向
                self._act.actor.apply_control(control)
                self._act_cutin_stage = 2
            elif vertical_distance < 0.25 * self._init_vertical_distance and self._act_cutin_stage == 2:
                # 变道完成后，标记为已完成，重新启用 autopilot
                self._act_cutin = False
                tm = self._context.traffic_manager
                tm.set_route(self._act.actor, ['Straight'])
                self._act.set_carla_autopilot(enable=True)
                self.logger.info(f'ACT autopilot re-enabled')
                self._act_cutin_stage = 3
        
        return super().tick()

    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        if self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            self._act.set_carla_autopilot(enable=False)
            self._act.destroy()
        return super().teardown()