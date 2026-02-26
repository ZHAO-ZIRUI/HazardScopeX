import carla
from typing_extensions import Self

from shared.scenarios import Factor
from shared.define import FactorLevel
from shared.simulator import CarlaContext, CarlaVehicle, CarlaBlueprints, CarlaActor

class FactorCaseVehicleDropObstacle(Factor):
    NAME = 'F_CaseVehicleDropObstacle'

    M_WORLD_LOCATION = {
        'Carla/Maps/Town10HD_Opt': {
            Factor.K_VEHICLE_EGO: 93,
            Factor.K_VEHICLE_ACT: 53,
            Factor.K_OBSTACLE: 107,
            Factor.K_VEHICLE_NPC: [101, 55, 57, 119, 59],
        },
        'Carla/Maps/Town03': {
            Factor.K_VEHICLE_EGO: 106,
            Factor.K_VEHICLE_ACT: 149,
            Factor.K_OBSTACLE: 121,
            Factor.K_VEHICLE_NPC: [248, 247, 120, 146, 105],
        },
    }

    def __init__(
        self,
        context: CarlaContext,
        ego_vehicle: CarlaVehicle,
        level: FactorLevel = FactorLevel.HIGH,
        obstical_bp: carla.ActorBlueprint | CarlaBlueprints | str = CarlaBlueprints.STATIC_PROP_BOX01,
        obstical_create_offset_xy: float = 2.0,
        obstical_create_offset_z: float = 1.5,
        obstical_create_rotation: carla.Rotation = carla.Rotation(yaw=0.0, pitch=0.0, roll=0.0),
        *,
        ignore_factor_ego_control: bool = False,
    ):
        super().__init__(
            context,
            ego_vehicle,
            level=level,
            ignore_factor_ego_control=ignore_factor_ego_control,
            keepalive_after_trigger=5.0,
        )
        self._act: CarlaVehicle | None = None
        self._obstical_bp = obstical_bp
        self._obstical_create_offset_xy = obstical_create_offset_xy
        self._obstical_create_offset_z = obstical_create_offset_z
        self._obstical_create_rotation = obstical_create_rotation
        self._is_obstacle_created = False

    def __post_init__(self) -> Self:
        self.hook_bringup.append(self.move_ego_vehicle_to_init_tf)
        self.hook_bringup.append(self.create_npc_vehicles)
        self.hook_bringup.append(self.create_act_vehicle)
        self.hook_bringup.append(self.spawn_all_factor_actors)
        self.hook_bringup.append(self.apply_npc_vehicles_carla_autopilot)
        self.hook_bringup.append(self.apply_act_vehicle_carla_autopilot)

        self.hook_update.append(self.update_npc_vehicles_auto_lights)
        self.hook_update.append(self.create_obstacle_on_act_reach_obstacle_spawn_point)
        self.hook_update.append(self.keepalive_after_triggered)
        return super().__post_init__()

    def create_act_vehicle(self) -> None:
        self._act = self._context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_MERCEDES_SPRINTER,
            tf=self._context.spawn_points[self.M_WORLD_LOCATION[self._context.map_name][Factor.K_VEHICLE_ACT]],
            name=self.K_VEHICLE_ACT,
        )
        self._factor_actors[self.K_VEHICLE_ACT] = self._act

    def apply_act_vehicle_carla_autopilot(self) -> None:
        self._act.set_carla_autopilot(enable=True)
        self._context.traffic.auto_lane_change(self._act.actor, False)

    def create_obstacle_on_act_reach_obstacle_spawn_point(self) -> None:
        if self._is_obstacle_created:
            return

        obstacle_tf = self._context.spawn_points[self.M_WORLD_LOCATION[self._context.map_name][Factor.K_OBSTACLE]]

        obstacle_loc_xy= carla.Location(
            x=obstacle_tf.location.x,
            y=obstacle_tf.location.y,
            z=0
        )

        act_location_xy = carla.Location(
            x=self._act.actor.get_location().x,
            y=self._act.actor.get_location().y,
            z=0
        )

        obstacle_create_offset = self._act.actor.bounding_box.extent.x + self._obstical_create_offset_xy
        act_heading_vector = self._act.actor.get_transform().get_forward_vector()

        obstacle_create_tf = carla.Transform(
            location=carla.Location(
                x=act_location_xy.x - obstacle_create_offset * act_heading_vector.x,
                y=act_location_xy.y - obstacle_create_offset * act_heading_vector.y,
                z=obstacle_tf.location.z + self._obstical_create_offset_z,
            ),
            rotation=self._obstical_create_rotation,
        )

        if act_location_xy.distance(obstacle_loc_xy) < 0.5:
            self.logger.info(f'Creating obstacle at {obstacle_tf.location}')
            obstacle = self._context.actors.create_actor(
                bp=self._obstical_bp,
                tf=obstacle_create_tf,
                name=self.K_OBSTACLE,
            )
            obstacle.spawn(no_tick=True)
            self._is_obstacle_created = True
            self._factor_actors[self.K_OBSTACLE] = obstacle

            self.hook_update.remove(self.create_obstacle_on_act_reach_obstacle_spawn_point)
            self.hook_update.append(self.after_create_obstacle)

    def after_create_obstacle(self) -> None:
        if not self._is_obstacle_created:
            return

        obstacle: CarlaActor = self._factor_actors[self.K_OBSTACLE]

        if not obstacle.is_alive:
            return

        obstacle_velocity = self._act.actor.get_velocity()
        obstacle.actor.set_simulate_physics(True)
        obstacle.actor.set_target_velocity(obstacle_velocity * 0.8)

        # 移除自身, 只执行一次
        self.hook_update.remove(self.after_create_obstacle)
        self.stage = self.FactorStage.TRIGGERED