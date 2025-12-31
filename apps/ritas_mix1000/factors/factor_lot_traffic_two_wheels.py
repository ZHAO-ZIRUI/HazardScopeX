import numpy as np
import random
from shared.scenarios import Factor
from shared.simulator import *


class FactorLotTrafficTwoWheels(Factor):
    NAME = 'F_LotTrafficTwoWheels'

    def __init__(self, context: CarlaContext, vehicle: CarlaVehicle, *, radius: float = 100.0, other_ratio: float = 0.2):
        super().__init__(context)
        self._radius = radius
        self._other_ratio = other_ratio  # Tesla Model 3 的比例（0.0-1.0）
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
        
        # 随机打乱 spawn points，以便随机分配车辆类型
        random.shuffle(nearby_spawn_points)
        
        # 计算 Tesla Model 3 的数量
        other_count = max(1, int(len(nearby_spawn_points) * self._other_ratio))
        
        # 在附近的 spawn points 生成车辆
        two_wheel_count = 0
        other_count_actual = 0
        for i, tf in enumerate(nearby_spawn_points):
            # 前 tesla_count 个生成 Tesla Model 3，其余生成两轮车
            # print("spawn vehicle at:",tf)
            if i < other_count:
                bp = CarlaBlueprints.VEHICLE_TESLA_MODEL3
                name_prefix = 'AGENT_TESLA'
                other_count_actual += 1
            else:
                bp = random.choice(CarlaBlueprints.vehicles("2wheel"))
                name_prefix = 'AGENT_2W'
                two_wheel_count += 1
            
            agent = self._context.actors.create_vehicle(
                bp=bp,
                tf=tf,
                name=f'{name_prefix}_{i:03d}',
                ignore_spawn_failure=True,
            )
            agent.spawn()
            self._agents.append(agent)

        self._context.tick()

        # 收集所有成功spawn的actors
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