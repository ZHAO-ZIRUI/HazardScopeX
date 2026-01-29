import carla
import numpy as np
from shared.scenarios import Factor
from shared.simulator import *
from shared.prefabs import PlayerVehicle

class FactorWeatherDustStorm(Factor):
    NAME = 'F_WeatherDustStorm'

    def __init__(self, context: CarlaContext,
                 ego_vehicle: PlayerVehicle,
                 level = 1):# 1 2 3
        super().__init__(context, ego_vehicle)
        self._vehicle = ego_vehicle

        level_map = {
            1: {"name": "I级", "wind_intensity": 33,"fog_density": 10,"dust_storm": 33},
            2: {"name": "II级", "wind_intensity": 67,"fog_density": 20,"dust_storm": 67},
            3: {"name": "III级", "wind_intensity": 100,"fog_density": 30,"dust_storm": 100}
        }
        
        if level in level_map:
            info = level_map[level]
            self._wind_intensity = info["wind_intensity"]
            self._fog_density = info["fog_density"]
            self._dust_storm = info["dust_storm"]
            self._level_name = info["name"]
        else:
            raise ValueError(f"无效的等级: {level}")
    
    def bringup(self) -> None:
        # weather = self._context.world.get_weather()
        weather = carla.WeatherParameters()
        weather.sun_altitude_angle = 45
        weather.wind_intensity = self._wind_intensity
        weather.fog_density = self._fog_density
        weather.mie_scattering_scale = self._fog_density
        weather.dust_storm = self._dust_storm
        self._context.world.set_weather(weather)

        return super().bringup()
