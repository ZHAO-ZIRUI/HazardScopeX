import numpy as np
import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorCaseLongCargoMany(Factor):
    NAME = 'F_CaseLongCargoMany'

    MAP_SPAWN_POINT_MAPPING = {
        'Carla/Maps/Town10HD_Opt': {
            'ego': 93,
            'act': 53,
            'npc': [101, 55, 57, 119, 59]
        },
    }

    def __init__(self, context: CarlaContext, ego: CarlaVehicle, *, distance_offset: float = 10.0, cargo_offset_behind: float = 0.1, cargo_count: int = 20, cargo_y_offset: float = 0.4, cargo_z_offset: float = 0.3):
        super().__init__(context)
        self._ego = ego
        self._act: CarlaVehicle | None = None
        self._distance_offset = distance_offset
        self._cargo_offset_behind = cargo_offset_behind
        self._cargo_count = cargo_count
        self._cargo_y_offset = cargo_y_offset
        self._cargo_z_offset = cargo_z_offset
        self._cargo_list: list[carla.Actor] = []
        self._cargo_bp: carla.ActorBlueprint | None = None
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

        # 计算 act 位置
        tf_act = self._context.spawn_points[spawn_point_mapping['act']]
        ego_yaw_rad = np.radians(tf_ego.rotation.yaw)
        tf_act.location.x -= self._distance_offset * np.cos(ego_yaw_rad)
        tf_act.location.y -= self._distance_offset * np.sin(ego_yaw_rad)
        self._act = self._context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_MERCEDES_SPRINTER,
            tf=tf_act,
            name='ACT',
        )
        self._act.spawn(self._context.world)
        self._vehicles.append(self._act)

        self._context.tick()

        # 准备cargo blueprint（使用原生CARLA API）
        blueprint_library = self._context.world.get_blueprint_library()
        self._cargo_bp = blueprint_library.find('static.prop.mesh')
        self._cargo_bp.set_attribute('mesh_path', '/Game/Carla/Static/Pole/SM_RoadSigns01.SM_RoadSigns01')
        self._cargo_bp.set_attribute('scale', '2.0')

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

        # 使用 Traffic Manager 控制车辆直行
        tm = self._context.traffic_manager
        for vehicle in self._vehicles:
            tm.auto_lane_change(vehicle.actor, False)
            vehicle.set_carla_autopilot(enable=True)
        
        return super().setup()

    def tick(self) -> None:
        # 每帧销毁旧cargo并spawn新的cargo（使用原生CARLA API）
        if (self._act is not None and self._act.actor is not None and self._act.actor.is_alive and
            self._cargo_bp is not None):
            
            # 销毁所有旧的cargo
            for cargo in self._cargo_list:
                if cargo is not None and cargo.is_alive:
                    cargo.destroy()
            self._cargo_list.clear()
            
            # 计算act车辆后方的基准位置
            act_transform = self._act.actor.get_transform()
            act_bbox = self._act.actor.bounding_box
            
            # 计算后方位置：车辆中心 - (bounding box长度 + 偏移) * 车辆朝向
            act_yaw_rad = np.radians(act_transform.rotation.yaw)
            rear_offset = act_bbox.extent.x + self._cargo_offset_behind
            
            base_cargo_location = carla.Location(
                x=act_transform.location.x - rear_offset * np.cos(act_yaw_rad),
                y=act_transform.location.y - rear_offset * np.sin(act_yaw_rad),
                z=act_transform.location.z + 1.0
            )
            
            cargo_rotation = carla.Rotation(yaw=act_transform.rotation.yaw, pitch=90.0, roll=0.0)
            
            # 生成多个cargo，每个在Y和Z上有偏移
            grid_size = int(np.sqrt(self._cargo_count))
            for i in range(self._cargo_count):
                # 计算Y和Z偏移
                # Y方向偏移：横向（左右）
                y_offset_index = (i % grid_size) - (grid_size - 1) / 2
                # Z方向偏移：高度（上下）
                z_offset_index = (i // grid_size) - (grid_size - 1) / 2
                
                # 将Y偏移转换为世界坐标系（横向，left方向）：(-sin(yaw), cos(yaw))
                y_offset_x = y_offset_index * self._cargo_y_offset * (-np.sin(act_yaw_rad))
                y_offset_y = y_offset_index * self._cargo_y_offset * np.cos(act_yaw_rad)
                
                # Z方向偏移（高度）
                z_offset = z_offset_index * self._cargo_z_offset
                
                cargo_location = carla.Location(
                    x=base_cargo_location.x + y_offset_x,
                    y=base_cargo_location.y + y_offset_y,
                    z=base_cargo_location.z + z_offset
                )
                
                cargo_transform = carla.Transform(
                    location=cargo_location,
                    rotation=cargo_rotation
                )
                
                # 使用原生CARLA API spawn新的cargo
                cargo = self._context.world.spawn_actor(
                    self._cargo_bp,
                    cargo_transform
                )
                # 禁用物理模拟
                cargo.set_simulate_physics(False)
                self._cargo_list.append(cargo)
        
        return super().tick()

    def teardown(self) -> None:
        # 禁用 Traffic Manager 控制的 autopilot
        if self._ego.actor is not None and self._ego.actor.is_alive:
            self._ego.set_carla_autopilot(enable=False)
        if self._act is not None and self._act.actor is not None and self._act.actor.is_alive:
            self._act.set_carla_autopilot(enable=False)
            self._act.destroy()
        
        # 销毁所有cargo
        for cargo in self._cargo_list:
            if cargo is not None and cargo.is_alive:
                cargo.destroy()
        self._cargo_list.clear()
        
        return super().teardown()