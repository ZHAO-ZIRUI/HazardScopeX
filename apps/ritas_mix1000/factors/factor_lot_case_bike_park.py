import numpy as np
import carla
import random
from shared.scenarios import Factor
from shared.simulator import *


class FactorLotCaseBikePark(Factor):
    NAME = 'F_LotCaseBikePark'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/SUSTech_COE_ParkingLot': {
            'ego': 24,
            'npc': [1, 12, 15, 18, 25]
        },
    }
    AVAILABLE_PARKING_AREAS = [
        carla.Transform(carla.Location(x=-21.58, y=-61.94, z=-2), carla.Rotation(yaw=270)),
        carla.Transform(carla.Location(x=-21.86, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-19.49, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-17.10, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-13.76, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-11.39, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-09.00, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-05.66, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-03.27, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-00.91, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=+02.46, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=+04.82, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=+10.54, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=+26.75, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=+31.48, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=+45.33, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-09.00, y=-44.50, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-13.79, y=-44.50, z=-2), carla.Rotation(yaw=270)),
        carla.Transform(carla.Location(x=-17.15, y=-44.50, z=-2), carla.Rotation(yaw=270)),
        carla.Transform(carla.Location(x=-21.86, y=-44.50, z=-2), carla.Rotation(yaw=90)),
    ]

    def __init__(self, context: CarlaContext, vehicle: CarlaVehicle, wait_trigger_seconds: float = 5.0, triggered_seconds: float = 5.0, 
                 static_vehicle_count: int = 3, s1_left_offset: float = 2.5, s_spacing: float = 7, sn_front_offset: float = 14.0):
        super().__init__(context)
        self._ego = vehicle
        self._vehicles: list[CarlaVehicle] = []
        self._wait_trigger_seconds = wait_trigger_seconds
        self._triggered_seconds = triggered_seconds
        self._count_before_trigger = 0
        self._count_after_trigger = 0
        self._static_vehicle_count = static_vehicle_count
        self._s1_left_offset = s1_left_offset
        self._s_spacing = s_spacing
        self._sn_front_offset = sn_front_offset
        self.world = context.world
        self.debug = self.world.debug

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego

    def bringup(self) -> None:
        spawn_point_mapping = self.MAP_SPAWN_POINT_MAPPING[self._context.map.name]
        # 设置 ego 位置
        tf_ego = self._context.spawn_points[spawn_point_mapping['ego']]
        self._ego.actor.set_transform(tf_ego)
        self._vehicles.append(self._ego)

        # 计算ego的朝向
        ego_yaw_rad = np.radians(tf_ego.rotation.yaw)
        
        spectator = self.world.get_spectator()
        tf_spec = carla.Transform(carla.Location(x=tf_ego.location.x,y=tf_ego.location.y,z=tf_ego.location.z+1.5), tf_ego.rotation)
        spectator.set_transform(tf_spec)

        for i, parking_tf in enumerate(self.AVAILABLE_PARKING_AREAS):
            s_vehicle = self._context.actors.create_vehicle(
                bp=random.choice(CarlaBlueprints.vehicles("2wheel")),
                tf=parking_tf,
                name=f'NPC_Parking_{i+1}',  # 修改命名以反映停车位来源
                ignore_spawn_failure=True
            )
            s_vehicle.spawn()
            
            if s_vehicle is not None and s_vehicle.is_alive:
                self._vehicles.append(s_vehicle)
            else:
                self.logger.warning(f'NPC vehicle failed to spawn at parking area {i+1}')

        # 在ego生成点，向left偏置的地方生成第一辆静止的车辆，记为s1
        current_location = carla.Location(
            x=tf_ego.location.x - self._s1_left_offset * np.sin(ego_yaw_rad) - 11.0 * np.cos(ego_yaw_rad),
            y=tf_ego.location.y - self._s1_left_offset * np.cos(ego_yaw_rad) - 11.0 * np.sin(ego_yaw_rad),
            z=tf_ego.location.z
        )

        # 生成静态车辆（s1, s2, ..., sN）
        for i in range(1, self._static_vehicle_count + 1):
            s_transform = carla.Transform(
                location=current_location,
                rotation=carla.Rotation(pitch=0,yaw=random.randint(-179,179),roll=0)
            )

            s_vehicle = self._context.actors.create_vehicle(
                bp=random.choice(CarlaBlueprints.vehicles("2wheel")),
                tf=s_transform,
                name=f'S{i}',
                ignore_spawn_failure=True
            )
            s_vehicle.spawn()
            # 只将成功spawn的车辆添加到列表
            if s_vehicle is not None and s_vehicle.is_alive:
                self._vehicles.append(s_vehicle)
            else:
                self.logger.warning(f'Static vehicle S{i} failed to spawn at ({current_location.x:.2f}, {current_location.y:.2f}, {current_location.z:.2f})')
            
            # 无论成功与否，都基于当前位置计算下一辆的位置
            if i < self._static_vehicle_count:
                # 如果当前车辆spawn成功，使用其bounding box计算间距；否则使用固定间距
                if s_vehicle is not None and s_vehicle.is_alive:
                    vehicle_bbox = s_vehicle.actor.bounding_box
                    vehicle_length = vehicle_bbox.extent.x * 2
                    spacing = vehicle_length + self._s_spacing + 5
                else:
                    # spawn失败时使用固定间距（假设车辆长度约6米）
                    spacing = 17.0 + self._s_spacing
                
                current_location = carla.Location(
                    x=current_location.x + spacing * np.cos(ego_yaw_rad),
                    y=current_location.y + spacing * np.sin(ego_yaw_rad),
                    z=current_location.z
                )
        
        current_location = carla.Location(
            x=tf_ego.location.x + self._sn_front_offset * np.cos(ego_yaw_rad),
            y=tf_ego.location.y + self._sn_front_offset * np.sin(ego_yaw_rad),
            z=tf_ego.location.z
        )
        
        # 生成静态车辆（sN, sN+1, ..., s2N）
        for i in range(self._static_vehicle_count, self._static_vehicle_count * 2):
            s_transform = carla.Transform(
                location=current_location,
                rotation=carla.Rotation(pitch=0,yaw=random.randint(-179,179),roll=0)
            )
            s_vehicle = self._context.actors.create_vehicle(
                bp=random.choice(CarlaBlueprints.vehicles("2wheel")),
                tf=s_transform,
                name=f'S{i}',
                ignore_spawn_failure=True
            )
            s_vehicle.spawn()
            # 只将成功spawn的车辆添加到列表
            if s_vehicle is not None and s_vehicle.is_alive:
                self._vehicles.append(s_vehicle)
            else:
                self.logger.warning(f'Static vehicle S{i} failed to spawn at ({current_location.x:.2f}, {current_location.y:.2f}, {current_location.z:.2f})')
            
            # 无论成功与否，都基于当前位置计算下一辆的位置
            if i < self._static_vehicle_count * 2:
                # 如果当前车辆spawn成功，使用其bounding box计算间距；否则使用固定间距
                if s_vehicle is not None and s_vehicle.is_alive:
                    vehicle_bbox = s_vehicle.actor.bounding_box
                    vehicle_length = vehicle_bbox.extent.x
                    spacing = vehicle_length + self._s_spacing
                else:
                    # spawn失败时使用固定间距（假设车辆长度约6米）
                    spacing = 14.0 + self._s_spacing
                
                current_location = carla.Location(
                    x=current_location.x + spacing * np.cos(ego_yaw_rad),
                    y=current_location.y + spacing * np.sin(ego_yaw_rad),
                    z=current_location.z
                )

        for i in range(self._static_vehicle_count * 2, self._static_vehicle_count * 4):
            s_transform = carla.Transform(
                location=carla.Location(x=tf_ego.location.x+random.randint(-20,20),y=tf_ego.location.y+random.randint(-20,20),z=-2),
                rotation=carla.Rotation(pitch=0,yaw=random.randint(-179,179),roll=0)
            )
            s_vehicle = self._context.actors.create_vehicle(
                bp=random.choice(CarlaBlueprints.vehicles("2wheel")),
                tf=s_transform,
                name=f'S{i}',
                ignore_spawn_failure=True
            )
            s_vehicle.spawn()
            # 只将成功spawn的车辆添加到列表
            if s_vehicle is not None and s_vehicle.is_alive:
                self._vehicles.append(s_vehicle)
            else:
                self.logger.warning(f'Static vehicle S{i} failed to spawn at ({current_location.x:.2f}, {current_location.y:.2f}, {current_location.z:.2f})')

        # 创建 npc
        for npc_sp_idx in spawn_point_mapping['npc']:
            npc_tf = self._context.spawn_points[npc_sp_idx]
            npc = self._context.actors.create_vehicle(
                bp=random.choice(CarlaBlueprints.vehicles("2wheel")),
                tf=npc_tf,
                name=f'NPC_{npc_sp_idx}',
                ignore_spawn_failure=True
            )
            npc.spawn()
            self._vehicles.append(npc)
        self._context.tick()
        
        # 收集所有成功spawn的actors
        spawned_actors = []
        for vehicle in self._vehicles:
            if vehicle is not None and vehicle.is_alive:
                spawned_actors.append(vehicle)
        if spawned_actors:
            self._context.actors.wait_stable(*spawned_actors)

        # ego和npc开始AP（静态车辆不启动AP）
        tm = self._context.traffic
        for vehicle in spawned_actors:
            if vehicle.name.startswith('NPC_') and not vehicle.name.startswith('NPC_Parking_') and not vehicle.name.startswith('S_'):
                tm.auto_lane_change(vehicle.actor, False)
                print("npc ap:",vehicle.name)
                vehicle.set_carla_autopilot(enable=True)
        self.ego.set_carla_autopilot(enable=True)
        
        return super().bringup()
    
    def trigger(self) -> None:
        # 如果因子不在等待触发阶段, 则直接返回
        if self.stage != self.FactorStage.WAIT_FOR_TRIGGER:
            return
        # 如果等待触发帧数达到阈值, 则触发因子
        if self._count_before_trigger >= self._wait_trigger_seconds * self._context.fps:
            self.stage = self.FactorStage.TRIGGERED
            self.logger.warning(f'Factor {self.NAME} triggered')  # 以警告级别输出
        self._count_before_trigger += 1
        return

    def post_trigger(self) -> None:
        # 如果因子不在触发阶段, 则直接返回
        if self.stage != self.FactorStage.TRIGGERED:
            return
        # 如果触发帧数达到阈值, 则完成因子
        if self._count_after_trigger >= self._triggered_seconds * self._context.fps:
            self.stage = self.FactorStage.COMPLETED
            self.logger.warning(f'Factor {self.NAME} completed')  # 以警告级别输出
        self._count_after_trigger += 1
        return

    def teardown(self) -> None:
        for vehicle in self._vehicles:
            if vehicle is not None and vehicle.is_alive:
                vehicle.set_carla_autopilot(enable=False)
        
        return super().teardown()