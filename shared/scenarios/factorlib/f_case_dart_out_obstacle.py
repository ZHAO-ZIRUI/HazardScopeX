import carla
from typing_extensions import Self

from shared.scenarios import Factor
from shared.simulator import CarlaContext, CarlaVehicle, CarlaBlueprints, CarlaActor

class FactorCaseDartOutObstacle(Factor):
    NAME = 'F_CaseDartOutObstacle'

    MAPPING_WORLD_LOCATION = {
        'Carla/Maps/Town10HD_Opt': {
            Factor.K_EGO: 118,
            Factor.K_ACT: 118,
            Factor.K_OBSTACLE: carla.Transform(
                location=carla.Location(x=0.5, y=62, z=1.1),
                rotation=carla.Rotation(yaw=0.0, pitch=0.0, roll=0.0),
            ),
            Factor.K_NPC_VEHICLE: [124, 30, 31, 33]
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
        keepalive_after_triggered_seconds: int = 5,
    ):
        super().__init__(context, ego_vehicle, ignore_factor_ego_control=ignore_factor_ego_control, keepalive_after_triggered_seconds=keepalive_after_triggered_seconds)
        self._act: CarlaVehicle | None = None
        self._obstical_bp = obstical_bp
        self._is_obstacle_created = False
        self._dart_out_distance = dart_out_distance
        self._dart_out_speed_ms = dart_out_speed_ms

    def __post_init__(self) -> Self:
        self.hook_bringup.append(self.move_ego_vehicle_to_init_tf)
        self.hook_bringup.append(self.create_obstical)
        self.hook_bringup.append(self.create_npc_vehicles)
        self.hook_bringup.append(self.spawn_all_factor_actors)
        self.hook_bringup.append(self.apply_npc_vehicles_carla_autopilot)

        self.hook_update.append(self.update_npc_vehicles_auto_lights)
        self.hook_update.append(self.trigger_obstacle_dart_out)
        self.hook_update.append(self.keepalive_after_triggered)
        self.hook_update.append(self.post_trigger_obstacle_dart_out)
        return super().__post_init__()

    def create_obstical(self) -> None:
        obstacle_tf: carla.Transform = self.MAPPING_WORLD_LOCATION[self._context.map_name][Factor.K_OBSTACLE]
        obstacle = self._context.actors.create_actor(
            bp=self._obstical_bp,
            tf=obstacle_tf,
            name=self.K_OBSTACLE,
        )
        self._factor_actors[self.K_OBSTACLE] = obstacle
        self._is_obstacle_created = True

    def trigger_obstacle_dart_out(self) -> None:
        if not self._is_obstacle_created:
            return

        obstacle: CarlaActor = self._factor_actors[self.K_OBSTACLE]
        if not obstacle.is_alive:
            return

        obstacle.actor.set_simulate_physics(True)
        obstacle.actor.set_enable_gravity(False)
        # 计算自车与目标对象的相对距离
        ego_location = self._vehicle_ego.tf_now.location
        obs_location = obstacle.tf_now.location
        relative_distance = ego_location.distance(obs_location)
        if relative_distance > self._dart_out_distance:
            return

        # 触发
        obstacle_fwd = obstacle.tf_now.get_right_vector().make_unit_vector()
        obstacle_velocity = carla.Vector3D(
            x=self._dart_out_speed_ms * obstacle_fwd.x ,
            y=self._dart_out_speed_ms * obstacle_fwd.y,
            z=0.0,
        )
        print(obstacle_velocity)
        # obstacle.actor.set_simulate_physics(False)
        obstacle.actor.set_enable_gravity(False)
        obstacle.actor.set_target_velocity(obstacle_velocity)

        self.logger.info(f'Trigger obstacle dart out, speed: {self._dart_out_speed_ms} m/s')
        self._stage = self.FactorStage.TRIGGERED
        self.hook_update.remove(self.trigger_obstacle_dart_out)

    def post_trigger_obstacle_dart_out(self) -> None:
        if not self._is_obstacle_created:
            return
        obstacle: CarlaActor = self._factor_actors[self.K_OBSTACLE]
        if not obstacle.is_alive:
            return
        if not self._stage != self.FactorStage.TRIGGERED:
            return
        if self._keepalive_begin_frames == 0:
            return
        if self._count_update_frames - self._keepalive_begin_frames <= 80:
            return
        obstacle.actor.set_enable_gravity(True)