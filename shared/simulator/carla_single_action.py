import numpy as np
from logging import Logger
import carla
import random
import math
from shared.scenarios import Factor
from shared.simulator import *
from shared.simulator.carla_parkinglot_manager import AVAILABLE_PARKING_AREAS

class CarlaSingleAction():
    NAME = 'CarlaSingleAction'

    def __init__(self, context: CarlaContext, ego: CarlaVehicle, logger: Logger):
        self._context = context
        self._ego = ego
        self._logger = logger
        self._client = context.client
        self._world = context.world
        self._map = context.map
        self._debug = self._world.debug
        self._tm = self._context.traffic

    @property
    def context(self) -> CarlaContext:
        return self._context

    @property
    def world(self) -> carla.World:
        return self._world
    
    @property
    def ego(self) -> CarlaVehicle:
        return self._ego

    @property
    def logger(self) -> Logger:
        return self._logger

    def lotStatic_parking_car(self, distance: float = 100.0,
                            mix_large = 0.0, 
                            mix_emergency = 0.0,
                            mix_head_in = 0.0, 
                            mix_empty = 0.0, 
                            limit_yaw = 0.0, 
                            limit_drift_short = 0.0, 
                            limit_drift_long = 0.0):
        if mix_large + mix_emergency + mix_empty > 1.0:
            self._logger.error('Mix ratios exceed 1.0, please adjust the parameters.')
            return
        if mix_head_in > 1.0:
            self._logger.error('Mix head-in ratio exceed 1.0, please adjust the parameters.')
            return
        if mix_large < 0 or mix_emergency < 0 or mix_empty < 0 or mix_head_in < 0:
            self._logger.error('The proportion cannot be negative.')
            return

        car_bp_list = CarlaBlueprints.vehicles('car')
        large_bp_list = CarlaBlueprints.vehicles('large')
        emergency_bp_list = CarlaBlueprints.vehicles('emergency')

        parking_vehicles = []
        parking_areas = AVAILABLE_PARKING_AREAS

        # 筛选附近的 spawn points
        nearby_parking_areas = []
        tf_ego = self._ego.tf_now_baselink
        for area in parking_areas:
            location_distance = math.sqrt((tf_ego.location.x - area.x) ** 2 + (tf_ego.location.y - area.y) ** 2)
            if location_distance < distance:
                nearby_parking_areas.append(area)

        for i, parking_area in enumerate(nearby_parking_areas):

            r = random.random()
            if r < mix_large:
                # create large
                bp = random.choice(large_bp_list)
            elif r < mix_large + mix_emergency:
                # create emergency
                bp = random.choice(emergency_bp_list)
            elif r < mix_large + mix_emergency + mix_empty:
                # Not create
                continue
            else:
                # create car
                bp = random.choice(car_bp_list)

            r = random.random()
            if r < mix_head_in:
                reverse = False
            else:
                reverse = True
            
            rand_pos_x = limit_drift_long * abs(math.cos(limit_yaw)) + limit_drift_short * abs(math.sin(limit_yaw))
            rand_pos_y = limit_drift_long * abs(math.sin(limit_yaw)) + limit_drift_short * abs(math.cos(limit_yaw))

            s_vehicle = self._context.actors.create_vehicle(
                bp=bp,
                tf=parking_area.get_spawn_point(reverse=reverse,rand_pos_x=rand_pos_x,rand_pos_y=rand_pos_y,rand_yaw=limit_yaw),
                name=f'NPC_Parking_{i+1}',  # 修改命名以反映停车位来源
                ignore_spawn_failure=True
            )
            s_vehicle.spawn()
            
            if s_vehicle is not None and s_vehicle.is_alive:
                parking_vehicles.append(s_vehicle)
            else:
                self.logger.warning(f'NPC vehicle failed to spawn at parking area {i+1}')
        return parking_vehicles

    def autopilot_traffic(self, nums: int = 100,
                         distance: float = 100.0,
                         spawn_point_list: list[int] = None,
                         spawn_transform_list: list[carla.Transform] = None,
                         mix_car: float = 1.0,
                         mix_large: float = 0.0, 
                         mix_2wheel: float = 0.0,
                         mix_emergency = 0.0,) -> list[CarlaVehicle]:
        
        if mix_car + mix_large + mix_2wheel + mix_emergency > 1.0:
            print("mix_car:",mix_car," mix_large:",mix_large," mix_2wheel:",mix_2wheel," mix_emergency:",mix_emergency)
            self._logger.error('Mix ratios exceed 1.0, please adjust the parameters.')
            return
        if mix_car < 0 or mix_large < 0 or mix_2wheel < 0 or mix_emergency < 0:
            self._logger.error('The proportion cannot be negative.')
            return
        if spawn_point_list is None and spawn_transform_list is None:
            spawn_transform_list = self._context.spawn_points

        # 获取主车辆位置
        tf_ego = self._ego.tf_now_baselink
        vehicle_location = tf_ego.location

        tf_list = []
        if spawn_transform_list is not None:
            tf_list = spawn_transform_list
        if spawn_point_list is not None:
            for id in spawn_point_list:
                tf = self._context.spawn_points[id]
                tf_list.append(tf)
        
        # 筛选附近的 spawn points
        nearby_spawn_points = []
        for tf in tf_list:
            location_distance = vehicle_location.distance(tf.location)
            if location_distance < distance:
                nearby_spawn_points.append(tf)
        random.shuffle(nearby_spawn_points)

        car_bp_list = CarlaBlueprints.vehicles('car')
        large_bp_list = CarlaBlueprints.vehicles('large')
        emergency_bp_list = CarlaBlueprints.vehicles('emergency')
        twowheel_bp_list = CarlaBlueprints.vehicles('2wheel')

        vehicles = []

        # 在附近的 spawn points 生成车辆
        for i, tf in enumerate(nearby_spawn_points):
            if i > nums:
                break
            r = random.random()
            if r < mix_car:
                # create car
                bp = random.choice(car_bp_list)
                name_prefix = 'NPC_Car'
            elif r < mix_car + mix_large:
                # create large
                bp = random.choice(large_bp_list)
                name_prefix = 'NPC_Large'
            elif r < mix_car + mix_large + mix_emergency:
                # create emergency
                bp = random.choice(emergency_bp_list)
                name_prefix = 'NPC_Emergency'
            elif r < mix_car + mix_large + mix_emergency + mix_2wheel:
                # create 2wheel
                bp = random.choice(twowheel_bp_list)
                name_prefix = 'NPC_2Wheel'
            else:
                # Not create
                continue
            
            agent = self._context.actors.create_vehicle(
                bp=bp,
                tf=tf,
                name=f'{name_prefix}_{i:03d}',
                ignore_spawn_failure=True,
            )
            agent.spawn()
            vehicles.append(agent)

        self._context.tick()

        # 收集所有成功spawn的actors
        spawned_actors = []
        for vehicle in vehicles:
            if vehicle.is_alive:
                spawned_actors.append(vehicle)
        if spawned_actors:
            self._context.actors.wait_stable(*spawned_actors)

        for agent in spawned_actors:
            if agent.actor is not None:
                agent.set_carla_autopilot(enable=True)

        return spawned_actors
    
    def manual_control_vehicle(
                        self,   
                        vehicle: CarlaVehicle = None,
                        spawnpoint: int = None,
                        transform: carla.Transform = None,
                        bp_type: str = None,
                        bp: str = None,
                        throttle: float = 0.0,
                        steer: float = 0.0,
                        brake: float = 0.0,
                        reverse: bool = False) -> CarlaVehicle:
        if throttle < 0 or throttle > 1:
            self._logger.error('Throttle beyond range.')
            return
        if steer < -1 or steer > 1:
            self._logger.error('Steer beyond range.')
            return
        if brake < 0 or brake > 1:
            self._logger.error('Brake beyond range.')
            return

        if vehicle is not None:
            act = vehicle
        else:
            if transform is not None:
                act_transform = transform
            elif spawnpoint is not None:
                act_transform = self._context.spawn_points[spawnpoint]
            else:
                self._logger.error('The vehicle generation point has not been passed in.')
                return 

            if bp is not None:
                act_bp = bp
            elif bp_type is not None:
                act_bp = random.choice(CarlaBlueprints.vehicles(bp_type))
            else:
                act_bp = random.choice(CarlaBlueprints.vehicles())

            act = self._context.actors.create_vehicle(
                bp=act_bp,
                tf=act_transform,
                name=f'ACT',
                ignore_spawn_failure=True
            )
            act.spawn()

        control = carla.VehicleControl(throttle=throttle, brake=brake, steer=steer, reverse=reverse)
        act.actor.apply_control(control)

        return act

    def generate_pedestrain(self,
                            pedestrain: carla.Walker = None,
                            transform: carla.Transform = None,
                            bp: str = None,
                            destination: carla.Transform = None,
                            direction: carla.Vector3D = None,
                            speed: float = 0.0,
                            jump: bool = False,) -> carla.Walker:
        if pedestrain is not None:
            act = pedestrain
        else:
            if bp is not None:
                pedestrain_blueprint = bp
            else:
                pedestrain_blueprint = random.choice(CarlaBlueprints.walkers())
            # 设置行人起点
            act = self._context.actors.create_actor(
                bp=pedestrain_blueprint,
                tf=transform,
                name=f'Walker_ACT',
                ignore_spawn_failure=False,
            )
            act.spawn()

        pedestrain_control = carla.WalkerControl()
        if destination is not None:
            pedestrain_control.direction = carla.Vector3D(x=destination.location.x-transform.location.x,
                                                          y=destination.location.y-transform.location.y,
                                                          z=destination.location.z-transform.location.z)
        else:
            if direction is not None:
                pedestrain_control.direction = direction
            else:
                self._logger.error('The pedestrain\'s moving target is not specified.')
                return 

        pedestrain_control.speed = speed
        pedestrain_control.jump = jump
        act.actor.apply_control(pedestrain_control)

        return act
    
    def random_move_pedestrains(self,
                                nums: int = 100,
                                distance: float = 100.0,
                                spawn_point_list: list[int] = None,
                                spawn_transform_list: list[carla.Transform] = None,) -> list[carla.Walker]:
        # 获取主车辆位置
        tf_ego = self._ego.tf_now_baselink
        vehicle_location = tf_ego.location

        tf_list = []
        if spawn_transform_list is not None:
            tf_list = spawn_transform_list
        if spawn_point_list is not None:
            for id in spawn_point_list:
                tf = self._context.spawn_points[id]
                tf_list.append(tf)
        
        # 筛选附近的 spawn points
        nearby_spawn_points = []
        for tf in tf_list:
            location_distance = vehicle_location.distance(tf.location)
            if location_distance < distance:
                nearby_spawn_points.append(tf)
        random.shuffle(nearby_spawn_points)

        walkers = []
        for i, tf in enumerate(nearby_spawn_points):
            if i > nums:
                break
            
            agent = self._context.actors.create_actor(
                bp=random.choice(CarlaBlueprints.walkers()),
                tf=tf,
                name=f'Walker{i:03d}',
                ignore_spawn_failure=True,
            )
            agent.spawn()
            walkers.append(agent)

        self._context.tick()

        # 收集所有成功spawn的actors
        spawned_actors = []
        for walker in walkers:
            if walker.is_alive:
                spawned_actors.append(walker)
        if spawned_actors:
            self._context.actors.wait_stable(*spawned_actors)

        for walker in spawned_actors:
            pedestrain_control = carla.WalkerControl()
            r = random.uniform(0,3)
            pedestrain_control.speed = r
            pedestrain_rotation = carla.Rotation(0,random.uniform(-180,180),0)
            pedestrain_control.direction = pedestrain_rotation.get_forward_vector()
            # r = random.random()
            # if r > 0.5:
            #     pedestrain_control.jump = True
            # else:
            #     pedestrain_control.jump = False
            # 在地库让行人起跳可能会出现行人飞天bug
            pedestrain_control.jump = False
            walker.actor.apply_control(pedestrain_control)

        return spawned_actors
    
    def create_static_object(self,
                             transform: carla.Transform = None,
                             bp: str = None) -> CarlaActor:
        static_object = self._context.actors.create_actor(
                bp=bp,
                tf=transform,
                name=f'Static_{bp}',
                ignore_spawn_failure=True,
        )
        static_object.spawn()
        static_object.actor.set_simulate_physics(True)
        return static_object

    def create_static_objects(self,
                            nums: int = 100,
                            distance: float = 100.0,
                            spawn_point_list: list[int] = None,
                            spawn_transform_list: list[carla.Transform] = None,
                            ) -> list[CarlaActor]:
        # 获取主车辆位置
        tf_ego = self._ego.tf_now_baselink
        vehicle_location = tf_ego.location

        static_objects = []
        nearby_spawn_points = []

        if spawn_transform_list is not None or spawn_point_list is not None:
            tf_list = []
            if spawn_transform_list is not None:
                tf_list = spawn_transform_list
            if spawn_point_list is not None:
                for id in spawn_point_list:
                    tf = self._context.spawn_points[id]
                    tf_list.append(tf)
            
            # 筛选附近的 spawn points
            for tf in tf_list:
                location_distance = vehicle_location.distance(tf.location)
                if location_distance < distance:
                    nearby_spawn_points.append(tf)
            random.shuffle(nearby_spawn_points)
        else:
            for i in range(nums):
                dx = random.uniform(-distance, distance)
                dy = math.sqrt(distance**2 - dx**2) * random.choice([-1, 1])
                tf = carla.Transform(
                    carla.Location(
                        x=vehicle_location.x + dx,
                        y=vehicle_location.y + dy,
                        z=vehicle_location.z,
                    ),
                    carla.Rotation(
                        pitch=0.0,
                        yaw=random.uniform(-180.0, 180.0), 
                        roll=0.0,
                    )
                )
                nearby_spawn_points.append(tf)

        # 在附近的 spawn points 生成static objects
        for i, tf in enumerate(nearby_spawn_points):
            if i > nums:
                break
            bp = random.choice(CarlaBlueprints.static_objects())
            static_object = self._context.actors.create_actor(
                bp=bp,
                tf=tf,
                name=f'Static_{i}',
                ignore_spawn_failure=True,
            )
            static_object.spawn()
            if static_object is not None and static_object.is_alive:
                static_object.actor.set_simulate_physics(True)
                static_objects.append(static_object)

        self._context.tick()

        # 收集所有成功spawn的actors
        spawned_actors = []
        for static_object in static_objects:
            if static_object.is_alive:
                spawned_actors.append(static_object)
        if spawned_actors:
            self._context.actors.wait_stable(*spawned_actors)

        return static_objects
    
    def object_fly_away(self
            
                                    ):
        initial_velocity = spec_transform.rotation.get_forward_vector()
        box = manager.spawn_one_box(spec_transform, world, blueprint_id='static.prop.streetbarrier')
        box.set_simulate_physics(True)
        box.set_target_velocity(initial_velocity*10) # type: ignore
        box.add_impulse(initial_velocity*500) # type: ignore
        return

    def transform_from_ego(self,
                           left_offset: float = 0.0,
                           front_offset: float = 0.0,
                           height_offset: float = 0.0,
                           yaw_offset: float = 0.0) -> carla.Transform:
        tf_ego = self._ego.tf_now_baselink

        ego_yaw_rad = np.radians(tf_ego.rotation.yaw)
        rotation=carla.Rotation(pitch=tf_ego.rotation.pitch,yaw=tf_ego.rotation.yaw + yaw_offset,roll=tf_ego.rotation.roll)

        location = carla.Location(
            x=tf_ego.location.x + left_offset * np.sin(ego_yaw_rad) + front_offset * np.cos(ego_yaw_rad),
            y=tf_ego.location.y + left_offset * np.cos(ego_yaw_rad) + front_offset * np.sin(ego_yaw_rad),
            z=tf_ego.location.z + height_offset
        )

        transform = carla.Transform(location=location, rotation=rotation)
        return transform
    
    def transform_from_transform(self,
                                 transform: carla.Transform = None,
                                 left_offset: float = 0.0,
                                 front_offset: float = 0.0,
                                 height_offset: float = 0.0,
                                 yaw_offset: float = 0.0) -> carla.Transform:
        if transform is None:
            self._logger.error('Initial transform is not passed in.')
            return
        
        yaw = transform.rotation.yaw
        if 0 < yaw <= 90:
            yaw = 90 - yaw
        elif 90 < yaw <= 180:
            yaw = 450 - yaw
        elif -90 < yaw <= 0:
            yaw = 90 - yaw
        else:
            yaw = 90 - yaw
        transform_yaw_rad = np.radians(yaw)
        rotation=carla.Rotation(pitch=transform.rotation.pitch,yaw=transform.rotation.yaw + yaw_offset,roll=transform.rotation.roll)

        location = carla.Location(
            x=transform.location.x + left_offset * np.sin(transform_yaw_rad + math.pi / 2) + front_offset * np.cos(transform_yaw_rad + math.pi / 2),
            y=transform.location.y + left_offset * np.cos(transform_yaw_rad + math.pi / 2) + front_offset * np.sin(transform_yaw_rad + math.pi / 2),
            z=transform.location.z + height_offset
        )

        transform = carla.Transform(location=location, rotation=rotation)
        return transform
    
    def set_vehicle_light(self, vehicle: CarlaVehicle, 
                          none: bool = False,
                          position: bool = False,
                          lowbeam: bool = False,
                          highbeam: bool = False,
                          brake: bool = False,
                          rightblinker: bool = False,
                          leftblinker: bool = False,
                          reverse: bool = False,
                          fog: bool = False,
                          interior: bool = False,
                          special1: bool = False,
                          special2: bool = False,
                          all: bool = False,):
        light_state = vehicle.actor.get_light_state()
        if all:
            light_state = carla.VehicleLightState.ALL_LIGHTS
        else:
            light_state = carla.VehicleLightState(0)
            if none:
                light_state |= carla.VehicleLightState.NONE
            if position:
                light_state |= carla.VehicleLightState.Position
            if lowbeam:
                light_state |= carla.VehicleLightState.LowBeam
            if highbeam:
                light_state |= carla.VehicleLightState.HighBeam
            if brake:
                light_state |= carla.VehicleLightState.Brake
            if rightblinker:
                light_state |= carla.VehicleLightState.RightBlinker
            if leftblinker:
                light_state |= carla.VehicleLightState.LeftBlinker
            if reverse:
                light_state |= carla.VehicleLightState.Reverse
            if fog:
                light_state |= carla.VehicleLightState.Fog
            if interior:
                light_state |= carla.VehicleLightState.Interior
            if special1:
                light_state |= carla.VehicleLightState.Special1
            if special2:
                light_state |= carla.VehicleLightState.Special2

        vehicle.actor.set_light_state(carla.VehicleLightState(light_state))
        return
    
    def get_path_by_start_point(self, start_location: carla.Location = None, distance: float = 200.0, interval: float = 5.0) -> list[carla.Waypoint]:
        """
        从起点开始，规划一条确定的 Waypoint 路径。
        我们总是选择最右侧（车道不变）或直行（路口）路径。
        """
        if start_location is None:
            self._logger.error('Initial location is not passed in.')
            return
        
        carla_map = self.world.get_map()
        current_wp = carla_map.get_waypoint(start_location, project_to_road=True)
        
        path = []
        for _ in range(int(distance / interval)): # 每 5 米一个 Waypoint
            path.append(current_wp)
            
            # 核心逻辑：路径选择
            next_wps = current_wp.next(interval) # 获取前方 5 米的所有可能 Waypoint
            
            if not next_wps:
                break
                
            # 在路口：我们总是选择第一个 Waypoint（通常是直行或默认路径）
            # 在直道：选择 lane_id 不变的 Waypoint
            
            next_wp = next_wps[0] # 默认选择第一个
            
            if current_wp.is_junction and len(next_wps) > 1:
                # 在路口时，可以加入自定义逻辑，例如：
                # 找到下一个 Waypoint 中 'road_id' 不变的 (直行)
                # 或者强制选择一个固定的方向
                next_wp = next_wps[0] # 这里简化为选择第一个出口
            
            current_wp = next_wp
            
        return path
    
    def set_spectator(self, transform):
        spectator = self.world.get_spectator()
        spectator.set_transform(transform)
        return
    
    def set_ego(self, transform):
        self._ego.actor.set_transform(transform)
        return
    


