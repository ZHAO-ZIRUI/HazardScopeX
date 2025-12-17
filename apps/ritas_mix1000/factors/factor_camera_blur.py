import cv2
from shared.scenarios import Factor
from shared.simulator import *
from shared.data import Image


class FactorCameraBlur(Factor):
    NAME = 'F_CameraBlur'

    def __init__(
        self, 
        context: CarlaContext, 
        sensor: CarlaSensor,
        *,
        kernel_size: int = 15,
        sigma: float = 0.0,
    ):
        super().__init__(context)
        self._sensor = sensor
        # 确保 kernel_size 是奇数
        if kernel_size % 2 == 0:
            kernel_size += 1
        self._kernel_size = kernel_size
        self._sigma = sigma

    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def on_sensor_data_recv(self, data: Image) -> Image:
        # 对图像应用高斯模糊
        data._raw = cv2.GaussianBlur(data._raw, (self._kernel_size, self._kernel_size), self._sigma)
        return data