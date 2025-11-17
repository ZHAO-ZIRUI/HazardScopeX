import random
import carla

from shared.scenarios import Factor
from shared.simulator import *


class FactorSensorCalibError(Factor):
    NAME = 'F_SensorCalibError'

    def __init__(
        self, 
        context: 'CarlaContext', 
        sensor: CarlaSensor, 
        *, 
        location_offset: float =  0.005, 
        rotation_offset: float =  2.0):
        super().__init__(context)
        self._sensor = sensor
        self._location_offset = location_offset
        self._rotation_offset = rotation_offset
    
    def setup(self) -> None:
        tf_init = self._sensor.tf_init
        tf_new = carla.Transform(
            location=carla.Location(
                x=tf_init.location.x + random.uniform(-1, 1) * self._location_offset, 
                y=tf_init.location.y + random.uniform(-1, 1) * self._location_offset, 
                z=tf_init.location.z + random.uniform(-1, 1) * self._location_offset),
            rotation=carla.Rotation(
                yaw=tf_init.rotation.yaw + random.uniform(-1, 1) * self._rotation_offset, 
                pitch=tf_init.rotation.pitch + random.uniform(-1, 1) * self._rotation_offset, 
                roll=tf_init.rotation.roll + random.uniform(-1, 1) * self._rotation_offset),
        )

        self._sensor.actor.set_transform(tf_new)
        return super().setup()