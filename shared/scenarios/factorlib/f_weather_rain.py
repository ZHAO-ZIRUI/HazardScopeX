from typing_extensions import Self

from shared.scenarios import Factor
from shared.define import FactorLevel
from shared.simulator import CarlaContext, CarlaVehicle

class FactorWeatherRain(Factor):
    NAME = 'F_WeatherRain'

    # (precipitation, precipitation_deposits, wetness, cloudiness, wind_intensity, fog_density, fog_distance, fog_falloff, scattering_intensity)
    MAPPING_WPARAM_LEVEL = {
        FactorLevel.NONE: (0.0, 0.0, 0.0, 80.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        FactorLevel.LOW: (15.0, 20.0, 25.0, 80.0, 15.0, 4.0, 100.0, 0.8, 0.2),
        FactorLevel.MEDIUM: (55.0, 50.0, 55.0, 100.0, 30.0, 10.0, 100.0, 1.5, 0.5),
        FactorLevel.HIGH: (90.0, 80.0, 85.0, 100.0, 60.0, 16.0, 70.0, 2.2, 0.8),
    }

    def __init__(
        self,
        context: CarlaContext,
        ego_vehicle: CarlaVehicle,
        level: FactorLevel,
    ):
        super().__init__(
            context, 
            ego_vehicle, 
            ignore_factor_ego_control=True,
            keepalive_after_triggered_seconds=0,
        )
        self._level = level

    def __post_init__(self) -> Self:
        self.hook_bringup.append(self.set_weather)
        return super().__post_init__()

    def set_weather(self) -> None:
        params = self.MAPPING_WPARAM_LEVEL[self._level]
        (
            precipitation,
            precipitation_deposits,
            wetness,
            cloudiness,
            wind_intensity,
            fog_density,
            fog_distance,
            fog_falloff,
            scattering_intensity,
        ) = params

        weather = self._context.world.get_weather()
        weather.precipitation = precipitation
        weather.precipitation_deposits = precipitation_deposits
        weather.wetness = wetness
        weather.cloudiness = cloudiness
        weather.wind_intensity = wind_intensity
        weather.fog_density = fog_density
        weather.fog_distance = fog_distance
        weather.fog_falloff = fog_falloff
        weather.scattering_intensity = scattering_intensity
        self._context.world.set_weather(weather)