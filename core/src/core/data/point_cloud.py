import carla
import numpy as np
from enum import Enum

from .simulator_output import SimulatorOutput


class PointCloud(SimulatorOutput):

    class Format(Enum):
        XYZ_Intensity_Channel  = 'XYZ_Intensity_Channel'

    def __init__(
            self,
            data_channels: int,
            data_format: Format,
            data: np.ndarray,
            *,
            frame_id: int = 0,
            timestamp_sim: float = 0,
    ):
        """
        :param data_channels: 点云的分组
        :param data_format: 点云的数据编码格式
        :param data: 以 ``np.ndarray`` 形式存储的数据
        :param frame_id: 帧序号
        :param timestamp_sim: 仿真时间戳
        """
        super().__init__(frame_id, timestamp_sim)
        self.data_channels = data_channels
        self.data_format: PointCloud.Format = data_format
        self._data: np.ndarray = data

    @property
    def data(self) -> np.ndarray:
        return self._data

    @classmethod
    def from_carla(cls, data: carla.LidarMeasurement) -> 'PointCloud':
        # 将 data.raw_data 转换为 Nx4 (x, y, z, intensity)
        points_per_channel = [data.get_point_count(i) for i in range(data.channels)]
        count_point = sum(points_per_channel)
        pc = np.frombuffer(data.raw_data, dtype=np.float32)
        pc = pc.reshape(count_point, 4)
        pc = pc.copy()

        # 将 Channel 编码成 Nx5 (x, y, z, intensity, channel)
        channel_col = np.repeat(np.arange(data.channels), points_per_channel)
        channel_col = channel_col.astype(np.float32).reshape(-1, 1)
        pc = np.hstack((pc, channel_col))

        instance = cls(
            data_channels=data.channels,
            data_format=cls.Format.XYZ_Intensity_Channel,
            data=pc,
            frame_id=data.frame,
            timestamp_sim=data.timestamp,
        )
        return instance
