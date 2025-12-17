import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseHighwayWrongWay(Factor):
    NAME = 'F_CaseHighwayWrongWay'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town04': {
            'ego': 110,
            'act': 268,
            'npc': [108, 113, 114, 117]
        },
    }

    def __init__(
        self, context: CarlaContext, ego: CarlaVehicle, *,
        distance_offset: float = 15.0,
        lateral_offset: float = 1.5,
        act_speed_kmh: float = 30.0,
        act_brake_distance: float = 30.0,
        target_speed_kmh: float = 100.0,
    ):
        super().__init__(context)
        self._ego = ego
        self._act: CarlaVehicle | None = None
        self._distance_offset = distance_offset
        self._lateral_offset = lateral_offset
        self._act_speed_kmh = act_speed_kmh
        self._act_brake_distance = act_brake_distance
        self._act_braking = False
        self._vehicles: list[CarlaVehicle] = []

    @property
    def ego(self) -> CarlaVehicle:
        return self._ego

    @property
    def act(self) -> CarlaVehicle:
        return self._act

    def setup(self) -> None:
        spawn_point_mapping = self.MAP_SPAWN_POINT_MAPPING[self._context.map_name]
        # 设置 ego 位置
        tf_ego = self._context.spawn_points[spawn_point_mapping['ego']]
        self._ego.actor.set_transform(tf_ego)
        self._vehicles.append(self._ego)

        # 计算 act 位置和朝向
        tf_act_spawn = self._context.spawn_points[spawn_point_mapping['act']]
        ego_yaw_rad = np.radians(tf_ego.rotation.yaw)
        
        # 计算act位置：距离偏移 + 横向偏置
        act_location = carla.Location(
            x=tf_act_spawn.location.x - self._distance_offset * np.cos(ego_yaw_rad) + self._lateral_offset * (-np.sin(ego_yaw_rad)),
            y=tf_act_spawn.location.y - self._distance_offset * np.sin(ego_yaw_rad) + self._lateral_offset * np.cos(ego_yaw_rad),
            z=tf_act_spawn.location.z
        )
        
        # act的yaw设置为180度（相对于spawn point的yaw）
        act_yaw = tf_act_spawn.rotation.yaw - 180.0
        act_transform = carla.Transform(
            location=act_location,
            rotation=carla.Rotation(yaw=act_yaw)
        )
        
        self._act = self._context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_TESLA_MODEL3,
            tf=act_transform,
            name='ACT',
        )
        self._act.spawn(self._context.world)
        self._vehicles.append(self._act)
        
        # 开启act的双闪灯（使用RightBlinker + LeftBlinker）
        if self._act.actor is not None and self._act.actor.is_alive:
            combined_light_state = carla.VehicleLightState.RightBlinker | carla.VehicleLightState.LeftBlinker
            self._act.actor.set_light_state(carla.VehicleLightState(combined_light_state))
            self.logger.info('ACT hazard lights enabled (RightBlinker + LeftBlinker)')

        # 创建 npc
        for npc_sp_idx in spawn_point_mapping['npc']:
            npc_tf = self._context.spawn_points[npc_sp_idx]
            npc = self._context.actors.create_vehicle(
                bp=CarlaBlueprints.VEHICLE_MERCEDES_SPRINTER,
                tf=npc_tf,
                name=f'NPC_{npc_sp_idx}',
            )
            npc.spawn(self._context.world, ignore_spawn_failure=True)
            self._vehicles.append(npc)

        self._context.tick()
        self._context.actors.wait_stable()

        # 使用 Traffic Manager 控制车辆直行（act不启动AP，使用手动控制）
        tm = self._context.traffic_manager
        target_speed_kmh = 90.0
        target_speed_ms = target_speed_kmh / 3.6
        for vehicle in self._vehicles:
            if vehicle != self._act:  # act不启动autopilot
                tm.auto_lane_change(vehicle.actor, False)
                vehicle.set_carla_autopilot(enable=True)
                tm.set_desired_speed(vehicle.actor, target_speed_ms)
        
        self.logger.info(f'All vehicles (except ACT) target speed set to {target_speed_kmh:.1f} km/h')
        return super().setup()

    def tick(self) -> None:
        if self._act is None or self._act.actor is None or not self._act.actor.is_alive:
            return super().tick()
        
        # act使用set_target_velocity设置速度，朝向他自身的正方向
        if not self._act_braking:
            # 获取act的朝向
            act_transform = self._act.actor.get_transform()
            act_yaw_rad = np.radians(act_transform.rotation.yaw)
            
            # 计算速度向量（朝向act自身的正方向）
            act_speed_ms = self._act_speed_kmh / 3.6  # 转换为米/秒
            velocity = carla.Vector3D(
                x=act_speed_ms * np.cos(act_yaw_rad),
                y=act_speed_ms * np.sin(act_yaw_rad),
                z=0.0
            )
            self._act.actor.set_target_velocity(velocity)
        
        # 检测ego和act的距离，当距离小于act_brake_distance时，act全力刹车
        if (self._ego.actor is not None and self._ego.actor.is_alive and
            self._act.actor is not None and self._act.actor.is_alive):
            
            ego_location = self._ego.actor.get_location()
            act_location = self._act.actor.get_location()
            distance = ego_location.distance(act_location)
            
            if distance <= self._act_brake_distance:
                # act全力刹车
                if not self._act_braking:
                    self._act_braking = True
                    self.logger.info(f'ACT braking triggered at distance {distance:.2f}m (threshold: {self._act_brake_distance}m)')
                
                # 持续应用全力刹车
                control = carla.VehicleControl(throttle=0.0, brake=1.0, steer=0.0)
                self._act.actor.apply_control(control)
        
        

        return super().tick()

    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        if self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            self._act.set_carla_autopilot(enable=False)
            self._act.destroy()
        return super().teardown()