import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseWrongWayBike(Factor):
    NAME = 'F_CaseWrongWayBike'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town10HD_Opt': {
            'ego': 101,
            'act': 59,
            'npc': [93, 53, 56, 107, 58]
        },
    }

    def __init__(
        self, context: CarlaContext, ego: CarlaVehicle, *,
        s1_right_offset: float = 3.0,
        s_spacing: float = 2,
        static_vehicle_count: int = 7,
        act_speed_kmh: float = 50.0,
        act_brake_distance: float = 16.0,
    ):
        super().__init__(context)
        self._ego = ego
        self._s1_right_offset = s1_right_offset
        self._s_spacing = s_spacing
        self._static_vehicle_count = static_vehicle_count
        self._act_speed_kmh = act_speed_kmh
        self._act_brake_distance = act_brake_distance
        self._static_vehicles: list[CarlaVehicle] = []
        self._vehicles: list[CarlaVehicle] = []
        self._act: CarlaVehicle | None = None
        self._act_braking = False

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
        
        # 在act位置生成vespa，yaw为-180度
        tf_act_spawn = self._context.spawn_points[spawn_point_mapping['act']]
        act_yaw = tf_act_spawn.rotation.yaw - 180.0
        act_transform = carla.Transform(
            location=tf_act_spawn.location,
            rotation=carla.Rotation(yaw=act_yaw)
        )
        self._act = self._context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_VESPA_ZX125,
            tf=act_transform,
            name='ACT',
        )
        self._act.spawn(self._context.world, ignore_spawn_failure=True)
        if self._act.actor is not None and self._act.actor.is_alive:
            self.logger.info(f'ACT vespa spawned at ({tf_act_spawn.location.x:.2f}, {tf_act_spawn.location.y:.2f}, {tf_act_spawn.location.z:.2f}) with yaw {act_yaw:.2f} degrees')
        
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
        if self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            spawned_actors.append(self._act)
        
        if spawned_actors:
            self._context.actors.wait_stable(*spawned_actors)

        # ego和npc开始AP（静态车辆和act不启动AP）
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
        # act使用set_target_velocity设置速度，朝向他自身的正方向
        if (self._act is not None and self._act.actor is not None and self._act.actor.is_alive and
            not self._act_braking):
            
            # 获取act的朝向
            act_transform = self._act.actor.get_transform()
            act_yaw_rad = np.radians(act_transform.rotation.yaw)
            
            # 计算速度向量（朝向act自身的正方向）
            act_speed_ms = self._act_speed_kmh / 3.6  # 转换为米/秒
            velocity = carla.Vector3D(
                x=act_speed_ms * np.cos(act_yaw_rad),
                y=act_speed_ms * np.sin(act_yaw_rad),
                z=0.0
            )
            self._act.actor.set_target_velocity(velocity)
        
        # 检测ego和act的距离，当距离小于act_brake_distance时，act全力刹车
        if (self._ego.actor is not None and self._ego.actor.is_alive and
            self._act is not None and self._act.actor is not None and self._act.actor.is_alive):
            
            ego_location = self._ego.actor.get_location()
            act_location = self._act.actor.get_location()
            distance = ego_location.distance(act_location)
            
            if distance <= self._act_brake_distance:
                # act全力刹车
                if not self._act_braking:
                    self._act_braking = True
                    self.logger.info(f'ACT braking triggered at distance {distance:.2f}m (threshold: {self._act_brake_distance}m)')
                
                # 持续应用全力刹车
                control = carla.VehicleControl(throttle=0.0, brake=0.11, steer=0.0)
                self._act.actor.apply_control(control)
        
        return super().tick()

    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        
        # 禁用act的autopilot（如果存在）
        if self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            self._act.set_carla_autopilot(enable=False)
        
        return super().teardown()