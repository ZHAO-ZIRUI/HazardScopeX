from shared.scenarios import Factor
from shared.simulator import *


class FactorWeatherSuddenRain(Factor):
    NAME = 'F_WeatherSuddenRain'

    def __init__(self, context: CarlaContext, delay_seconds: float = 3.0):
        super().__init__(context)
        self._delay_ticks = int(delay_seconds * context.fps)
        self._current_ticks = 0
        self._rain_applied = False

    def setup(self) -> None:
        return super().setup()

    def tick(self) -> None:
        if not self._rain_applied and self._current_ticks >= self._delay_ticks:
            self._rain_applied = True
            weather = self._context.world.get_weather()
            weather.precipitation = 100
            weather.precipitation_deposits = 5
            weather.wetness = 5
            self._context.world.set_weather(weather)

        self._current_ticks += 1