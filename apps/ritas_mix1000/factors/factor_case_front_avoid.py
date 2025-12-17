import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseFrontAvoid(Factor):
    NAME = 'F_CaseFrontAvoid'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town10HD_Opt': {
            'ego': 93,
            'act': 53,
            'obs': 107,
            'npc': [101, 58]
        },
    }

    def __init__(self, context: CarlaContext, ego: CarlaVehicle, *, distance_offset: float = 15.0, avoid_distance: float = 10.0):
        super().__init__(context)
        self._ego = ego
        self._act: CarlaVehicle | None = None
        self._obs: CarlaActor | None = None
        self._distance_offset = distance_offset
        self._avoid_distance = avoid_distance
        self._act_avoiding = False
        self._act_avoided = False  # 标记是否已经完成避让（确保只发生一次）
        self._act_manual_control = False  # 是否处于手动控制状态（避让前保持速度）
        self._target_velocity = None  # 目标速度向量
        self._avoid_start_ticks = -1
        self._avoid_duration_ticks = int(0.75 * self._context.fps)  # 0.75秒
        self._current_ticks = 0
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

        # 创建障碍物
        tf_obs = self._context.spawn_points[spawn_point_mapping['obs']]
        self._obs = self._context.actors.create_actor(
            bp=CarlaBlueprints.WALKER_PEDESTRIAN_0001,
            tf=tf_obs,
            name='OBS',
        )
        self._obs.spawn(self._context.world, ignore_spawn_failure=True)

        # 等待稳定
        self._context.tick()
        self._context.actors.wait_stable()

        # 使用 Traffic Manager 控制车辆直行
        tm = self._context.traffic_manager
        for vehicle in self._vehicles:
            tm.auto_lane_change(vehicle.actor, False)
            vehicle.set_carla_autopilot(enable=True)
        
        # 让 act 忽略碰撞，不要在碰撞前减速
        if self._act is not None and self._act.actor is not None:
            tm.ignore_vehicles_percentage(self._act.actor, 100.0)  # 100% 忽略其他车辆和障碍物
        
        return super().setup()

    def tick(self) -> None:
        self._current_ticks += 1
        
        # 如果已经完成避让，不再检测和处理
        if self._act_avoided:
            return super().tick()
        
        # 检测 act 和 obs 之间的距离
        if (self._act is not None and self._act.actor is not None and self._act.actor.is_alive and
            self._obs is not None and self._obs.actor is not None and self._obs.actor.is_alive):
            
            act_location = self._act.actor.get_location()
            obs_location = self._obs.actor.get_location()
            distance = act_location.distance(obs_location)
            
            # 如果距离接近 avoid_distance，提前禁用 autopilot 并使用 set_target_velocity 保持速度
            if not self._act_manual_control and distance <= self._avoid_distance + 10.0:  # 提前10米开始手动控制
                self._act_manual_control = True
                self._act.set_carla_autopilot(enable=False)
                # 获取当前速度向量作为目标速度
                current_velocity = self._act.actor.get_velocity()
                self._target_velocity = carla.Vector3D(current_velocity.x, current_velocity.y, current_velocity.z)
                speed_kmh = 3.6 * (current_velocity.x**2 + current_velocity.y**2 + current_velocity.z**2)**0.5
                self.logger.info(f'ACT manual control enabled at distance {distance:.2f}m to maintain speed {speed_kmh:.1f} km/h')
            
            # 如果距离小于等于 avoid_distance，开始紧急避让（只发生一次）
            if not self._act_avoiding and distance <= self._avoid_distance:
                self._act_avoiding = True
                self._avoid_start_ticks = self._current_ticks
                self.logger.info(f'ACT avoiding right at distance {distance:.2f}m (threshold: {self._avoid_distance}m)')
        
        # 如果处于手动控制状态但还没开始避让，使用 set_target_velocity 保持速度
        if self._act_manual_control and not self._act_avoiding and self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            if self._target_velocity is not None:
                self._act.actor.set_target_velocity(self._target_velocity)
        
        # 如果正在避让，应用手动控制
        if self._act_avoiding and self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            elapsed_ticks = self._current_ticks - self._avoid_start_ticks
            
            # 如果还没超过指定时间，继续手动控制（向右转向）
            if elapsed_ticks < self._avoid_duration_ticks:
                control = carla.VehicleControl(throttle=0.0, brake=0.0, steer=0.3)  # 向右打0.3方向，油门刹车为0
                self._act.actor.apply_control(control)
            else:
                # 避让完成后，标记为已完成，重新启用 autopilot
                self._act_avoiding = False
                self._act_manual_control = False
                self._act_avoided = True
                self._target_velocity = None
                self._act.set_carla_autopilot(enable=True)
                self.logger.info(f'ACT autopilot re-enabled after {self._avoid_duration_ticks / self._context.fps:.1f} seconds')
        
        return super().tick()

    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        if self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            self._act.set_carla_autopilot(enable=False)
        return super().teardown()