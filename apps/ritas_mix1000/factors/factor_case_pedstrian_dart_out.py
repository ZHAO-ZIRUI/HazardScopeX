import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorCasePedestrianDartOut(Factor):
    NAME = 'F_CasePedestrianDartOut'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town10HD_Opt': {
            'ego': 101,
            'npc': [93, 53, 56, 107, 58]
        },
    }

    def __init__(
        self, context: CarlaContext, ego: CarlaVehicle, *,
        s1_right_offset: float = 3.0,
        s_spacing: float = 2,
        static_vehicle_count: int = 7,
        pedestrian_offset_ahead: float = 3.5,
        trigger_distance: float = 18.0,
        pedestrian_speed: float = 1.5,
    ):
        super().__init__(context)
        self._ego = ego
        self._s1_right_offset = s1_right_offset
        self._s_spacing = s_spacing
        self._static_vehicle_count = static_vehicle_count
        self._pedestrian_offset_ahead = pedestrian_offset_ahead
        self._trigger_distance = trigger_distance
        self._pedestrian_speed = pedestrian_speed  # 米/秒
        self._static_vehicles: list[CarlaVehicle] = []
        self._vehicles: list[CarlaVehicle] = []
        self._pedestrian: CarlaActor | None = None
        self._pedestrian_triggered = False
        self._pedestrian_start_location: carla.Location | None = None
        self._pedestrian_target_location: carla.Location | None = None
        self._pedestrian_yaw: float = 0.0

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego


    def setup(self) -> None:
        spawn_point_mapping = self.MAP_SPAWN_POINT_MAPPING[self._context.map_name]
        # 设置 ego 位置
        tf_ego = self._context.spawn_points[spawn_point_mapping['ego']]
        self._ego.actor.set_transform(tf_ego)
        self._vehicles.append(self._ego)

        # 计算ego的朝向
        ego_yaw_rad = np.radians(tf_ego.rotation.yaw)
        
        # 1. 在ego生成点，向右偏置的地方生成第一辆静止的车辆，记为s1
        current_location = carla.Location(
            x=tf_ego.location.x + self._s1_right_offset * (-np.sin(ego_yaw_rad)),
            y=tf_ego.location.y + self._s1_right_offset * np.cos(ego_yaw_rad),
            z=tf_ego.location.z
        )
        
        # 生成静态车辆（s1, s2, ..., sN）
        last_vehicle_spawn_location = None
        for i in range(1, self._static_vehicle_count + 1):
            s_transform = carla.Transform(
                location=current_location,
                rotation=tf_ego.rotation
            )
            s_vehicle = self._context.actors.create_vehicle(
                bp=CarlaBlueprints.VEHICLE_MERCEDES_SPRINTER,
                tf=s_transform,
                name=f'S{i}',
            )
            s_vehicle.spawn(self._context.world, ignore_spawn_failure=True)
            
            # 只将成功spawn的车辆添加到列表
            if s_vehicle.actor is not None and s_vehicle.actor.is_alive:
                self._static_vehicles.append(s_vehicle)
                self.logger.info(f'Static vehicle S{i} spawned at ({current_location.x:.2f}, {current_location.y:.2f}, {current_location.z:.2f})')
                # 保存最后一辆车的spawn位置
                last_vehicle_spawn_location = current_location
            else:
                self.logger.warning(f'Static vehicle S{i} failed to spawn at ({current_location.x:.2f}, {current_location.y:.2f}, {current_location.z:.2f})')
            
            # 无论成功与否，都基于当前位置计算下一辆的位置
            if i < self._static_vehicle_count:
                # 如果当前车辆spawn成功，使用其bounding box计算间距；否则使用固定间距
                if s_vehicle.actor is not None and s_vehicle.actor.is_alive:
                    vehicle_bbox = s_vehicle.actor.bounding_box
                    vehicle_length = vehicle_bbox.extent.x * 2
                    spacing = vehicle_length + self._s_spacing
                else:
                    # spawn失败时使用固定间距（假设车辆长度约6米）
                    spacing = 6.0 + self._s_spacing
                
                current_location = carla.Location(
                    x=current_location.x + spacing * np.cos(ego_yaw_rad),
                    y=current_location.y + spacing * np.sin(ego_yaw_rad),
                    z=current_location.z
                )
        
        # 在最后一个静态车辆前方生成一个行人
        if last_vehicle_spawn_location is not None:
            # 直接使用spawn时的位置和朝向计算行人位置
            vehicle_yaw_rad = np.radians(tf_ego.rotation.yaw)
            
            # 直接在车辆spawn位置前方pedestrian_offset_ahead米处生成行人
            offset_x = self._pedestrian_offset_ahead * np.cos(vehicle_yaw_rad)
            offset_y = self._pedestrian_offset_ahead * np.sin(vehicle_yaw_rad)
            pedestrian_location = carla.Location(
                x=last_vehicle_spawn_location.x + offset_x,
                y=last_vehicle_spawn_location.y + offset_y,
                z=last_vehicle_spawn_location.z
            )
            
            pedestrian_transform = carla.Transform(
                location=pedestrian_location,
                rotation=carla.Rotation(yaw=tf_ego.rotation.yaw - 90.0)
            )
            
            self._pedestrian = self._context.actors.create_actor(
                bp=CarlaBlueprints.WALKER_PEDESTRIAN_0001,
                tf=pedestrian_transform,
                name='PEDESTRIAN',
            )
            self._pedestrian.spawn(self._context.world, ignore_spawn_failure=True)
            
            # 保存行人的起始位置和朝向
            if self._pedestrian.actor is not None and self._pedestrian.actor.is_alive:
                self._pedestrian_start_location = pedestrian_location
                self._pedestrian_yaw = tf_ego.rotation.yaw - 90.0
                self.logger.info(f'Pedestrian spawned at ({pedestrian_location.x:.2f}, {pedestrian_location.y:.2f}, {pedestrian_location.z:.2f}), {self._pedestrian_offset_ahead}m ahead of last static vehicle')
            else:
                self.logger.warning(f'Pedestrian failed to spawn at ({pedestrian_location.x:.2f}, {pedestrian_location.y:.2f}, {pedestrian_location.z:.2f})')
        
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
        for s_vehicle in self._static_vehicles:
            if s_vehicle.actor is not None and s_vehicle.actor.is_alive:
                spawned_actors.append(s_vehicle)
        if self._pedestrian is not None and self._pedestrian.actor is not None and self._pedestrian.actor.is_alive:
            spawned_actors.append(self._pedestrian)
        
        if spawned_actors:
            self._context.actors.wait_stable(*spawned_actors)

        # ego和npc开始AP（静态车辆不启动AP）
        tm = self._context.traffic_manager
        # 使用TM要求ego在前方路口直行
        tm.auto_lane_change(self._ego.actor, False)
        self._ego.set_carla_autopilot(enable=True)
        for vehicle in self._vehicles:
            if vehicle != self._ego:
                tm.auto_lane_change(vehicle.actor, False)
                vehicle.set_carla_autopilot(enable=True)
        
        return super().setup()

    def tick(self) -> None:
        # 检测行人和ego的距离，当距离小于trigger_distance时，触发行人移动
        if (not self._pedestrian_triggered and
            self._ego.actor is not None and self._ego.actor.is_alive and
            self._pedestrian is not None and self._pedestrian.actor is not None and self._pedestrian.actor.is_alive and
            self._pedestrian_start_location is not None):
            
            ego_location = self._ego.actor.get_location()
            pedestrian_location = self._pedestrian.actor.get_location()
            distance = ego_location.distance(pedestrian_location)
            
            if distance <= self._trigger_distance:
                # 触发行人移动：向朝向方向前进
                pedestrian_yaw_rad = np.radians(self._pedestrian_yaw)
                
                # 计算行人前进方向的目标位置（前进3米）
                forward_distance = 3.0
                target_x = pedestrian_location.x + forward_distance * np.cos(pedestrian_yaw_rad)
                target_y = pedestrian_location.y + forward_distance * np.sin(pedestrian_yaw_rad)
                self._pedestrian_target_location = carla.Location(
                    x=target_x,
                    y=target_y,
                    z=pedestrian_location.z
                )
                
                self._pedestrian_triggered = True
                self.logger.info(f'Pedestrian started moving at distance {distance:.2f}m (trigger threshold: {self._trigger_distance}m)')
        
        # 如果已触发，每帧更新行人的位置
        if (self._pedestrian_triggered and
            self._pedestrian is not None and self._pedestrian.actor is not None and self._pedestrian.actor.is_alive and
            self._pedestrian_target_location is not None):
            
            current_location = self._pedestrian.actor.get_location()
            distance_to_target = current_location.distance(self._pedestrian_target_location)
            
            if distance_to_target > 0.1:  # 如果还没到达目标位置
                # 计算每帧的移动距离
                dt = 1.0 / self._context.fps
                move_distance = self._pedestrian_speed * dt
                
                # 计算朝向目标的方向
                direction_x = self._pedestrian_target_location.x - current_location.x
                direction_y = self._pedestrian_target_location.y - current_location.y
                direction_length = np.sqrt(direction_x**2 + direction_y**2)
                
                if direction_length > 0:
                    # 归一化方向向量
                    direction_x /= direction_length
                    direction_y /= direction_length
                    
                    # 计算新位置（不超过目标位置）
                    move_distance = min(move_distance, distance_to_target)
                    new_x = current_location.x + move_distance * direction_x
                    new_y = current_location.y + move_distance * direction_y
                    
                    # 更新行人的transform（位置由set_transform控制）
                    new_location = carla.Location(
                        x=new_x,
                        y=new_y,
                        z=current_location.z
                    )
                    new_transform = carla.Transform(
                        location=new_location,
                        rotation=carla.Rotation(yaw=self._pedestrian_yaw)
                    )
                    # 更新行人的transform
                    self._pedestrian.actor.set_transform(new_transform)
        
        return super().tick()

    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        
        # 销毁行人（如果存在）
        if self._pedestrian is not None:
            try:
                if self._pedestrian.actor is not None and self._pedestrian.actor.is_alive:
                    self._pedestrian.destroy()
            except Exception as e:
                self.logger.warning(f'Error destroying pedestrian: {e}')
        
        return super().teardown()