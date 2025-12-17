from shared.scenarios import Factor
from shared.simulator import *


class FactorWeatherCloudiness(Factor):
    NAME = 'F_WeatherCloudiness'

    def __init__(self, context: CarlaContext):
        super().__init__(context)

    def setup(self) -> None:
        weather = self._context.world.get_weather()
        weather.cloudiness = 100
        self._context.world.set_weather(weather)
        return super().setup()
