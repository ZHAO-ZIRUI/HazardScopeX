import carla
import random
from typing_extensions import Self

from shared.scenarios import Factor
from shared.define import FactorLevel
from shared.simulator import CarlaContext, CarlaVehicle, CarlaBlueprints, CarlaActor

class FactorCaseStaticObstacle(Factor):
    NAME = 'F_CaseStaticObstacle'

    M_WORLD_LOCATION = {
        'Carla/Maps/Town10HD_Opt': {
            Factor.K_VEHICLE_EGO: 101,
            Factor.K_OBSTACLE: 119,
            Factor.K_VEHICLE_NPC: [93, 53, 56, 107, 59, 58, 94, 91],
        },
        'Carla/Maps/Town03': {
            Factor.K_VEHICLE_EGO: 147,
            Factor.K_OBSTACLE: 191,
            Factor.K_VEHICLE_NPC: [189, 21, 23,185, 1, 2, 184, 102],
        },
    }

    def __init__(
        self,
        context: CarlaContext,
        ego_vehicle: CarlaVehicle,
        level: FactorLevel = FactorLevel.HIGH,
        obstical_bp: carla.ActorBlueprint | CarlaBlueprints | str = CarlaBlueprints.STATIC_PROP_SHOPPINGCART,
        *,
        ignore_factor_ego_control: bool = False,
        obstacle_random_xy: float = 1.0,
        obstacle_count: int = 1,
    ):
        super().__init__(
            context,
            ego_vehicle,
            level=level,
            ignore_factor_ego_control=ignore_factor_ego_control,
            keepalive_after_trigger=10.0,
        )
        self._obstical_bp = obstical_bp
        self._obstacle_random_xy = obstacle_random_xy
        self._obstacle_count = obstacle_count

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

    def get_ego_vehicle_distance_to_obstacle(self) -> float:
        ego_location = self._vehicle_ego.tf_now.location
        obstacle_location = self._factor_actors[self.K_OBSTACLE + str(0)].tf_now.location
        return ego_location.distance(obstacle_location)

    def create_obstical(self) -> None:
        obstacle_tf: carla.Transform | int = self.M_WORLD_LOCATION[self._context.map_name][Factor.K_OBSTACLE]
        if isinstance(obstacle_tf, int):
            obstacle_tf = self._context.spawn_points[obstacle_tf]
        else:
            obstacle_tf = obstacle_tf

        for i in range(self._obstacle_count):
            obstacle_name = self.K_OBSTACLE + str(i)
            obstacle_tf = carla.Transform(
                location=carla.Location(
                    x=obstacle_tf.location.x + random.uniform(-self._obstacle_random_xy, self._obstacle_random_xy),
                    y=obstacle_tf.location.y + random.uniform(-self._obstacle_random_xy, self._obstacle_random_xy),
                    z=obstacle_tf.location.z + 1.0,
                ),
                rotation=obstacle_tf.rotation,
            )
            obstacle = self._context.actors.create_actor(
                bp=self._obstical_bp,
                tf=obstacle_tf,
                name=obstacle_name
            )
            self._factor_actors[obstacle_name] = obstacle
        return self

    def post_create_obstacle(self) -> None:
        for i in range(self._obstacle_count):
            obstacle_name = self.K_OBSTACLE + str(i)
            obstacle: CarlaActor | None = self._factor_actors.get(obstacle_name)
            if obstacle is None or not obstacle.is_alive:
                continue
            obstacle.actor.set_simulate_physics(True)
            obstacle.actor.set_enable_gravity(True)
        if self.post_create_obstacle in self.hook_update:
            self.hook_update.remove(self.post_create_obstacle)
        return self