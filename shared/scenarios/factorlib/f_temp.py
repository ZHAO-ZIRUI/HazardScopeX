from typing_extensions import Self

from shared.scenarios import Factor
from shared.define import FactorLevel
from shared.simulator import CarlaContext, CarlaVehicle

class FactorTemp(Factor):
    NAME = 'F_Temp'

    'Carla/Maps/Town10HD_Opt': {
            Factor.K_EGO: 93,
            Factor.K_ACT: 53,
            Factor.K_OBSTACLE: 107,
            Factor.K_NPC_VEHICLE: [101, 55, 57, 119, 59]
        },


    def __init__(
        self,
        context: CarlaContext,
        ego_vehicle: CarlaVehicle,
    ):
        super().__init__(
            context, 
            ego_vehicle, 
            ignore_factor_ego_control=True,
            keepalive_after_triggered_seconds=0,
        )

    def __post_init__(self) -> Self:
        self.hook_bringup.append(self.move_ego_vehicle_to_init_tf)
        self.hook_bringup.append(self.create_npc_vehicles)
        self.hook_bringup.append(self.spawn_all_factor_actors)
        self.hook_bringup.append(self.apply_npc_vehicles_carla_autopilot)

        self.hook_update.append(self.update_npc_vehicles_auto_lights)
        return super().__post_init__()