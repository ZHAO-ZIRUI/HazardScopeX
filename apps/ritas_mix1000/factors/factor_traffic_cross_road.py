import random
from shared.scenarios import Factor
from shared.simulator import *


class FactorTrafficCrossRoad(Factor):
    NAME = 'F_TrafficCrossRoad'

    def __init__(self, context: CarlaContext, vehicle: CarlaVehicle, *, radius: float = 200.0):
        super().__init__(context)
        self._radius = radius
        self._agents: list[CarlaVehicle] = []
        self._vehicle = vehicle

    def setup(self) -> None:
        # 获取主车辆位置
        vehicle_tf = self._vehicle.tf_now
        vehicle_location = vehicle_tf.location
        
        # 筛选附近的 spawn points
        nearby_spawn_points = []
        for tf in self._context.spawn_points:
            distance = vehicle_location.distance(tf.location)
            if distance < self._radius:
                nearby_spawn_points.append(tf)
        
        # 随机打乱 spawn points，以便随机分配车辆类型
        random.shuffle(nearby_spawn_points)
        
        # 在附近的 spawn points 生成车辆
        for i, tf in enumerate(nearby_spawn_points):
            bp = random.choice(CarlaBlueprints.NORMAL_TRAFFIC())
            name_prefix = 'AGENT_NORMAL'
            
            agent = self._context.actors.create_vehicle(
                bp=bp,
                tf=tf,
                name=f'{name_prefix}_{i:03d}',
            )
            agent.spawn(self._context.world, ignore_spawn_failure=True)
            self._agents.append(agent)

        self._context.tick()
        self._context.actors.wait_stable()

        for agent in self._agents:
            if agent.actor is not None:
                agent.set_carla_autopilot(enable=True)

        self._vehicle.set_carla_autopilot(enable=True)

        return super().setup()

    def teardown(self) -> None:
        for agent in self._agents:
            agent.destroy()
        return super().teardown()