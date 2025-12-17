import random
from shared.scenarios import Factor
from shared.simulator import *


class FactorTrafficLargeVehicles(Factor):
    NAME = 'F_TrafficLargeVehicles'

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
        
        # 在附近的 spawn points 生成车辆
        for i, tf in enumerate(nearby_spawn_points):
            agent = self._context.actors.create_vehicle(
                bp=random.choice(CarlaBlueprints.LARGE_VEHICLES()),
                tf=tf,
                name=f'AGENT_LARGE_{i:03d}',
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