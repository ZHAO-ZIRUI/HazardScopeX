import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorEnvNight(Factor):
    NAME = 'F_EnvNight'

    def __init__(self, context: CarlaContext):
        super().__init__(context)

    def setup(self) -> None:
        self._context.world.set_weather(carla.WeatherParameters.ClearNoon)
        # 对太阳角度进行调整
        weather = self._context.world.get_weather()
        weather.sun_azimuth_angle = -1.0 * weather.sun_azimuth_angle
        weather.sun_altitude_angle = -1.0 * weather.sun_altitude_angle
        self._context.world.set_weather(weather)
        return super().setup()
