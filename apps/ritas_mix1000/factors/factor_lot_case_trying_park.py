import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorLotCaseTryingPark(Factor):
    NAME = 'F_LotCaseTryingPark'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/SUSTech_COE_ParkingLot': {
            'ego': 3,
            'npc': [1, 12, 15, 18, 25]
        },
    }
    AVAILABLE_PARKING_AREAS = [
        carla.Transform(carla.Location(x=-21.58, y=-61.94, z=-2), carla.Rotation(yaw=270)),
        carla.Transform(carla.Location(x=-21.86, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-19.49, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-17.10, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-11.39, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-05.66, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-03.27, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=-00.91, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=+02.46, y=-55.54, z=-2), carla.Rotation(yaw=90)),
        carla.Transform(carla.Location(x=+04.82, y=-55.54, z=-2), carla.Rotation(yaw=90)),
    ]

    def __init__(
        self, context: CarlaContext, 
        ego: CarlaVehicle, *,
        s1_left_offset: float = 2.3,
        s_spacing: float = 2,
        static_vehicle_count: int = 10,
        trigger_distance: float = 20.0,
        step_seconds: float = 2.0,
        wait_trigger_seconds: float = 0.1,
        triggered_seconds: float = 13.0
    ):
        super().__init__(context)
        self._ego = ego
        self._s1_left_offset = s1_left_offset
        self._s_spacing = s_spacing
        self._static_vehicle_count = static_vehicle_count
        self._trigger_distance = trigger_distance
        self._step_seconds = step_seconds
        self._vehicles: list[CarlaVehicle] = []

        self._act: CarlaVehicle | None = None
        self._act_triggered = False
        self._act_ap_enabled = False  # 标记act是否已启用AP
        self.debug = context.world.debug
        self.world = context.world

        self._wait_trigger_seconds = wait_trigger_seconds
        self._triggered_seconds = triggered_seconds
        self._count_before_trigger = 0
        self._count_after_trigger = 0
        self.step = 0 # 用于控制act的动作步骤

    def __post_init__(self) -> None:
        self.hook_update.append(self.trigger)
        self.hook_update.append(self.post_trigger)
        return

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego

    def bringup(self) -> None:
        spawn_point_mapping = self.MAP_SPAWN_POINT_MAPPING[self._context.map.name]
        # 设置 ego 位置
        tf_ego = self._context.spawn_points[spawn_point_mapping['ego']]
        self._ego.actor.set_transform(tf_ego)
        self._vehicles.append(self._ego)

        spectator = self.world.get_spectator()
        tf_spec = carla.Transform(carla.Location(x=tf_ego.location.x,y=tf_ego.location.y,z=tf_ego.location.z+1.5), tf_ego.rotation)
        spectator.set_transform(tf_spec)

        for i, parking_tf in enumerate(self.AVAILABLE_PARKING_AREAS):
            if i == 4:
                parking_tf = carla.Transform(carla.Location(x=parking_tf.location.x+1.03,y=parking_tf.location.y+3.54,z=parking_tf.location.z),carla.Rotation(pitch=0,yaw=73,roll=0))
            s_vehicle = self._context.actors.create_vehicle(
                bp=CarlaBlueprints.VEHICLE_BMW_GRANDTOURER,
                tf=parking_tf,
                name=f'NPC_Parking_{i+1}',  # 修改命名以反映停车位来源
                ignore_spawn_failure=True
            )
            s_vehicle.spawn()
            
            if s_vehicle is not None and s_vehicle.is_alive:
                self._vehicles.append(s_vehicle)
                
                # 将第五辆NPC车辆标记为act
                if i == 4:  # 索引4对应第五辆（从0开始计数）
                    self._act = s_vehicle
                    self.logger.info(f'ACT vehicle (NPC_Parking_{i+1}) spawned at parking area {i+1}')
                else:
                    self.logger.info(f'NPC vehicle (Parking_{i+1}) spawned at ({parking_tf.location.x:.2f}, {parking_tf.location.y:.2f}, {parking_tf.location.z:.2f})')
            else:
                self.logger.warning(f'NPC vehicle failed to spawn at parking area {i+1}')

        # 创建 npc
        for npc_sp_idx in spawn_point_mapping['npc']:
            npc_tf = self._context.spawn_points[npc_sp_idx]
            s_vehicle = self._context.actors.create_vehicle(
                bp=CarlaBlueprints.VEHICLE_AUDI_A2,
                tf=npc_tf,
                name=f'NPC_{npc_sp_idx}',
                ignore_spawn_failure=True
            )
            s_vehicle.spawn()
            self._vehicles.append(s_vehicle)
        self._context.tick()
        
        # 收集所有成功spawn的NPC actors
        spawned_actors = []
        for vehicle in self._vehicles:
            if vehicle is not None and vehicle.is_alive:
                spawned_actors.append(vehicle)
        if spawned_actors:
            self._context.actors.wait_stable(*spawned_actors)

        # ego开始AP
        tm = self._context.traffic
        for vehicle in spawned_actors:
            if vehicle.name.startswith('NPC_') and not vehicle.name.startswith('NPC_Parking_'):
                tm.auto_lane_change(vehicle.actor, False)
                vehicle.set_carla_autopilot(enable=True)
        tm.auto_lane_change(self._ego.actor, False)
        tm.set_route(self._ego.actor, ['Straight'])
        # self._ego.set_carla_autopilot(enable=True)
        
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
        if self._count_after_trigger < self._step_seconds * self._context.fps:
            if self.step == 0:
                control = carla.VehicleControl(throttle=0.4, brake=0.0, steer=-0.25,reverse=True) 
                self._act.actor.apply_control(control)
                self.logger.info(f'ACT started reserving after {self._wait_trigger_seconds} seconds.')
                self.step = 1
        elif self._count_after_trigger < self._step_seconds * self._context.fps * 3:
            if self.step == 1:
                control = carla.VehicleControl(throttle=0.4, brake=0.0, steer=+0.25) 
                self._act.actor.apply_control(control)
                self.logger.info(f'ACT started moving after {self._wait_trigger_seconds + self._step_seconds} seconds.')
                self.step = 2
        elif self._count_after_trigger < self._step_seconds * self._context.fps * 4.5:
            if self.step == 2:
                control = carla.VehicleControl(throttle=0.4, brake=0.0, steer=0.25,reverse=True) 
                self._act.actor.apply_control(control)
                self.logger.info(f'ACT started reserving after {self._wait_trigger_seconds + self._step_seconds * 3} seconds.')
                self.step = 3
        else:
            if self.step == 3:
                # 启动act的carla AP接管
                self._act.set_carla_autopilot(enable=True)
                self.logger.info(f'ACT autopilot enabled after {self._wait_trigger_seconds + self._step_seconds * 4.5} seconds.')
                self.step = 4

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