import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorLotLightPollution(Factor):
    NAME = 'F_LotLightPollution'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/SUSTech_COE_ParkingLot': {
            'ego': 24,
            'npc': [1, 12, 15, 18, 25]
        },
    }

    def __init__(
        self, context: CarlaContext, ego: CarlaVehicle, *,
        s1_left_offset: float = 2.3,
        s_spacing: float = 2,
        static_vehicle_count: int = 10,
        trigger_distance: float = 20.0,
        act_ap_takeover_delay: float = 1.8,
        ego_aeb_distance: float = 7.0,
        ego_start_seconds: float = 3.0,
    ):
        super().__init__(context)
        self._ego = ego
        self._s1_left_offset = s1_left_offset
        self._s_spacing = s_spacing
        self._static_vehicle_count = static_vehicle_count
        self._trigger_distance = trigger_distance
        self._act_ap_takeover_delay = act_ap_takeover_delay
        self._ego_aeb_distance = ego_aeb_distance
        self._ego_start_ticks = int(ego_start_seconds * self._context.fps)
        self._static_vehicles: list[CarlaVehicle] = []
        self._vehicles: list[CarlaVehicle] = []
        self._act: CarlaVehicle | None = None
        self._act_triggered = False
        self._act_start_ticks: int | None = None
        self._act_ap_enabled = False  # 标记act是否已启用AP
        self._ego_aeb_triggered = False
        self._ego_started = True
        self._current_ticks = 0
        self.debug = context.world.debug

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
        act_rotation=carla.Rotation(pitch=tf_ego.rotation.pitch,yaw=-tf_ego.rotation.yaw,roll=tf_ego.rotation.roll)
        
        # 1. 在ego生成点，向left偏置的地方生成第一辆静止的车辆，记为s1
        current_location = carla.Location(
            x=tf_ego.location.x + self._s1_left_offset * np.sin(ego_yaw_rad),
            y=tf_ego.location.y + self._s1_left_offset * np.cos(ego_yaw_rad),
            z=tf_ego.location.z
        )
        
        # 生成静态车辆（s1, s2, ..., sN）
        for i in range(1, self._static_vehicle_count + 1):
            if i == 6:
                self._s1_left_offset -= 0.3
            s_transform = carla.Transform(
                location=current_location,
                rotation=act_rotation
            )

            s_vehicle = self._context.actors.create_vehicle(
                bp=CarlaBlueprints.VEHICLE_TESLA_MODEL3,
                tf=s_transform,
                name=f'S{i}',
            )
            s_vehicle.spawn(self._context.world, ignore_spawn_failure=True)
            
            # 只将成功spawn的车辆添加到列表
            if s_vehicle.actor is not None and s_vehicle.actor.is_alive:
                self._static_vehicles.append(s_vehicle)
                # 标记为act
                if i == 4:
                    self._act = s_vehicle
                    self.logger.info(f'ACT vehicle (S{i}) spawned at ({current_location.x:.2f}, {current_location.y:.2f}, {current_location.z:.2f})')
                else:
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
        if spawned_actors:
            self._context.actors.wait_stable(*spawned_actors)

        # ego和npc开始AP（静态车辆不启动AP）
        tm = self._context.traffic_manager
        for vehicle in spawned_actors:
            if vehicle.name.startswith('NPC_') and vehicle.name != 'NPC_1':
                tm.auto_lane_change(vehicle.actor, False)
                vehicle.set_carla_autopilot(enable=True)
        
        return super().setup()

    def tick(self) -> None:
        self._current_ticks += 1

        if self._current_ticks <= self._ego_start_ticks:
            control = carla.VehicleControl(throttle=0.5, brake=0.0, steer=0.0)
            self._ego.actor.apply_control(control)

        if self._current_ticks > self._ego_start_ticks and self._ego_started:
            self._ego_started = False
            tm = self._context.traffic_manager
            tm.auto_lane_change(self._ego.actor, False)
            self._ego.set_carla_autopilot(enable=True)
            self.logger.info(f'Ego car starts autopilot at tick {self._current_ticks}')

        # 检测ego和act的距离，当距离小于trigger_distance时，触发act起步（仅在act未启用AP时检测）
        if (not self._act_triggered and not self._act_ap_enabled and
            self._ego.actor is not None and self._ego.actor.is_alive and
            self._act is not None and self._act.actor is not None and self._act.actor.is_alive):
            
            ego_location = self._ego.actor.get_location()
            act_location = self._act.actor.get_location()
            distance = ego_location.distance(act_location)
            
            if distance <= self._trigger_distance:
                # 触发act起步：向左打满方向，0.3油门
                self._act.set_carla_autopilot(enable=False)
                control = carla.VehicleControl(throttle=0.3, brake=0.0, steer=-1.0)  # 向左打满方向
                self._act.actor.apply_control(control)
                self._act_triggered = True
                self._act_start_ticks = self._current_ticks
                self.logger.info(f'ACT started moving at distance {distance:.2f}m (trigger threshold: {self._trigger_distance}m)')
        
        # 如果act已起步，持续应用控制直到AP接管
        if (self._act_triggered and
            self._act_start_ticks is not None and
            self._act is not None and self._act.actor is not None and self._act.actor.is_alive):
            
            elapsed_ticks = self._current_ticks - self._act_start_ticks
            elapsed_seconds = elapsed_ticks / self._context.fps
            
            if elapsed_seconds >= self._act_ap_takeover_delay:
                # 启动act的carla AP接管
                self._act.set_carla_autopilot(enable=True)
                tm = self._context.traffic_manager
                tm.auto_lane_change(self._act.actor, False)
                self._act_triggered = False  # 重置标志，避免重复设置
                self._act_start_ticks = None
                self._act_ap_enabled = True  # 标记act已启用AP，不再响应ego距离
                self.logger.info(f'ACT autopilot enabled after {elapsed_seconds:.2f}s, will no longer respond to ego distance')
            else:
                # 持续应用控制：向左打满方向，0.3油门
                control = carla.VehicleControl(throttle=0.3, brake=0.0, steer=-1.0)
                self._act.actor.apply_control(control)
        
        # 检测ego和act的距离，当距离小于ego_aeb_distance时，触发ego AEB
        if (self._ego.actor is not None and self._ego.actor.is_alive and
            self._act is not None and self._act.actor is not None and self._act.actor.is_alive):
            
            ego_location = self._ego.actor.get_location()
            act_location = self._act.actor.get_location()
            distance = ego_location.distance(act_location)
            
            if distance <= self._ego_aeb_distance:
                # 触发ego AEB：禁用autopilot，持续应用刹车
                if not self._ego_aeb_triggered:
                    self._ego.set_carla_autopilot(enable=False)
                    self._ego_aeb_triggered = True
                    self.logger.info(f'EGO AEB triggered at distance {distance:.2f}m (threshold: {self._ego_aeb_distance}m)')
                
                # 持续应用刹车
                control = carla.VehicleControl(throttle=0.0, brake=1.0, steer=0.0)
                self._ego.actor.apply_control(control)
        
        return super().tick()

    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        
        # 禁用act的autopilot（如果存在）
        if self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            self._act.set_carla_autopilot(enable=False)
        
        return super().teardown()