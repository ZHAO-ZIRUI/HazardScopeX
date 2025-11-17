import numpy as np
from shared.scenarios import Factor
from shared.simulator import *
from shared.data import Image


class FactorCameraNoise(Factor):
    NAME = 'F_CameraNoise'

    def __init__(
        self, 
        context: CarlaContext, 
        sensor: CarlaSensor,
        *,
        noise_level: float = 10.0,
    ):
        super().__init__(context)
        self._sensor = sensor
        self._noise_level = noise_level

    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def on_sensor_data_recv(self, data: Image) -> Image:
        # 生成高斯噪声
        noise = np.random.normal(0, self._noise_level, data._raw.shape).astype(np.float32)
        
        # 将图像转换为浮点数并添加噪声
        noisy_image = data._raw.astype(np.float32) + noise
        
        # 限制像素值在 [0, 255] 范围内
        noisy_image = np.clip(noisy_image, 0, 255)
        
        # 转换回 uint8
        data._raw = noisy_image.astype(np.uint8)
        
        return data