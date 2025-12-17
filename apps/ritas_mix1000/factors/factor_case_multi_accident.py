import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseMultiAccident(Factor):
    NAME = 'F_CaseMultiAccident'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town10HD_Opt': {
            'ego': 93,
            'obs': 107,
            'npc': [101, 55, 57, 119, 59]
        },
    }

    def __init__(self, context: CarlaContext, ego: CarlaVehicle, *, obs_yaw_offset: float = 35.0, obs_xy_offset: tuple[float, float] = (0.0, 0.0), jeep_offset_behind_obs: float = 4.0, pedestrians_offset_behind_jeep: float = 2.0, ego_brake_distance_threshold: float = 20.0):
        super().__init__(context)
        self._ego = ego
        self._obs_yaw_offset = obs_yaw_offset
        self._obs_xy_offset = obs_xy_offset
        self._jeep_offset_behind_obs = jeep_offset_behind_obs
        self._pedestrians_offset_behind_jeep = pedestrians_offset_behind_jeep
        self._ego_brake_distance_threshold = ego_brake_distance_threshold
        self._obstacles: list[CarlaActor] = []
        self._vehicles: list[CarlaVehicle] = []
        self._walkers: list[CarlaActor] = []
        self._obs: CarlaVehicle | None = None
        self._jeep: CarlaVehicle | None = None
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
        
        # 在obs后方生成侧翻的jeep（基于原始spawn point计算，避免obs的yaw偏移影响）
        obs_spawn_yaw_rad = np.radians(tf_obs_spawn.rotation.yaw)
        jeep_location = carla.Location(
            x=tf_obs_spawn.location.x - self._jeep_offset_behind_obs * np.cos(obs_spawn_yaw_rad),
            y=tf_obs_spawn.location.y - self._jeep_offset_behind_obs * np.sin(obs_spawn_yaw_rad),
            z=2  # 降低初始高度
        )
        
        # 侧翻：设置roll角度为180度（侧翻）
        jeep_transform = carla.Transform(
            location=jeep_location,
            rotation=carla.Rotation(yaw=tf_obs_spawn.rotation.yaw, pitch=0.0, roll=90.0)
        )
        
        self._jeep = self._context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_JEEP_WRANGLER_RUBICON,
            tf=jeep_transform,
            name='JEEP_FLIPPED',
        )
        self._jeep.spawn(self._context.world, ignore_spawn_failure=True)
        self._vehicles.append(self._jeep)
        self.logger.info(f'Flipped jeep spawned at ({jeep_location.x:.2f}, {jeep_location.y:.2f}, {jeep_location.z:.2f})')
        
        # 在jeep后方生成四个行人（基于原始spawn point计算，避免obs的yaw偏移影响）
        pedestrian_blueprints = [
            CarlaBlueprints.WALKER_PEDESTRIAN_0001,
            CarlaBlueprints.WALKER_PEDESTRIAN_0002,
            CarlaBlueprints.WALKER_PEDESTRIAN_0003,
            CarlaBlueprints.WALKER_PEDESTRIAN_0004,
        ]
        
        for i, ped_bp in enumerate(pedestrian_blueprints):
            # 在jeep后方横向分布行人
            lateral_offset = (i - 1.5) * 1.5  # 横向偏移，使行人分布在jeep后方
            ped_location = carla.Location(
                x=jeep_location.x - self._pedestrians_offset_behind_jeep * np.cos(obs_spawn_yaw_rad) + lateral_offset * np.sin(obs_spawn_yaw_rad),
                y=jeep_location.y - self._pedestrians_offset_behind_jeep * np.sin(obs_spawn_yaw_rad) - lateral_offset * np.cos(obs_spawn_yaw_rad),
                z=jeep_location.z
            )
            
            ped_transform = carla.Transform(
                location=ped_location,
                rotation=carla.Rotation(yaw=tf_obs_spawn.rotation.yaw)
            )
            
            pedestrian = self._context.actors.create_actor(
                bp=ped_bp,
                tf=ped_transform,
                name=f'PEDESTRIAN_{i+1}',
            )
            pedestrian.spawn(self._context.world, ignore_spawn_failure=True)
            self._walkers.append(pedestrian)
            self.logger.info(f'Pedestrian {i+1} spawned at ({ped_location.x:.2f}, {ped_location.y:.2f}, {ped_location.z:.2f})')
        
        self._context.tick()
        
        # 收集所有成功spawn的actors，只等待这些actors稳定
        spawned_actors = []
        for vehicle in self._vehicles:
            if vehicle.actor is not None and vehicle.actor.is_alive:
                spawned_actors.append(vehicle)
        for walker in self._walkers:
            if walker.actor is not None and walker.actor.is_alive:
                spawned_actors.append(walker)
        for obstacle in self._obstacles:
            if obstacle.actor is not None and obstacle.actor.is_alive:
                spawned_actors.append(obstacle)
        
        if spawned_actors:
            self._context.actors.wait_stable(*spawned_actors)

        # 启动AP（obs和jeep不启动，保持静止）
        self._ego.set_carla_autopilot(enable=True)
        for vehicle in self._vehicles:
            if vehicle != self._obs and vehicle != self._jeep:  # obs和jeep不启动autopilot
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