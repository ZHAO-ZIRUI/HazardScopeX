import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseForceCutin(Factor):
    NAME = 'F_CaseForceCutin'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town10HD_Opt': {
            'ego': 93,
            'act': 101,
            'npc': [55, 57, 119, 59, 107, 58]
        },
    }

    def __init__(self, context: CarlaContext, ego: CarlaVehicle, *, distance_offset: float = 15.0, cutin_distance_threshold: float = 1.0, act_speed_kmh: float = 70.0, ego_speed_kmh: float = 30.0):
        super().__init__(context)
        self._ego = ego
        self._act: CarlaVehicle | None = None
        self._distance_offset = distance_offset
        self._cutin_distance_threshold = cutin_distance_threshold
        self._act_speed_kmh = act_speed_kmh
        self._ego_speed_kmh = ego_speed_kmh
        self._current_ticks = 0
        self._act_cutin = False  # 是否正在变道
        self._act_cutin_done = False  # 是否已完成变道（确保只发生一次）
        self._cutin_start_ticks = -1
        self._cutin_duration_ticks = int(1.4 * self._context.fps)  # 变道持续时间1.4秒
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
            bp=CarlaBlueprints.VEHICLE_MERCEDES_SPRINTER,
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

        # 使用 Traffic Manager 控制车辆
        tm = self._context.traffic_manager
        for vehicle in self._vehicles:
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
        if self._act_cutin_done:
            return super().tick()
        
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
                self._act_cutin = True
                self._cutin_start_ticks = self._current_ticks
                self._act.set_carla_autopilot(enable=False)
                self.logger.info(f'ACT cutin right at projection distance {projection_distance:.2f}m (threshold: {self._cutin_distance_threshold}m)')
        
        # 如果正在变道，应用手动控制（向右打方向盘）
        if self._act_cutin and self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            elapsed_ticks = self._current_ticks - self._cutin_start_ticks
            
            # 如果还没超过指定时间，继续手动控制（向右转向）
            if elapsed_ticks < self._cutin_duration_ticks:
                # 向左打方向盘（steer < 0），保持速度
                control = carla.VehicleControl(throttle=0.5, brake=0.0, steer=-0.2)  # 向左打0.5方向
                self._act.actor.apply_control(control)
            else:
                # 变道完成后，标记为已完成，重新启用 autopilot
                self._act_cutin = False
                self._act_cutin_done = True
                self._act.set_carla_autopilot(enable=True)
                self.logger.info(f'ACT autopilot re-enabled after {self._cutin_duration_ticks / self._context.fps:.1f} seconds')
        
        return super().tick()

    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        if self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            self._act.set_carla_autopilot(enable=False)
            self._act.destroy()
        return super().teardown()