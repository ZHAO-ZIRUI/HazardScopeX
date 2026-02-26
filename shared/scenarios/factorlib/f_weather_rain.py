from typing_extensions import Self
from collections import namedtuple

from shared.scenarios import Factor
from shared.define import FactorLevel
from shared.simulator import CarlaContext, CarlaVehicle

RAIN_CTRL_PARAMS = namedtuple(
    'RainCtrlParams',
    [
        'precipitation',
        'precipitation_deposits',
        'wetness',
        'cloudiness',
        'wind_intensity',
        'fog_density',
        'fog_distance',
        'fog_falloff',
        'scattering_intensity',
    ],
)


class FactorWeatherRain(Factor):
    NAME = 'F_WeatherRain'

    M_LEVEL_VALUE = {
        FactorLevel.NONE: RAIN_CTRL_PARAMS(0.0, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        FactorLevel.LOW: RAIN_CTRL_PARAMS(45.0, 30.0, 55.0, 60.0, 15.0, 4.0, 100.0, 0.2, 0.2),
        FactorLevel.MEDIUM: RAIN_CTRL_PARAMS(75.0, 60.0, 85.0, 100.0, 30.0, 10.0, 100.0, 0.3, 0.5),
        FactorLevel.HIGH: RAIN_CTRL_PARAMS(90.0, 100.0, 100.0, 100.0, 60.0, 16.0, 70.0, 0.4, 0.8),
    }

    def __init__(
        self,
        context: CarlaContext,
        ego_vehicle: CarlaVehicle,
        level: FactorLevel,
        *,
        ignore_factor_ego_control: bool = False,
        ignore_fog_params: bool = True,
        keepalive_after_trigger: float = 0.0,
    ):
        super().__init__(
            context,
            ego_vehicle,
            level,
            ignore_factor_ego_control=ignore_factor_ego_control,
            keepalive_after_trigger=keepalive_after_trigger,
        )
        self._flag_ignore_fog_params = ignore_fog_params

    def __post_init__(self) -> Self:
        self.hook_bringup.append(self.set_weather)
        return super().__post_init__()

    def set_weather(self) -> None:
        params: RAIN_CTRL_PARAMS = self.M_LEVEL_VALUE[self._level]

        weather = self._context.world.get_weather()
        weather.precipitation = params.precipitation
        weather.precipitation_deposits = params.precipitation_deposits
        weather.wetness = params.wetness
        weather.cloudiness = params.cloudiness
        weather.wind_intensity = params.wind_intensity
        if not self._flag_ignore_fog_params:
            weather.fog_density = params.fog_density
            weather.fog_distance = params.fog_distance
            weather.fog_falloff = params.fog_falloff
        weather.scattering_intensity = params.scattering_intensity
        self._context.world.set_weather(weather)