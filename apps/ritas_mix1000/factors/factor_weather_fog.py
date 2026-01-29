import numpy as np
from shared.scenarios import Factor
from shared.simulator import *
from shared.data import PointCloud
from shared.prefabs import PlayerVehicle

class FactorWeatherFog(Factor):
    NAME = 'F_WeatherFog'

    def __init__(self, context: CarlaContext,
                 vehicle: PlayerVehicle,
                 fog_level = 1):# 1 2 3
        super().__init__(context)
        self._vehicle = vehicle

        level_map = {
            1: {"name": "I级", "fog_density": 33,"fog_distance": 10},
            2: {"name": "II级", "fog_density": 67,"fog_distance": 5},
            3: {"name": "III级", "fog_density": 100,"fog_distance": 0}
        }
        
        if fog_level in level_map:
            info = level_map[fog_level]
            self._fog_density = info["fog_density"]
            self._fog_distance = info["fog_distance"]
            self._level_name = info["name"]
        else:
            raise ValueError(f"无效的等级: {fog_level}")
    
    def bringup(self) -> None:
        weather = self._context.world.get_weather()
        weather.fog_density = self._fog_density
        weather.fog_distance = self._fog_distance
        self._context.world.set_weather(weather)

        return super().bringup()
