from typing_extensions import Self
from collections import namedtuple

from shared.scenarios import Factor
from shared.define import FactorLevel
from shared.simulator import CarlaContext, CarlaVehicle

FOG_CTRL_PARAMS = namedtuple(
    'FogCtrlParams',
    ['fog_density', 'fog_distance', 'fog_falloff', 'scattering_intensity'],
)

class FactorWeatherFog(Factor):
    NAME = 'F_WeatherFog'

    M_LEVEL_VALUE = {
        FactorLevel.NONE: FOG_CTRL_PARAMS(0.0, 0.0, 0.0, 0.0),
        FactorLevel.LOW: FOG_CTRL_PARAMS(30.0, 80.0, 0.2, 0.2),
        FactorLevel.MEDIUM: FOG_CTRL_PARAMS(60.0, 40.0, 0.3, 0.6),
        FactorLevel.HIGH: FOG_CTRL_PARAMS(100.0, 10.0, 0.4, 0.9),
    }

    def __init__(
        self,
        context: CarlaContext,
        ego_vehicle: CarlaVehicle,
        level: FactorLevel,
        *,
        ignore_factor_ego_control: bool = False,
        keepalive_after_trigger: float = 0.0,
    ):
        super().__init__(
            context,
            ego_vehicle,
            level,
            ignore_factor_ego_control=ignore_factor_ego_control,
            keepalive_after_trigger=keepalive_after_trigger,
        )

    def __post_init__(self) -> Self:
        self.hook_bringup.append(self.set_weather)
        return super().__post_init__()

    def set_weather(self) -> None:
        params: FOG_CTRL_PARAMS = self.M_LEVEL_VALUE[self._level]
        weather = self._context.world.get_weather()
        weather.fog_density = params.fog_density
        weather.fog_distance = params.fog_distance
        weather.fog_falloff = params.fog_falloff
        weather.scattering_intensity = params.scattering_intensity
        self._context.world.set_weather(weather)