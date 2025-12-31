import random
from shared.scenarios import Factor
from shared.simulator import *


class FactorLotTrafficLargeVehicles(Factor):
    NAME = 'F_LotTrafficLargeVehicles'

    def __init__(self, context: CarlaContext, vehicle: CarlaVehicle, *, radius: float = 200.0):
        super().__init__(context)
        self._radius = radius
        self._agents: list[CarlaVehicle] = []
        self._vehicle = vehicle

    def bringup(self) -> None:
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
                bp=random.choice(CarlaBlueprints.vehicles("large")),
                tf=tf,
                name=f'AGENT_LARGE_{i:03d}',
                ignore_spawn_failure=True
            )
            agent.spawn()
            self._agents.append(agent)

        self._context.tick()
        spawned_actors = []
        for vehicle in self._agents:
            if vehicle.is_alive:
                spawned_actors.append(vehicle)
        if spawned_actors:
            self._context.actors.wait_stable(*spawned_actors)

        for agent in spawned_actors:
            if agent.actor is not None:
                agent.set_carla_autopilot(enable=True)

        self._vehicle.set_carla_autopilot(enable=True)

        return super().bringup()

    def teardown(self) -> None:
        for agent in self._agents:
            agent.destroy()
        return super().teardown()