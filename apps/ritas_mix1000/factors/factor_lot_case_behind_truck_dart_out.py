import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorLotLightDark(Factor):
    NAME = 'F_LotLightDark'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/SUSTech_COE_ParkingLot': {
            'npc': [1, 12, 15, 18, 25, 33, 45]
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
        tf_ego = carla.Transform(
            carla.Location(x=-40,y=-68,z=-2),
            carla.Rotation(pitch=0,yaw=90,roll=0)
        )
        self._ego.actor.set_transform(tf_ego)
        self._vehicles.append(self._ego)

        # 计算ego的朝向
        ego_yaw_rad = np.radians(tf_ego.rotation.yaw)
        act_rotation=carla.Rotation(pitch=tf_ego.rotation.pitch,yaw=-tf_ego.rotation.yaw,roll=tf_ego.rotation.roll)
        
        spectator = self.world.get_spectator()
        tf_spec = carla.Transform(carla.Location(x=tf_ego.location.x,y=tf_ego.location.y,z=tf_ego.location.z+1.5), tf_ego.rotation)
        spectator.set_transform(tf_spec)

        for i, parking_tf in enumerate(self.AVAILABLE_PARKING_AREAS):
            s_vehicle = self._context.actors.create_vehicle(
                bp=CarlaBlueprints.VEHICLE_AUDI_A2,
                tf=parking_tf,
                name=f'NPC_Parking_{i+1}',  # 修改命名以反映停车位来源
                ignore_spawn_failure=True
            )
            s_vehicle.spawn()
            
            if s_vehicle is not None and s_vehicle.is_alive:
                self._vehicles.append(s_vehicle)
            else:
                self.logger.warning(f'NPC vehicle failed to spawn at parking area {i+1}')

        # 创建 npc
        for npc_sp_idx in spawn_point_mapping['npc']:
            npc_tf = self._context.spawn_points[npc_sp_idx]
            npc = self._context.actors.create_vehicle(
                bp=CarlaBlueprints.VEHICLE_MERCEDES_SPRINTER,
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