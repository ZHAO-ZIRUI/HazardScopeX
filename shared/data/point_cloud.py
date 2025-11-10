import carla
import copy
import numpy as np
from enum import Enum
from typing import TYPE_CHECKING
from typing_extensions import Self
from io import StringIO

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

    def reformat(self, target_format: Format) -> Self:
        """将点云数据转换为目标格式

        Args:
            target_format (Format): 目标格式

        Returns:
            PointCloud: 转换后的点云数据
        """
        source_format = self.format
        if target_format == source_format:
            return self
        if self._raw.ndim != 2 or self._raw.shape[1] < 3:
            raise ValueError('Invalid point cloud data, at least 3 columns are required')

        dtype = self._raw.dtype
        count = self.count
        xyz = self._raw[:, :3]

        if target_format == self.Format.XYZ:
            target_raw = xyz.copy()
        elif target_format == self.Format.XYZ_Intensity:
            if source_format in (self.Format.XYZ_Intensity, self.Format.XYZ_Intensity_Channel):
                intensity = self._raw[:, 3:4]
            else:
                intensity = np.ones((count, 1), dtype=dtype)
            target_raw = np.hstack((xyz, intensity))
        elif target_format == self.Format.XYZ_Intensity_Channel:
            if source_format == self.Format.XYZ_Intensity_Channel:
                intensity = self._raw[:, 3:4]
                channel = self._raw[:, 4:5]
            elif source_format == self.Format.XYZ_Intensity:
                intensity = self._raw[:, 3:4]
                channel = np.zeros((count, 1), dtype=dtype)
            elif source_format == self.Format.XYZ_Channel_Agnle_Id_SemTag:
                intensity = np.ones((count, 1), dtype=dtype)
                channel = self._raw[:, 3:4]
            else:
                intensity = np.ones((count, 1), dtype=dtype)
                channel = np.zeros((count, 1), dtype=dtype)
            target_raw = np.hstack((xyz, intensity, channel))
        elif target_format == self.Format.XYZ_Channel_Agnle_Id_SemTag:
            if source_format == self.Format.XYZ_Channel_Agnle_Id_SemTag:
                target_raw = self._raw[:, :7]
            else:
                if source_format == self.Format.XYZ_Intensity_Channel:
                    channel = self._raw[:, 4:5]
                else:
                    channel = np.zeros((count, 1), dtype=dtype)
                cos_inc_angle = np.zeros((count, 1), dtype=dtype)
                object_id = np.zeros((count, 1), dtype=dtype)
                semantic_tag = np.zeros((count, 1), dtype=dtype)
                target_raw = np.hstack((xyz, channel, cos_inc_angle, object_id, semantic_tag))
        else:
            raise ValueError(f'Unsupported format conversion: {source_format} -> {target_format}')

        converted = copy.deepcopy(self)
        converted._format = target_format
        converted._raw = np.ascontiguousarray(target_raw)
        return converted

    @classmethod
    def from_carla(cls, carla_input: carla.LidarMeasurement | carla.SemanticLidarMeasurement) -> Self:
        if isinstance(carla_input, carla.LidarMeasurement):
            points_per_channel = [carla_input.get_point_count(i) for i in range(carla_input.channels)]
            count_point = sum(points_per_channel)
            raw = np.frombuffer(carla_input.raw_data, dtype=np.float32).reshape(count_point, 4).copy()

            channel_col = np.repeat(np.arange(carla_input.channels), points_per_channel).astype(np.float32).reshape(-1, 1)
            point_cloud = np.hstack((raw, channel_col))

            return cls(
                sim_frame=carla_input.frame,
                sim_timestamp=carla_input.timestamp,
                point_cloud=point_cloud,
                format=cls.Format.XYZ_Intensity_Channel,
            )

        if isinstance(carla_input, carla.SemanticLidarMeasurement):
            points_per_channel = [carla_input.get_point_count(i) for i in range(carla_input.channels)]
            count_point = sum(points_per_channel)
            raw = np.frombuffer(carla_input.raw_data, dtype=np.float32).reshape(count_point, 6).copy()

            channel_col = np.repeat(np.arange(carla_input.channels), points_per_channel).astype(np.float32).reshape(-1, 1)
            xyz = raw[:, :3]
            cos_inc_angle = raw[:, 3:4]
            object_id = raw[:, 4:5]
            semantic_tag = raw[:, 5:6]
            point_cloud = np.hstack((xyz, channel_col, cos_inc_angle, object_id, semantic_tag))

            return cls(
                sim_frame=carla_input.frame,
                sim_timestamp=carla_input.timestamp,
                point_cloud=point_cloud,
                format=cls.Format.XYZ_Channel_Agnle_Id_SemTag,
            )

        raise TypeError(f'Unsupported CARLA input type: {type(carla_input)}')

    def to_ros2(self, frame_id: str = 'lidar', timestamp_source: TimestampSource = TimestampSource.OS) -> "PointCloud2":
        from sensor_msgs.msg import PointCloud2, PointField
        from builtin_interfaces.msg import Time

        # 获取时间戳并转换为 ROS2 Time 格式
        timestamp = self.sim_timestamp if timestamp_source == TimestampSource.SIM else self.os_timestamp
        stamp = Time()
        stamp.sec = int(timestamp)
        stamp.nanosec = int((timestamp - stamp.sec) * 1e9)

        formatted = self.reformat(self.Format.XYZ_Intensity)
        ros_points = formatted._raw.astype(np.float32).copy()
        ros_points[:, 1] = -ros_points[:, 1]    # CARLA左手系 -> ROS右手系，Y轴取反

        # 定义 PointField
        fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
            PointField(name='intensity', offset=12, datatype=PointField.FLOAT32, count=1),
        ]

        # 组装 ROS2 消息
        msg = PointCloud2()
        msg.header.stamp = stamp
        msg.header.frame_id = frame_id
        msg.height = 1
        msg.width = formatted.count
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
            content = self._dump_to_pcd()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        elif file_path.endswith('.ply'):
            content = self._dump_to_ply()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        elif file_path.endswith('.npz'):
            np.savez(file_path, points=self._raw)
        else:
            raise ValueError(f'Unsupported file extension: {file_path}')
        return self

    def _dump_to_pcd(self) -> str:
        if self._raw.ndim != 2 or self._raw.shape[1] < 3:
            raise ValueError('PCD export requires at least XYZ columns')

        format_fields = {
            self.Format.XYZ: (
                self.Format.XYZ,
                ['x', 'y', 'z'],
                ['F', 'F', 'F'],
                ['float', 'float', 'float'],
            ),
            self.Format.XYZ_Intensity: (
                self.Format.XYZ_Intensity,
                ['x', 'y', 'z', 'intensity'],
                ['F', 'F', 'F', 'F'],
                ['float', 'float', 'float', 'float'],
            ),
            self.Format.XYZ_Intensity_Channel: (
                self.Format.XYZ_Intensity_Channel,
                ['x', 'y', 'z', 'intensity', 'channel'],
                ['F', 'F', 'F', 'F', 'I'],
                ['float', 'float', 'float', 'float', 'int'],
            ),
            self.Format.XYZ_Channel_Agnle_Id_SemTag: (
                self.Format.XYZ_Channel_Agnle_Id_SemTag,
                ['x', 'y', 'z', 'channel', 'cos_inc_angle', 'object_id', 'object_semantic_tag'],
                ['F', 'F', 'F', 'I', 'F', 'I', 'I'],
                ['float', 'float', 'float', 'int', 'float', 'int', 'int'],
            ),
        }

        target_format, fields, field_types, _ = format_fields[self.format]
        formatted = self.reformat(target_format)
        points = formatted._raw.copy()
        for idx, field_type in enumerate(field_types):
            if field_type == 'I':
                points[:, idx] = np.rint(points[:, idx])
            else:
                points[:, idx] = points[:, idx].astype(np.float32)

        fmt = ['%.8f' if field_type == 'F' else '%d' for field_type in field_types]

        header_lines = [
            '# .PCD v0.7 - Point Cloud Data file format',
            'VERSION 0.7',
            f"FIELDS {' '.join(fields)}",
            f"SIZE {' '.join(['4'] * len(fields))}",
            f"TYPE {' '.join(field_types)}",
            f"COUNT {' '.join(['1'] * len(fields))}",
            f'WIDTH {formatted.count}',
            'HEIGHT 1',
            'VIEWPOINT 0 0 0 1 0 0 0',
            f'POINTS {formatted.count}',
            'DATA ascii',
        ]

        buffer = StringIO()
        np.savetxt(buffer, points, fmt=fmt)
        return '\n'.join(header_lines) + '\n' + buffer.getvalue()

    def _dump_to_ply(self) -> str:
        if self._raw.ndim != 2 or self._raw.shape[1] < 3:
            raise ValueError('PLY export requires at least XYZ columns')

        format_fields = {
            self.Format.XYZ: (
                self.Format.XYZ,
                ['x', 'y', 'z'],
                ['F', 'F', 'F'],
                ['float', 'float', 'float'],
            ),
            self.Format.XYZ_Intensity: (
                self.Format.XYZ_Intensity,
                ['x', 'y', 'z', 'intensity'],
                ['F', 'F', 'F', 'F'],
                ['float', 'float', 'float', 'float'],
            ),
            self.Format.XYZ_Intensity_Channel: (
                self.Format.XYZ_Intensity_Channel,
                ['x', 'y', 'z', 'intensity', 'channel'],
                ['F', 'F', 'F', 'F', 'I'],
                ['float', 'float', 'float', 'float', 'int'],
            ),
            self.Format.XYZ_Channel_Agnle_Id_SemTag: (
                self.Format.XYZ_Channel_Agnle_Id_SemTag,
                ['x', 'y', 'z', 'channel', 'cos_inc_angle', 'object_id', 'object_semantic_tag'],
                ['F', 'F', 'F', 'I', 'F', 'I', 'I'],
                ['float', 'float', 'float', 'int', 'float', 'int', 'int'],
            ),
        }

        target_format, fields, field_types, property_types = format_fields[self.format]
        formatted = self.reformat(target_format)
        points = formatted._raw.copy()
        for idx, field_type in enumerate(field_types):
            if field_type == 'I':
                points[:, idx] = np.rint(points[:, idx])
            else:
                points[:, idx] = points[:, idx].astype(np.float32)

        fmt = ['%.8f' if field_type == 'F' else '%d' for field_type in field_types]

        header_lines = [
            'ply',
            'format ascii 1.0',
            f'element vertex {formatted.count}',
        ]
        header_lines.extend([f'property {prop_type} {field}' for field, prop_type in zip(fields, property_types)])
        header_lines.append('end_header')

        buffer = StringIO()
        np.savetxt(buffer, points, fmt=fmt)
        return '\n'.join(header_lines) + '\n' + buffer.getvalue()