import numpy as np
from shared.scenarios import Factor
from shared.simulator import *
from shared.data import PointCloud


class FactorLidarBlock(Factor):
    NAME = 'F_LidarBlock'

    def __init__(
        self, 
        context: CarlaContext, 
        sensor: CarlaSensor,
        *,
        horizontal_min: float = -30.0,
        horizontal_max: float = 30.0,
        vertical_min: float = -10.0,
        vertical_max: float = 10.0,
    ):
        """
        模拟雷达在某个角度范围内被遮挡
        
        清空指定角度范围内的所有点云数据, 模拟雷达被遮挡的效果.
        
        Args:
            horizontal_min: 水平角度下界(度), 默认-30.0
            horizontal_max: 水平角度上界(度), 默认30.0
            vertical_min: 垂直角度下界(度), 默认-10.0
            vertical_max: 垂直角度上界(度), 默认10.0
        """
        super().__init__(context)
        self._sensor = sensor
        self._horizontal_min = np.radians(horizontal_min)
        self._horizontal_max = np.radians(horizontal_max)
        self._vertical_min = np.radians(vertical_min)
        self._vertical_max = np.radians(vertical_max)

    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def on_sensor_data_recv(self, data: PointCloud) -> PointCloud:
        """
        根据角度范围清空点云中的点
        """
        if data.count == 0:
            return data
        
        # 获取xyz坐标
        xyz = data._raw[:, :3]
        x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
        
        # 计算水平角度(azimuth): atan2(y, x), 范围 [-π, π]
        horizontal_angle = np.arctan2(y, x)
        
        # 计算垂直角度(elevation): atan2(z, sqrt(x^2 + y^2)), 范围 [-π/2, π/2]
        horizontal_distance = np.sqrt(x**2 + y**2)
        vertical_angle = np.arctan2(z, horizontal_distance)
        
        # 判断点是否在遮挡范围内
        in_horizontal_range = (horizontal_angle >= self._horizontal_min) & (horizontal_angle <= self._horizontal_max)
        in_vertical_range = (vertical_angle >= self._vertical_min) & (vertical_angle <= self._vertical_max)
        in_blocked_range = in_horizontal_range & in_vertical_range
        
        # 保留不在遮挡范围内的点
        mask = ~in_blocked_range
        data._raw = data._raw[mask]
        
        return data