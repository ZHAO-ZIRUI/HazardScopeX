from typing_extensions import Self

from shared.scenarios import Factor
from shared.define import FactorLevel
from shared.simulator import CarlaContext, CarlaVehicle

class FactorWeatherFog(Factor):
    NAME = 'F_WeatherFog'

    # (fog_density, fog_distance, fog_falloff, scattering_intensity)
    MAPPING_WPARAM_LEVEL = {
        FactorLevel.NONE: (0.0, 0.0, 0.0, 0.0),
        FactorLevel.LOW: (30.0, 80.0, 1.0, 0.2),
        FactorLevel.MEDIUM: (60.0, 40.0, 2.0, 0.6),
        FactorLevel.HIGH: (100.0, 10.0, 3.0, 0.9),
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
            fog_density,
            fog_distance,
            fog_falloff,
            scattering_intensity,
        ) = params

        weather = self._context.world.get_weather()
        weather.fog_density = fog_density
        weather.fog_distance = fog_distance
        weather.fog_falloff = fog_falloff
        weather.scattering_intensity = scattering_intensity
        self._context.world.set_weather(weather)