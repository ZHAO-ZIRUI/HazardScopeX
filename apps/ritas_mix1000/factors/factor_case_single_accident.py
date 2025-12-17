import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseSingleAccident(Factor):
    NAME = 'F_CaseSingleAccident'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town10HD_Opt': {
            'ego': 93,
            'obs': 107,
            'npc': [101, 55, 57, 119, 59]
        },
    }

    def __init__(self, context: CarlaContext, ego: CarlaVehicle, *, obs_yaw_offset: float = 35.0, obs_xy_offset: tuple[float, float] = (0.0, 0.0), warning_sign_offset_behind: float = 10.0, ego_brake_distance_threshold: float = 15.0):
        super().__init__(context)
        self._ego = ego
        self._obs_yaw_offset = obs_yaw_offset
        self._obs_xy_offset = obs_xy_offset
        self._warning_sign_offset_behind = warning_sign_offset_behind
        self._ego_brake_distance_threshold = ego_brake_distance_threshold
        self._obstacles: list[CarlaActor] = []
        self._vehicles: list[CarlaVehicle] = []
        self._obs: CarlaVehicle | None = None
        self._warning_sign: CarlaActor | None = None
        self._obstacle_spawn_point_location: carla.Location | None = None
        self._is_ego_braked = False

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego


    def setup(self) -> None:
        spawn_point_mapping = self.MAP_SPAWN_POINT_MAPPING[self._context.map_name]
        # 设置 ego 位置
        tf_ego = self._context.spawn_points[spawn_point_mapping['ego']]
        self._ego.actor.set_transform(tf_ego)
        self._vehicles.append(self._ego)

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
        
        # 获取obs spawn_point位置
        tf_obs_spawn = self._context.spawn_points[spawn_point_mapping['obs']]
        self._obstacle_spawn_point_location = tf_obs_spawn.location
        
        # 计算obs车辆的位置和朝向（应用yaw偏移和xy偏移）
        obs_location = carla.Location(
            x=tf_obs_spawn.location.x + self._obs_xy_offset[0],
            y=tf_obs_spawn.location.y + self._obs_xy_offset[1],
            z=tf_obs_spawn.location.z
        )
        obs_yaw = tf_obs_spawn.rotation.yaw + self._obs_yaw_offset
        
        obs_transform = carla.Transform(
            location=obs_location,
            rotation=carla.Rotation(yaw=obs_yaw)
        )
        
        # 在obs位置生成车辆
        self._obs = self._context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_MERCEDES_COUPE,
            tf=obs_transform,
            name='OBS',
        )
        self._obs.spawn(self._context.world)
        self._vehicles.append(self._obs)
        
        # 开启obs的双闪灯（使用RightBlinker + LeftBlinker）
        if self._obs.actor is not None and self._obs.actor.is_alive:
            combined_light_state = carla.VehicleLightState.RightBlinker | carla.VehicleLightState.LeftBlinker
            self._obs.actor.set_light_state(carla.VehicleLightState(combined_light_state))
            self.logger.info('OBS hazard lights enabled (RightBlinker + LeftBlinker)')
        
        # 计算warning sign的位置（在原始obs spawn point后方）
        obs_spawn_yaw_rad = np.radians(tf_obs_spawn.rotation.yaw)
        warning_sign_location = carla.Location(
            x=tf_obs_spawn.location.x - self._warning_sign_offset_behind * np.cos(obs_spawn_yaw_rad),
            y=tf_obs_spawn.location.y - self._warning_sign_offset_behind * np.sin(obs_spawn_yaw_rad),
            z=tf_obs_spawn.location.z
        )
        
        # 计算warning sign朝向ego的yaw角
        ego_location = self._ego.actor.get_location()
        direction_to_ego = carla.Location(
            x=ego_location.x - warning_sign_location.x,
            y=ego_location.y - warning_sign_location.y,
            z=0.0
        )
        warning_sign_yaw = np.degrees(np.arctan2(direction_to_ego.y, direction_to_ego.x)) - 90.0
        
        warning_sign_transform = carla.Transform(
            location=warning_sign_location,
            rotation=carla.Rotation(yaw=warning_sign_yaw)
        )
        
        # 生成warning sign
        self._warning_sign = self._context.actors.create_actor(
            bp=CarlaBlueprints.STATIC_PROP_WARNINGACCIDENT,
            tf=warning_sign_transform,
            name='WARNING_SIGN',
        )
        self._warning_sign.spawn(self._context.world, ignore_spawn_failure=True)
        
        # 启用物理模拟，让warning sign响应重力和物理
        if self._warning_sign.actor is not None and self._warning_sign.actor.is_alive:
            self._warning_sign.actor.set_simulate_physics(True)
        
        self._obstacles.append(self._warning_sign)
        self.logger.info(f'Warning sign spawned at ({warning_sign_location.x:.2f}, {warning_sign_location.y:.2f}, {warning_sign_location.z:.2f}) facing ego with physics enabled')
        
        self._context.tick()
        self._context.actors.wait_stable()

        # 启动AP（obs不启动，保持静止）
        self._ego.set_carla_autopilot(enable=True)
        for vehicle in self._vehicles:
            if vehicle != self._obs:  # obs不启动autopilot
                tm.auto_lane_change(vehicle.actor, False)
                vehicle.set_carla_autopilot(enable=True)
        
        return super().setup()

    def tick(self) -> None:
        # 如果已经刹停，持续应用刹车控制
        if self._is_ego_braked:
            if self._ego.actor is not None and self._ego.actor.is_alive:
                control = carla.VehicleControl(throttle=0.0, brake=1.0, steer=0.0)
                self._ego.actor.apply_control(control)
            return super().tick()
        
        # 检测ego和障碍物生成点的距离
        if (self._ego.actor is not None and self._ego.actor.is_alive and 
            self._obstacle_spawn_point_location is not None):
            
            ego_location = self._ego.actor.get_location()
            ego_to_obs_distance = ego_location.distance(self._obstacle_spawn_point_location)
            
            # 如果距离小于阈值，刹停ego
            if ego_to_obs_distance < self._ego_brake_distance_threshold:
                self._is_ego_braked = True
                self._ego.set_carla_autopilot(enable=False)
                self._ego.actor.apply_control(carla.VehicleControl(throttle=0.0, brake=0.8, steer=0.0))
                self.logger.info(f'EGO braked at distance {ego_to_obs_distance:.2f}m (threshold: {self._ego_brake_distance_threshold}m)')
        
        return super().tick()

    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        
        return super().teardown()