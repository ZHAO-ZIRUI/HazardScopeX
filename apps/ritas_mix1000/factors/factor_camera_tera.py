import numpy as np
import random
from collections import deque
from shared.scenarios import Factor
from shared.simulator import *
from shared.data import Image


class FactorCameraTera(Factor):
    NAME = 'F_CameraTera'

    def __init__(
        self, 
        context: CarlaContext, 
        sensor: CarlaSensor,
        *,
        tear_position: float = 0.3,
        frame_delay: int = 1,
        num_tears: int = 1,
        transition_width: float = 0.0,
        tear_probability: float = 0.1,
    ):
        """
        模拟横向撕裂效果, 类似显示器垂直同步失效
        
        图像在水平方向上出现撕裂, 上半部分和下半部分显示不同时刻的画面.
        模拟显示器在没有垂直同步时, 刷新过程中上半部分显示旧帧, 下半部分显示新帧的效果.
        
        Args:
            tear_position: 撕裂位置(0.0到1.0), 0.0表示顶部, 1.0表示底部, 默认0.2
            frame_delay: 错帧数量, 上半部分使用多少帧前的数据, 值越大错帧越明显, 默认10
            num_tears: 撕裂线数量, 可以有多条撕裂线, 默认1
            transition_width: 过渡带宽度(0.0到1.0), 0.0表示硬切换, 值越大过渡越平滑, 默认0.0
            tear_probability: 撕裂出现的概率(0.0到1.0), 0.0表示永不出现, 1.0表示每帧都出现, 默认0.1
        """
        super().__init__(context)
        self._sensor = sensor
        self._frame_buffer = deque(maxlen=frame_delay + 1)
        self._tear_position = tear_position
        self._frame_delay = frame_delay
        self._num_tears = num_tears
        self._transition_width = transition_width
        self._tear_probability = tear_probability

    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def on_sensor_data_recv(self, data: Image) -> Image:
        """
        模拟横向撕裂效果
        使用帧缓冲区保存历史帧, 上半部分使用延迟的帧, 下半部分使用当前帧
        撕裂效果偶发出现, 由tear_probability控制概率
        """
        height, width = data._raw.shape[:2]
        
        # 将当前帧添加到缓冲区
        current_frame = data._raw.copy()
        self._frame_buffer.append(current_frame)
        
        # 如果缓冲区未满, 直接返回
        if len(self._frame_buffer) < self._frame_delay + 1:
            return data
        
        # 随机决定是否出现撕裂效果
        if random.random() > self._tear_probability:
            return data
        
        # 获取延迟的帧（用于上半部分）
        delayed_frame = self._frame_buffer[0]
        
        # 创建结果图像
        result = data._raw.copy()
        
        if self._num_tears == 1:
            # 单条撕裂线
            tear_y = int(height * self._tear_position)
            
            if self._transition_width > 0.0:
                # 有过渡带的情况
                transition_pixels = int(height * self._transition_width)
                transition_start = max(0, tear_y - transition_pixels // 2)
                transition_end = min(height, tear_y + transition_pixels // 2)
                
                # 上半部分: 使用延迟的帧
                if transition_start > 0:
                    result[:transition_start] = delayed_frame[:transition_start]
                
                # 过渡带: 混合延迟帧和当前帧
                if transition_end > transition_start:
                    transition_height = transition_end - transition_start
                    blend_factor = np.linspace(1.0, 0.0, transition_height)[:, np.newaxis, np.newaxis]
                    result[transition_start:transition_end] = (
                        delayed_frame[transition_start:transition_end].astype(np.float32) * blend_factor +
                        current_frame[transition_start:transition_end].astype(np.float32) * (1 - blend_factor)
                    ).astype(np.uint8)
                
                # 下半部分: 使用当前帧
                if transition_end < height:
                    result[transition_end:] = current_frame[transition_end:]
            else:
                # 硬切换: 直接拼接
                result[:tear_y] = delayed_frame[:tear_y]
                result[tear_y:] = current_frame[tear_y:]
        else:
            # 多条撕裂线: 将图像分成多个区域, 交替使用延迟帧和当前帧
            segment_height = height / self._num_tears
            
            for i in range(self._num_tears):
                start_y = int(i * segment_height)
                end_y = int((i + 1) * segment_height) if i < self._num_tears - 1 else height
                
                # 奇数段使用延迟帧, 偶数段使用当前帧(或相反, 取决于撕裂位置)
                if (i % 2 == 0 and self._tear_position < 0.5) or (i % 2 == 1 and self._tear_position >= 0.5):
                    result[start_y:end_y] = delayed_frame[start_y:end_y]
                else:
                    result[start_y:end_y] = current_frame[start_y:end_y]
        
        data._raw = result
        
        return data