import numpy as np
from collections import deque
from shared.scenarios import Factor
from shared.simulator import *
from shared.data import Image


class FactorCameraTrail(Factor):
    NAME = 'F_CameraTrail'

    def __init__(
        self, 
        context: CarlaContext, 
        sensor: CarlaSensor,
        *,
        trail_length: int = 5,
        decay_factor: float = 0.7,
    ):
        super().__init__(context)
        self._sensor = sensor
        self._trail_length = trail_length
        self._decay_factor = decay_factor
        self._frame_buffer = deque(maxlen=trail_length)

    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def on_sensor_data_recv(self, data: Image) -> Image:
        # 将当前帧添加到缓冲区
        current_frame = data._raw.copy()
        self._frame_buffer.append(current_frame)
        
        # 如果缓冲区未满，直接返回当前帧
        if len(self._frame_buffer) < self._trail_length:
            return data
        
        # 创建混合后的图像
        blended = np.zeros_like(current_frame, dtype=np.float32)
        total_weight = 0.0
        
        # 从旧到新遍历帧，权重递减
        for i, frame in enumerate(self._frame_buffer):
            # 计算权重：越新的帧权重越高
            weight = self._decay_factor ** (self._trail_length - 1 - i)
            blended += frame.astype(np.float32) * weight
            total_weight += weight
        
        # 归一化
        blended = (blended / total_weight).astype(np.uint8)
        data._raw = blended
        
        return data