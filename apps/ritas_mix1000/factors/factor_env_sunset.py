import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorEnvSunset(Factor):
    NAME = 'F_EnvSunset'

    def __init__(self, context: CarlaContext):
        super().__init__(context)

    def setup(self) -> None:
        self._context.world.set_weather(carla.WeatherParameters.ClearSunset)
        return super().setup()
