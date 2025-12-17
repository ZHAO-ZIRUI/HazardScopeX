import random
from shared.scenarios import Factor
from shared.simulator import *
from shared.data import SimulatorOutput


class FactorSensorHeavyLost(Factor):
    NAME = 'F_SensorHeavyLost'

    def __init__(self, context: 'CarlaContext', sensor: CarlaSensor, loss_threshold: float = 0.9):
        super().__init__(context)
        self._sensor = sensor
        self._last_data: SimulatorOutput | None = None
        self._loss_threshold = loss_threshold
    
    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def on_sensor_data_recv(self, data: SimulatorOutput) -> SimulatorOutput:
        if random.random() < self._loss_threshold:
            return self._last_data
        else:
            self._last_data = data
            return data