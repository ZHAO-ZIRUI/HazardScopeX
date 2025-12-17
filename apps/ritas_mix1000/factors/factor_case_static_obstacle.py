import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseStaticObstacle(Factor):
    NAME = 'F_CaseStaticObstacle'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town10HD_Opt': {
            'ego': 93,
            'obs': 107,
            'npc': [101, 55, 57, 119, 59]
        },
    }

    def __init__(self, context: CarlaContext, ego: CarlaVehicle, *, xy_offset: float = 1.0, obstacle_count: int = 10, ticks_per_obstacle: int = 5, distance: float = 5.0):
        super().__init__(context)
        self._ego = ego
        self._xy_offset = xy_offset
        self._obstacle_count = obstacle_count
        self._ticks_per_obstacle = ticks_per_obstacle
        self._distance = distance
        self._obstacles: list[CarlaActor] = []
        self._vehicles: list[CarlaVehicle] = []
        self._obs_spawn_location: carla.Location | None = None
        self._ego_braked = False

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

        # 使用 Traffic Manager 控制车辆，npc车辆正常使用carla ap
        tm = self._context.traffic_manager
        
        # 获取obs位置，用于生成静态障碍物
        tf_obs = self._context.spawn_points[spawn_point_mapping['obs']]
        obs_location = tf_obs.location
        obs_yaw = tf_obs.rotation.yaw
        self._obs_spawn_location = obs_location  # 保存obs spawn_point位置用于距离检测
        
        # 在obs位置附近生成静态障碍物，每生成1个tick 5次
        for i in range(self._obstacle_count):
            # 在obs位置附近随机生成位置（在xy_offset范围内随机分布）
            angle = np.random.uniform(0, 2 * np.pi)
            distance = np.random.uniform(0, self._xy_offset)  # 在0到xy_offset之间随机距离
            offset_x = distance * np.cos(angle)
            offset_y = distance * np.sin(angle)
            
            obstacle_location = carla.Location(
                x=obs_location.x + offset_x,
                y=obs_location.y + offset_y,
                z=4.0  # 高度z=4
            )
            
            obstacle_tf = carla.Transform(
                location=obstacle_location,
                rotation=carla.Rotation(yaw=obs_yaw)
            )
            
            obstacle = self._context.actors.create_actor(
                bp=CarlaBlueprints.STATIC_PROP_BOX01,
                tf=obstacle_tf,
                name=f'OBS_BOX_{i:03d}',
            )
            obstacle.spawn(self._context.world, ignore_spawn_failure=True)
            
            # 启用物理模拟，让障碍物响应重力和物理
            if obstacle.actor is not None and obstacle.actor.is_alive:
                obstacle.actor.set_simulate_physics(True)
            
            self._obstacles.append(obstacle)
            self.logger.info(f'Spawned obstacle {i+1}/{self._obstacle_count} at ({obstacle_location.x:.2f}, {obstacle_location.y:.2f}, {obstacle_location.z:.2f}) with physics enabled')
            
            # 每生成1个tick指定次数
            for _ in range(self._ticks_per_obstacle):
                self._context.tick()
        
        self._context.tick()
        self._context.actors.wait_stable()

        # 启动AP
        self._ego.set_carla_autopilot(enable=True)
        for vehicle in self._vehicles:
            tm.auto_lane_change(vehicle.actor, False)
            vehicle.set_carla_autopilot(enable=True)
        
        return super().setup()

    def tick(self) -> None:
        # 如果已经刹停，持续应用刹车控制
        if self._ego_braked:
            if self._ego.actor is not None and self._ego.actor.is_alive:
                control = carla.VehicleControl(throttle=0.0, brake=1.0, steer=0.0)
                self._ego.actor.apply_control(control)
            return super().tick()
        
        # 检测ego和obs spawn_point的距离
        if (self._ego.actor is not None and self._ego.actor.is_alive and 
            self._obs_spawn_location is not None):
            
            ego_location = self._ego.actor.get_location()
            distance = ego_location.distance(self._obs_spawn_location)
            
            # 如果距离小于阈值，刹停ego
            if distance < self._distance:
                self._ego_braked = True
                self._ego.set_carla_autopilot(enable=False)
                self.logger.info(f'EGO braked at distance {distance:.2f}m (threshold: {self._distance}m)')
        
        return super().tick()

    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        
        return super().teardown()