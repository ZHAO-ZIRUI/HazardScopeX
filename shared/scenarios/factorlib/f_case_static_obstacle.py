import carla
from typing_extensions import Self

from shared.scenarios import Factor
from shared.simulator import CarlaContext, CarlaVehicle, CarlaBlueprints, CarlaActor

class FactorStaticObstacle(Factor):
    NAME = 'F_StaticObstacle'

    MAPPING_WORLD_LOCATION = {
        'Carla/Maps/Town10HD_Opt': {
            Factor.K_EGO: 118,
            Factor.K_OBSTACLE: carla.Transform(
                location=carla.Location(x=-2.5, y=64.7, z=1.1),
                rotation=carla.Rotation(yaw=90.0, pitch=0.0, roll=0.0),
            ),
            Factor.K_NPC_VEHICLE: [124, 30, 31, 33]
        },
        'Carla/Maps/Town03': {
            Factor.K_EGO: 146,
            Factor.K_OBSTACLE: 247,
            Factor.K_NPC_VEHICLE: [248, 121, 149]
        },
    }

    def __init__(
        self,
        context: CarlaContext,
        ego_vehicle: CarlaVehicle,
        obstical_bp: carla.ActorBlueprint | CarlaBlueprints | str = CarlaBlueprints.STATIC_PROP_SHOPPINGCART,
        *,
        dart_out_distance: float = 15.0,
        dart_out_speed_ms: float = 1,
        ignore_factor_ego_control: bool = False,
        keepalive_after_triggered_seconds: int = 10,
    ):
        super().__init__(context, ego_vehicle, ignore_factor_ego_control=ignore_factor_ego_control, keepalive_after_triggered_seconds=keepalive_after_triggered_seconds)
        self._obstical_bp = obstical_bp

    def __post_init__(self) -> Self:
        self.hook_bringup.append(self.move_ego_vehicle_to_init_tf)
        self.hook_bringup.append(self.create_obstical)
        self.hook_bringup.append(self.create_npc_vehicles)
        self.hook_bringup.append(self.spawn_all_factor_actors)
        self.hook_bringup.append(self.apply_npc_vehicles_carla_autopilot)

        self.hook_update.append(self.update_npc_vehicles_auto_lights)
        self.hook_update.append(self.keepalive_after_triggered)
        self.hook_update.append(self.post_create_obstacle)
        return super().__post_init__()

    def create_obstical(self) -> None:
        obstacle_tf: carla.Transform | int = self.MAPPING_WORLD_LOCATION[self._context.map_name][Factor.K_OBSTACLE]
        if isinstance(obstacle_tf, int):
            obstacle_tf = self._context.spawn_points[obstacle_tf]
        else:
            obstacle_tf = obstacle_tf

        obstacle_tf = carla.Transform(
            location=carla.Location(x=obstacle_tf.location.x, y=obstacle_tf.location.y - 1.5, z=obstacle_tf.location.z + 1.0),
            rotation=obstacle_tf.rotation,
        )
        obstacle = self._context.actors.create_actor(
            bp=self._obstical_bp,
            tf=obstacle_tf,
            name=self.K_OBSTACLE,
        )
        self._factor_actors[self.K_OBSTACLE] = obstacle
        return self

    def post_create_obstacle(self) -> None:
        obstacle: CarlaActor = self._factor_actors[self.K_OBSTACLE]
        obstacle.actor.set_simulate_physics(True)
        obstacle.actor.set_enable_gravity(True)
        self._stage = self.FactorStage.TRIGGERED
        self.hook_update.remove(self.post_create_obstacle)
        return self