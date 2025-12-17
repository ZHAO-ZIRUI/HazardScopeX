from shared.scenarios import Factor
from shared.simulator import *


class FactorRoadFlodding(Factor):
    NAME = 'F_RoadFlodding'

    def __init__(self, context: CarlaContext):
        super().__init__(context)

    def setup(self) -> None:
        weather = self._context.world.get_weather()
        weather.precipitation_deposits = 100
        weather.wetness = 100
        weather.fog_density = 10
        weather.fog_distance = 10
        weather.fog_falloff = 4
        self._context.world.set_weather(weather)
        return super().setup()
