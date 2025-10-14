import carla
import numpy as np
from enum import Enum
from typing_extensions import Self

from shared.data import SimulatorOutput


class PointCloud(SimulatorOutput):
    """
    点云数据
    """
    
    class Format(Enum):
        XYZIC = 'XYZIC' # x, y, z, intensity, channel

    def __init__(
        self, 
        sim_frame: int, 
        sim_timestamp: float, 
        point_cloud: np.ndarray, 
        format: Format
    ):
        super().__init__(sim_frame, sim_timestamp)
        self._raw = point_cloud
        self._format = format

    @property
    def format(self) -> Format:
        """点云格式"""
        return self._format

    @property
    def count(self) -> int:
        """点云数量"""
        return len(self._raw)
    
    @classmethod
    def from_carla(cls, carla_input: carla.LidarMeasurement) -> Self:
        # 将 data.raw_data 转换为 Nx4 (x, y, z, intensity)
        points_per_channel = [carla_input.get_point_count(i) for i in range(carla_input.channels)]
        count_point = sum(points_per_channel)
        pc = np.frombuffer(carla_input.raw_data, dtype=np.float32)
        pc = pc.reshape(count_point, 4)
        pc = pc.copy()

        # 将 Channel 编码成 Nx5 (x, y, z, intensity, channel)
        channel_col = np.repeat(np.arange(carla_input.channels), points_per_channel)
        channel_col = channel_col.astype(np.float32).reshape(-1, 1)
        pc = np.hstack((pc, channel_col))

        instance = cls(
            sim_frame=carla_input.frame,
            sim_timestamp=carla_input.timestamp,
            point_cloud=pc,
            format=cls.Format.XYZIC,
        )
        return instance