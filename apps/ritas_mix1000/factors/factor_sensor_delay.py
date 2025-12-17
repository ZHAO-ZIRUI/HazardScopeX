from collections import deque

from shared.scenarios import Factor
from shared.simulator import *
from shared.data import SimulatorOutput


class FactorSensorDelay(Factor):
    NAME = 'F_SensorDelay'

    def __init__(self, context: 'CarlaContext', sensor: CarlaSensor, delay_ticks: int = 20):
        super().__init__(context)
        self._sensor = sensor
        self._delay_ticks = delay_ticks
        self._data_buffer = deque(maxlen=delay_ticks)
    
    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def on_sensor_data_recv(self, data: SimulatorOutput) -> SimulatorOutput:
        self._data_buffer.append(data)
        return self._data_buffer[0]