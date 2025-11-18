import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseRuntimeObstacle(Factor):
    NAME = 'F_CaseRuntimeObstacle'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town10HD_Opt': {
            'ego': 93,
            'act': 53,
            'obs': 107,
            'npc': [101, 55, 57, 119, 59]
        },
    }

    def __init__(self, context: CarlaContext, ego: CarlaVehicle, *, ego_brake_distance_threshold: float = 5.0, act_obs_trigger_distance: float = 1.0, box_spawn_offset_behind_act: float = 2.0):
        super().__init__(context)
        self._ego = ego
        self._act: CarlaVehicle | None = None
        self._ego_brake_distance_threshold = ego_brake_distance_threshold
        self._act_obs_trigger_distance = act_obs_trigger_distance
        self._box_spawn_offset_behind_act = box_spawn_offset_behind_act
        self._obstacles: list[CarlaActor] = []
        self._vehicles: list[CarlaVehicle] = []
        self._obstacle_spawn_point_location: carla.Location | None = None
        self._obstacle_spawn_point_yaw: float | None = None
        self._is_ego_braked = False
        self._is_box_spawned = False
        self._is_box_physics_enabled = False
        self._previous_act_to_obs_distance: float | None = None

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

        # 创建 act 车辆
        tf_act = self._context.spawn_points[spawn_point_mapping['act']]
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
        
        # 获取障碍物生成点位置，用于距离检测
        tf_obs = self._context.spawn_points[spawn_point_mapping['obs']]
        self._obstacle_spawn_point_location = tf_obs.location
        self._obstacle_spawn_point_yaw = tf_obs.rotation.yaw
        
        self._context.tick()
        self._context.actors.wait_stable()

        # 启动AP
        self._ego.set_carla_autopilot(enable=True)
        self._act.set_carla_autopilot(enable=True)
        for vehicle in self._vehicles:
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
        
        # 检测act和障碍物生成点的距离，生成BOX（上升沿触发）
        if (not self._is_box_spawned and 
            self._act is not None and self._act.actor is not None and self._act.actor.is_alive and
            self._obstacle_spawn_point_location is not None):
            
            act_location = self._act.actor.get_location()
            current_act_to_obs_distance = act_location.distance(self._obstacle_spawn_point_location)
            
            # 检测上升沿：上次距离 < 阈值 && 当前距离 >= 阈值（远离）
            if (self._previous_act_to_obs_distance is not None and 
                self._previous_act_to_obs_distance < self._act_obs_trigger_distance and
                current_act_to_obs_distance >= self._act_obs_trigger_distance):
                
                # 上升沿触发，在act车后方生成BOX（使用bounding box确定位置）
                act_transform = self._act.actor.get_transform()
                act_bbox = self._act.actor.bounding_box
                
                # 计算bounding box后方中心点的位置
                # bbox.location是相对于车辆中心的偏移，extent.x是x方向的半尺寸
                # 后方位置 = bbox.location - (extent.x + offset_behind) * forward_vector
                rear_offset_from_bbox_center = act_bbox.extent.x + self._box_spawn_offset_behind_act
                box_spawn_local_position = carla.Location(
                    x=act_bbox.location.x - rear_offset_from_bbox_center,
                    y=act_bbox.location.y,
                    z=act_bbox.location.z
                )
                
                # 将局部坐标转换为世界坐标
                box_spawn_world_position = act_transform.transform(box_spawn_local_position)
                
                box_spawn_location = carla.Location(
                    x=box_spawn_world_position.x,
                    y=box_spawn_world_position.y,
                    z=1.5  # 高度z=1.5
                )
                
                box_spawn_transform = carla.Transform(
                    location=box_spawn_location,
                    rotation=carla.Rotation(yaw=act_transform.rotation.yaw)
                )
                
                box = self._context.actors.create_actor(
                    bp=CarlaBlueprints.STATIC_PROP_BOX01,
                    tf=box_spawn_transform,
                    name='OBS_BOX_RUNTIME',
                )
                box.spawn(self._context.world, ignore_spawn_failure=True)
                
                # 初始不启用物理
                if box.actor is not None and box.actor.is_alive:
                    box.actor.set_simulate_physics(False)
                
                self._obstacles.append(box)
                self._is_box_spawned = True
                self.logger.info(f'BOX spawned behind ACT at ({box_spawn_location.x:.2f}, {box_spawn_location.y:.2f}, {box_spawn_location.z:.2f}) on rising edge (distance: {self._previous_act_to_obs_distance:.2f}m -> {current_act_to_obs_distance:.2f}m)')
            
            # 更新上一次的距离
            self._previous_act_to_obs_distance = current_act_to_obs_distance
        
        # 如果BOX已生成但物理未启用，检测ACT和BOX是否不相交
        if (self._is_box_spawned and not self._is_box_physics_enabled and 
            len(self._obstacles) > 0 and
            self._act is not None and self._act.actor is not None and self._act.actor.is_alive):
            
            box = self._obstacles[0]
            if box.actor is not None and box.actor.is_alive:
                # 检测ACT和BOX是否相交（使用bounding box检测）
                act_bbox = self._act.actor.bounding_box
                box_bbox = box.actor.bounding_box
                
                act_transform = self._act.actor.get_transform()
                box_transform = box.actor.get_transform()
                
                # 计算两个bounding box的中心点距离
                act_bbox_center_world = act_transform.transform(act_bbox.location)
                box_bbox_center_world = box_transform.transform(box_bbox.location)
                
                # 计算两个bounding box的最大尺寸
                act_bbox_max_size = max(act_bbox.extent.x, act_bbox.extent.y, act_bbox.extent.z) * 2
                box_bbox_max_size = max(box_bbox.extent.x, box_bbox.extent.y, box_bbox.extent.z) * 2
                
                distance_between_centers = act_bbox_center_world.distance(box_bbox_center_world)
                min_separation_distance = (act_bbox_max_size + box_bbox_max_size) / 2
                
                # 如果不相交（距离大于最小分离距离）
                if distance_between_centers > min_separation_distance:
                    # 获取act当前速度
                    act_velocity = self._act.actor.get_velocity()
                    
                    # 给BOX赋予act的速度，并启用物理
                    box.actor.set_simulate_physics(True)
                    box.actor.set_target_velocity(act_velocity)
                    
                    self._is_box_physics_enabled = True
                    self.logger.info(f'BOX physics enabled with velocity ({act_velocity.x:.2f}, {act_velocity.y:.2f}, {act_velocity.z:.2f})')
        
        # 检测ego和障碍物生成点的距离，刹停ego
        if (self._ego.actor is not None and self._ego.actor.is_alive and 
            self._obstacle_spawn_point_location is not None):
            
            ego_location = self._ego.actor.get_location()
            ego_to_obs_distance = ego_location.distance(self._obstacle_spawn_point_location)
            
            # 如果距离小于阈值，刹停ego
            if ego_to_obs_distance < self._ego_brake_distance_threshold:
                self._is_ego_braked = True
                self._ego.set_carla_autopilot(enable=False)
                self.logger.info(f'EGO braked at distance {ego_to_obs_distance:.2f}m (threshold: {self._ego_brake_distance_threshold}m)')
        
        return super().tick()

    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        if self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            self._act.set_carla_autopilot(enable=False)
        return super().teardown()