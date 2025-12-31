import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseVehicleFollow(Factor):
    NAME = 'F_CaseVehicleFollow'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town10HD_Opt': {
            'ego': 101,
            'npc': [93, 53, 56, 107, 58]
        },
    }

    WAYPOINTS = [
        carla.Location(x=-3.97,y=28.104,z=0.6),
        carla.Location(x=3,y=28.104,z=0.6),
        carla.Location(x=10,y=28.104,z=0.6),
        carla.Location(x=17.091217, y=28.104216, z=0.6),

        # carla.Location(x=33.091217, y=31.104216, z=0.6),
        # carla.Location(x=38.091217, y=36.104216, z=0.6),
        # carla.Location(x=40.389641, y=41.945496, z=0.6),
        # carla.Location(x=40.389641, y=48, z=0.6),

        carla.Location(x=36,y=28.104,z=0.6),
        carla.Location(x=55,y=28.104,z=0.6),
        carla.Location(x=74.798752, y=28.343533, z=0.6),
        carla.Location(x=74.798752, y=28.343533, z=0.6),
        carla.Location(x=90,y=30,z=0.6),
        carla.Location(x=97,y=34,z=0.6),
        carla.Location(x=99.078560, y=42.141800, z=0.6),
        carla.Location(x=98.800659, y=56.890846, z=0.6),
        carla.Location(x=98.800659, y=69.890846, z=0.6),
        carla.Location(x=98.800659, y=82.890846, z=0.6),
        carla.Location(x=98.800659, y=90.890846, z=0.6),
    ]

    def __init__(self, context: CarlaContext, vehicle: CarlaVehicle, wait_trigger_seconds: float = 5.0, triggered_seconds: float = 5.0):
        super().__init__(context)
        self._ego = vehicle
        self._act = None
        self._waypoints = self.WAYPOINTS
        self._vehicles: list[CarlaVehicle] = []
        self._wait_trigger_seconds = wait_trigger_seconds
        self._triggered_seconds = triggered_seconds
        self._count_before_trigger = 0
        self._count_after_trigger = 0
        self.world = context.world
        self.debug = self.world.debug

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego
    
    @property
    def act(self) -> CarlaVehicle:
        return self._act
    
    @property
    def waypoints(self) -> list[carla.Location]:
        return self._waypoints

    def bringup(self) -> None:

        # 设置 ego 位置
        tf_ego = carla.Transform(
            carla.Location(x=-16,y=28.104,z=0.6),
            carla.Rotation(pitch=0,yaw=0,roll=0)
        )
        self._ego.actor.set_transform(tf_ego)
        self._vehicles.append(self._ego)

        tf_act = carla.Transform(
            carla.Location(x=-5,y=28.104,z=0.6),
            carla.Rotation(pitch=0,yaw=0,roll=0)
        )
        s_vehicle = self._context.actors.create_vehicle(
                bp=CarlaBlueprints.VEHICLE_MERCEDES_SPRINTER,
                tf=tf_act,
                name=f'ACT',
                ignore_spawn_failure=True
            )
        s_vehicle.spawn()
        self._act = s_vehicle
        self._vehicles.append(self._act)

        spectator = self.world.get_spectator()
        tf_spec = carla.Transform(carla.Location(x=tf_ego.location.x,y=tf_ego.location.y,z=tf_ego.location.z+1.5), tf_ego.rotation)
        spectator.set_transform(tf_spec)
        
        i = 0
        for location in self.waypoints:
            self.debug.draw_point(location,size=0.3,color=carla.Color(255 - 10 * i,10 * i,10 * i),life_time=1000)
            i += 1

        tm = self._context.traffic
        tm.set_path(self.ego.actor, self.waypoints)
        tm.set_path(self.act.actor, self.waypoints)

        self.ego.set_carla_autopilot(enable=True)
        self.act.set_carla_autopilot(enable=True)
        
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