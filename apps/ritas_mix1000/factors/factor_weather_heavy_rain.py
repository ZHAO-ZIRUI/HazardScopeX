from shared.scenarios import Factor
from shared.simulator import *


class FactorWeatherHeavyRain(Factor):
    NAME = 'F_WeatherHeavyRain'

    def __init__(self, context: CarlaContext):
        super().__init__(context)

    def setup(self) -> None:
        weather = self._context.world.get_weather()
        weather.precipitation = 70
        weather.precipitation_deposits = 10
        weather.wetness = 10
        self._context.world.set_weather(weather)
        return super().setup()
