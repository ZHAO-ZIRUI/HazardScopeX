import numpy as np
from shared.scenarios import Factor
from shared.simulator import *
from shared.data import PointCloud


class FactorWeatherMediumFog(Factor):
    NAME = 'F_WeatherMediumFog'

    def __init__(self, context: CarlaContext, lidar: CarlaSensor):
        super().__init__(context)
        self._lidar = lidar
    
    def setup(self) -> None:
        weather = self._context.world.get_weather()
        weather.fog_density = 30
        weather.fog_distance = 0
        self._context.world.set_weather(weather)

        self._lidar.hook_sensor_data_recv.append(self.add_gaussian_noise)
        return super().setup()

    def add_gaussian_noise(self, point_cloud: PointCloud) -> PointCloud:
        noise = np.random.normal(0, 0.02, size=(point_cloud.count, 3))
        point_cloud._raw[:, :3] += noise
        return point_cloud