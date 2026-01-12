from shared.data.collision import Collision
from shared.data.simulator_output import SimulatorOutput
from shared.simulator import CarlaContext
from shared.utils import Logging
import carla
import queue
import numpy as np

class CarlaEvaluatorAdapter:

    def __init__(self, carla_context: CarlaContext) -> None:
        self._carla_context = carla_context
        self._logger = Logging().get_logger('CarlaAdapter')
        
        self.history = queue.Queue()

    @property
    def world(self):
        return self._carla_context.client.get_world()
    
    def select_vehicles(self, ego_id):
        """获取除自车以外的所有其他车辆"""
        all_vehicles = self.world.get_actors().filter("vehicle.*")
        other_vehicles = []
        for vehicle in all_vehicles:
            if vehicle.id != ego_id:
                other_vehicles.append(vehicle)
        return other_vehicles

    def lidar_cast_ray(self, ego_vehicle: carla.Vehicle, ray_num: int=72):
        """以自车为中心向四周打出射线"""
        world = self.world
        ego_transform = ego_vehicle.get_transform()
        dir32 = [carla.Rotation(0, 360 / ray_num * i, 0) for i in range(0, ray_num)]
        initial_location = ego_transform.location + carla.Location(z=0.4)
        final_locations = []

        for rotation in dir32:
            final_loc = initial_location + rotation.get_forward_vector() * 50 # type: ignore
            final_locations.append(final_loc)

        valid_locations = []
        for final_location in final_locations:
            labelled_points = world.cast_ray(initial_location, final_location)
            for labelled_point in labelled_points:
                if labelled_point.label != carla.CityObjectLabel.NONE and (not ego_vehicle.bounding_box.contains(labelled_point.location, ego_transform)): # type: ignore
                    valid_locations.append(labelled_point.location)
                    if labelled_point.location.distance(initial_location) < 5.0:
                        self._logger.debug(f"Ray hit closed object: {labelled_point.label} at {labelled_point.location}")
                    break
        
        # 绘制射线检测点
        for loc in valid_locations:
            world.debug.draw_point(loc, life_time=0.1)
        return valid_locations
    
    def register_collision_sensor(self, ego_vehicle: carla.Vehicle) -> carla.Sensor:
        bp = self.world.get_blueprint_library().find('sensor.other.collision')
        # collision_sensor = self.world.spawn_actor(bp, carla.Transform(), attach_to=ego_vehicle)
        # if collision_sensor is None:
            # self._logger.error("无法创建碰撞传感器: spawn_actor 返回 None")
            # return None

        # 保留对传感器的引用，防止被 Python 垃圾回收，导致监听器不工作
        # self._sensors.append(collision_sensor)

        # collision_sensor.spawn(lambda event: self._on_collision(event))

        collision_sensor = self._carla_context.actors.create_sensor(bp=bp, tf=carla.Transform(), parent=ego_vehicle)
        collision_sensor.hook_sensor_data_ready.append(self._on_collision)
        collision_sensor.spawn()
        self._logger.info(f"已注册碰撞传感器 (id={collision_sensor.actor.id})！")
        return collision_sensor.actor

    def get_collision_event(self):
        """获取一帧的碰撞事件

        Returns:
            Tuple | None: 碰撞事件
        """
        if not self.history.empty():
            return self.history.get()
        return None

    def _on_collision(self, event: Collision) -> SimulatorOutput:
        self._logger.info(f'发生碰撞 {event.frame}: [{event.other_actor_bp_name}, {event.other_actor_id}]')
        # impulse = event.normal_impulse
        # intensity = np.sqrt(impulse.x**2 + impulse.y**2 + impulse.z**2)
        self.history.put((event.frame, event.other_actor_bp_name))
        return event