import numpy as np
import random
import carla
from PIL import Image
import os
from collections import deque
from shared.scenarios import Factor
from shared.simulator import *
from shared.data import Image

class FactorCameraColorCast(Factor):
    NAME = 'F_CameraColorCast'

    def __init__(
        self, 
        context: CarlaContext, 
        sensor: CarlaSensor,
        # *,
    ):
        super().__init__(context)
        self._sensor = sensor

    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def on_sensor_data_recv(self, data: Image) -> Image:

        # data._raw = 
        
        return data