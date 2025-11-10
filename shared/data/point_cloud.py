import carla
import numpy as np
from enum import Enum
from typing import TYPE_CHECKING
from typing_extensions import Self

from shared.data import SimulatorOutput, TimestampSource


if TYPE_CHECKING:
    from sensor_msgs.msg import PointCloud2


class PointCloud(SimulatorOutput):
    """
    点云数据
    """
    
    class Format(Enum):
        XYZ = 0 # x, y, z
        XYZ_Intensity = 1 # x, y, z, intensity
        XYZ_Intensity_Channel = 2 # x, y, z, intensity, channel -> FROM carla.LidarMeasurement
        XYZ_Channel_Agnle_Id_SemTag = 3 # x, y, z, channel, cos_inc_angle, object_id, object_semantic_tag -> FROM carla.SemanticLidarMeasurement

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
            format=cls.Format.XYZ_Intensity_Channel,
        )
        return instance

    def to_ros2(self, frame_id: str = 'lidar', timestamp_source: TimestampSource = TimestampSource.OS) -> "PointCloud2":
        from sensor_msgs.msg import PointCloud2, PointField
        from builtin_interfaces.msg import Time

        # 获取时间戳并转换为 ROS2 Time 格式
        timestamp = self.sim_timestamp if timestamp_source == TimestampSource.SIM else self.os_timestamp
        stamp = Time()
        stamp.sec = int(timestamp)
        stamp.nanosec = int((timestamp - stamp.sec) * 1e9)

        # 定义 PointField
        fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
            PointField(name='intensity', offset=12, datatype=PointField.FLOAT32, count=1),
        ]

        # 转换数据类型并处理坐标系转换（CARLA左手系 -> ROS右手系，Y轴取反）
        points = self._raw.astype(np.float32)
        xyz = points[:, :3].copy()
        xyz[:, 1] = -xyz[:, 1]

        if self._format in (self.Format.XYZ_Intensity, self.Format.XYZ_Intensity_Channel):
            intensity = points[:, 3]
        else:
            intensity = np.ones((self.count,), dtype=np.float32)

        ros_points = np.column_stack((xyz, intensity))

        # 组装 ROS2 消息
        msg = PointCloud2()
        msg.header.stamp = stamp
        msg.header.frame_id = frame_id
        msg.height = 1
        msg.width = self.count
        msg.fields = fields
        msg.is_bigendian = False
        msg.point_step = 16  # 4 floats * 4 bytes
        msg.row_step = msg.point_step * msg.width
        msg.is_dense = False
        msg.data = ros_points.astype(np.float32).tobytes()
        
        return msg

    @classmethod
    def from_ros2(cls, ros2_msg: "PointCloud2") -> Self:
        raise NotImplemented()

    def to_file(self, file_path: str) -> Self:
        if file_path.endswith('.pcd'):
            self._save_as_pcd(file_path)
        elif file_path.endswith('.ply'):
            self._save_as_ply(file_path)
        elif file_path.endswith('.npz'):
            np.savez(file_path, points=self._raw)
        else:
            raise ValueError(f'Unsupported file extension: {file_path}')
        return self

    def _save_as_pcd(self, file_path: str) -> None:
        if self._raw.ndim != 2 or self._raw.shape[1] < 3:
            raise ValueError('PCD export requires at least XYZ columns')

        fields = ['x', 'y', 'z']
        if self._raw.shape[1] >= 4:
            fields.append('intensity')
        header = (
            '# .PCD v0.7 - Point Cloud Data file format\n'
            'VERSION 0.7\n'
            f"FIELDS {' '.join(fields)}\n"
            f"SIZE {' '.join(['4'] * len(fields))}\n"
            f"TYPE {' '.join(['F'] * len(fields))}\n"
            f"COUNT {' '.join(['1'] * len(fields))}\n"
            f'WIDTH {self.count}\n'
            'HEIGHT 1\n'
            'VIEWPOINT 0 0 0 1 0 0 0\n'
            f'POINTS {self.count}\n'
            'DATA ascii\n'
        )
        points = self._raw[:, :len(fields)].astype(np.float32)
        with open(file_path, 'w', encoding='utf-8') as file_obj:
            file_obj.write(header)
            np.savetxt(file_obj, points, fmt='%.8f')

    def _save_as_ply(self, file_path: str) -> None:
        if self._raw.ndim != 2 or self._raw.shape[1] < 3:
            raise ValueError('PLY export requires at least XYZ columns')

        header_lines = [
            'ply',
            'format ascii 1.0',
            f'element vertex {self.count}',
            'property float x',
            'property float y',
            'property float z',
        ]
        if self._raw.shape[1] >= 4:
            header_lines.append('property float intensity')
        header_lines.append('end_header\n')
        header = '\n'.join(header_lines)
        points = self._raw[:, : (4 if self._raw.shape[1] >= 4 else 3)].astype(np.float32)
        with open(file_path, 'w', encoding='utf-8') as file_obj:
            file_obj.write(header)
            np.savetxt(file_obj, points, fmt='%.8f')