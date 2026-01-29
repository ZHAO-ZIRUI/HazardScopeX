from shared.scenarios import Factor
from shared.simulator import *
from shared.prefabs import PlayerVehicle

class FactorWeatherRain(Factor):
    NAME = 'F_WeatherRain'

    def __init__(self, 
                 context: CarlaContext,
                 vehicle: PlayerVehicle,
                 rain_level = 1):# 1 2 3
        self._vehicle = vehicle

        level_map = {
            1: {"name": "I级", "precipitation": 33,"precipitation_deposits": 33,"wetness": 33,"cloudiness": 33},
            2: {"name": "II级", "precipitation": 67,"precipitation_deposits": 67,"wetness": 67,"cloudiness": 67},
            3: {"name": "III级", "precipitation": 100,"precipitation_deposits": 100,"wetness": 100,"cloudiness": 100}
        }
        
        if rain_level in level_map:
            info = level_map[rain_level]
            self._precipitation = info["precipitation"]
            self._precipitation_deposits = info["precipitation_deposits"]
            self._wetness = info["wetness"]
            self._cloudiness = info["cloudiness"]
            self._level_name = info["name"]
        else:
            raise ValueError(f"无效的等级: {rain_level}")
        super().__init__(context)

    def bringup(self) -> None:
        weather = self._context.world.get_weather()
        weather.precipitation = self._precipitation
        weather.precipitation_deposits = self._precipitation_deposits
        weather.wetness = self._wetness
        weather.cloudiness = self._cloudiness
        self._context.world.set_weather(weather)
        return super().bringup()
