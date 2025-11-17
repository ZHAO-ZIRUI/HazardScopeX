from shared.scenarios import Factor
from shared.simulator import *
from shared.data import Image
from typing import Literal


class FactorCameraLostChannel(Factor):
    NAME = 'F_CameraLostChannel'

    def __init__(
        self, 
        context: CarlaContext, 
        sensor: CarlaSensor,
        *,
        channel: Literal['red', 'green', 'blue', 'alpha'] = 'red',
    ):
        super().__init__(context)
        self._sensor = sensor
        self._channel = channel.lower()
        if self._channel not in ['red', 'green', 'blue', 'alpha']:
            raise ValueError(f"channel must be 'red', 'green', 'blue', or 'alpha', got '{channel}'")
        
        # 将通道名称映射到BGRA格式的索引：B=0, G=1, R=2, A=3
        channel_map = {
            'blue': 0,
            'green': 1,
            'red': 2,
            'alpha': 3,
        }
        self._channel_index = channel_map[self._channel]

    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def on_sensor_data_recv(self, data: Image) -> Image:
        # 将指定通道的值设为0，模拟通道丢失
        data._raw[:, :, self._channel_index] = 0
        return data