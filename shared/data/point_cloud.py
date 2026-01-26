import carla
import numpy as np
from typing import TYPE_CHECKING
from pathlib import Path
from typing_extensions import Self
from io import StringIO

from shared.data import SimulatorOutput, TimestampSource


if TYPE_CHECKING:
    from sensor_msgs.msg import PointCloud2


class PointCloud(SimulatorOutput):
    """
    点云数据
    """

    FIELD_X = 'x'
    FIELD_Y = 'y'
    FIELD_Z = 'z'
    FIELD_INTENSITY = 'intensity'
    FIELD_CHANNEL = 'channel'
    FIELD_COS_INC_ANGLE = 'cos_inc_angle'
    FIELD_OBJECT_ID = 'object_id'
    FIELD_OBJECT_SEMANTIC_TAG = 'object_semantic_tag'

    def __init__(
        self, 
        sim_frame: int, 
        sim_timestamp: float, 
        point_cloud: np.ndarray, 
        format: np.dtype,
    ):
        super().__init__(sim_frame, sim_timestamp)
        self._raw = point_cloud
        self._format = format

    @property
    def format(self) -> np.dtype:
        """点云格式, 结构化数组类型"""
        return self._format

    @property
    def count(self) -> int:
        """点云数量"""
        return len(self._raw)

    @classmethod
    def from_carla(cls, carla_input: carla.LidarMeasurement | carla.SemanticLidarMeasurement) -> Self:
        if isinstance(carla_input, carla.LidarMeasurement):
            # 定义点云格式
            format = np.dtype([
                (cls.FIELD_X, np.float32),
                (cls.FIELD_Y, np.float32),
                (cls.FIELD_Z, np.float32),
                (cls.FIELD_INTENSITY, np.float32),
                (cls.FIELD_CHANNEL, np.uint32),
            ])

            # 读取点云, 并构建 Channel 列
            points_per_channel = [carla_input.get_point_count(i) for i in range(carla_input.channels)]
            points_sum = sum(points_per_channel)
            cloud_raw = np.frombuffer(carla_input.raw_data, dtype=np.float32).reshape(points_sum, 4).copy()
            col_channel = np.repeat(np.arange(carla_input.channels), points_per_channel).astype(np.uint32)
            
            # 创建结构化数组并填充数据, 避免额外拷贝
            cloud = np.empty(points_sum, dtype=format)
            cloud[cls.FIELD_X] = cloud_raw[:, 0]
            cloud[cls.FIELD_Y] = cloud_raw[:, 1]
            cloud[cls.FIELD_Z] = cloud_raw[:, 2]
            cloud[cls.FIELD_INTENSITY] = cloud_raw[:, 3]
            cloud[cls.FIELD_CHANNEL] = col_channel
            # print("cloud shape:",cloud.shape)
            return cls(
                sim_frame=carla_input.frame,
                sim_timestamp=carla_input.timestamp,
                point_cloud=cloud,
                format=format,
            )

        if isinstance(carla_input, carla.SemanticLidarMeasurement):
            # 定义点云格式
            format = np.dtype([
                (cls.FIELD_X, np.float32),
                (cls.FIELD_Y, np.float32),
                (cls.FIELD_Z, np.float32),
                (cls.FIELD_COS_INC_ANGLE, np.float32),
                (cls.FIELD_OBJECT_ID, np.uint32),
                (cls.FIELD_OBJECT_SEMANTIC_TAG, np.uint32),
                (cls.FIELD_CHANNEL, np.uint32),
            ])

            # 定义原始点云格式
            source_dtype = np.dtype([
                (cls.FIELD_X,  np.float32),
                (cls.FIELD_Y,  np.float32),
                (cls.FIELD_Z,  np.float32),
                (cls.FIELD_COS_INC_ANGLE, np.float32),
                (cls.FIELD_OBJECT_ID,  np.uint32),
                (cls.FIELD_OBJECT_SEMANTIC_TAG, np.uint32),
            ])

            # 读取点云, 并构建 Channel 列
            points_per_channel = [carla_input.get_point_count(i) for i in range(carla_input.channels)]
            points_sum = sum(points_per_channel)
            cloud_raw = np.frombuffer(carla_input.raw_data, dtype=source_dtype, count=points_sum).copy()
            col_channel = np.repeat(np.arange(carla_input.channels), points_per_channel).astype(np.uint32)

            # 创建结构化数组并填充数据
            cloud = np.empty(points_sum, dtype=format)
            cloud[cls.FIELD_X] = cloud_raw[cls.FIELD_X]
            cloud[cls.FIELD_Y] = cloud_raw[cls.FIELD_Y]
            cloud[cls.FIELD_Z] = cloud_raw[cls.FIELD_Z]
            cloud[cls.FIELD_COS_INC_ANGLE] = cloud_raw[cls.FIELD_COS_INC_ANGLE]
            cloud[cls.FIELD_OBJECT_ID] = cloud_raw[cls.FIELD_OBJECT_ID]
            cloud[cls.FIELD_OBJECT_SEMANTIC_TAG] = cloud_raw[cls.FIELD_OBJECT_SEMANTIC_TAG]
            cloud[cls.FIELD_CHANNEL] = col_channel
            # print("semantic cloud shape:",cloud.shape)
            return cls(
                sim_frame=carla_input.frame,
                sim_timestamp=carla_input.timestamp,
                point_cloud=cloud,
                format=format,
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

        # 准备点云数据（复制以避免修改原始数据）
        ros_points = self._raw.copy()
        
        # CARLA左手系 -> ROS右手系，Y轴取反
        ros_points[self.FIELD_Y] = -ros_points[self.FIELD_Y]

        # 根据 format 动态生成 PointField
        # 映射 numpy dtype 到 ROS2 PointField 数据类型
        dtype_to_pointfield = {
            np.float32: PointField.FLOAT32,
            np.float64: PointField.FLOAT64,
            np.int8: PointField.INT8,
            np.uint8: PointField.UINT8,
            np.int16: PointField.INT16,
            np.uint16: PointField.UINT16,
            np.int32: PointField.INT32,
            np.uint32: PointField.UINT32,
        }
        
        fields = []
        for name in self.format.names:
            field_dtype, offset = self.format.fields[name]
            ros_dtype = dtype_to_pointfield.get(field_dtype.type, PointField.FLOAT32)
            fields.append(PointField(
                name=name.lower(),
                offset=offset,
                datatype=ros_dtype,
                count=1
            ))

        # 组装 ROS2 消息
        msg = PointCloud2()
        msg.header.stamp = stamp
        msg.header.frame_id = frame_id
        msg.height = 1
        msg.width = self.count
        msg.fields = fields
        msg.is_bigendian = False
        msg.point_step = self.format.itemsize  # 使用 format 的实际大小
        msg.row_step = msg.point_step * msg.width
        msg.is_dense = False
        # 使用 memoryview 直接暴露底层连续缓冲区, 避免多余拷贝
        # 此处直接操作 msg 的 _data 属性, 而不是 msg.data, 因为 msg.data 会进行额外的格式转换
        msg._data = memoryview(ros_points)
        return msg

    @classmethod
    def from_ros2(cls, ros2_msg: "PointCloud2") -> Self:
        raise NotImplementedError()

    def to_file(
        self, 
        file_path: str | Path,
        *,
        include_extra_fields: bool = False,
    ) -> Self:
        file_path = Path(file_path) if isinstance(file_path, str) else file_path
        if file_path.suffix == '.pcd':
            content = self.to_pcd(include_extra_fields=include_extra_fields)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        elif file_path.suffix == '.ply':
            content = self.to_ply(include_extra_fields=include_extra_fields)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        elif file_path.suffix == '.npz':
            if include_extra_fields:
                # 将结构化数组转换为普通数组
                points = np.column_stack([self._raw[field] for field in self.format.names])
                np.savez(file_path, points=points)
            else:
                xyz = np.column_stack([
                    self._raw[self.FIELD_X],
                    self._raw[self.FIELD_Y],
                    self._raw[self.FIELD_Z]
                ])
                np.savez(file_path, points=xyz)
        elif file_path.suffix == '.bin':
            self.to_pcdbin(file_path)
        else:
            raise ValueError(f'Unsupported file extension: {file_path}')
        return self

    def to_pcdbin(self,file_path) -> None:
        '''
         将点云数据写为bin文件格式
        '''
        points = self.raw.copy()
        points_x = np.asarray(points[PointCloud.FIELD_X])
        points_y = np.asarray(points[PointCloud.FIELD_Y])
        points_z = np.asarray(points[PointCloud.FIELD_Z])
        points_cos = np.asarray(points[PointCloud.FIELD_COS_INC_ANGLE])
        points_save = np.stack([points_x, points_y, points_z,points_cos,points_cos], axis=1)  
         # 1) 基本检查：至少要有 XYZ，且我们需要前 5 列
        if points_save.ndim != 2 or points_save.shape[1] < 5:
            raise ValueError('PCD BIN export requires at least 5 columns: x, y, z, channel_col, cos_inc_angle')
        # 2) 确保是我们期望的格式：
        points_5 = points_save.copy() # (N,5)
        with open(file_path, "wb") as f:
            points_5.tofile(f)

    def to_pcd(self, *, include_extra_fields: bool = False) -> str:
        # 确定要导出的字段
        if include_extra_fields:
            fields = list(self.format.names)
        else:
            fields = [self.FIELD_X, self.FIELD_Y, self.FIELD_Z]

        # 提取字段数据并构建数组
        field_data = []
        field_types = []
        for field in fields:
            field_dtype, _ = self.format.fields[field]
            is_integer = np.issubdtype(field_dtype.type, np.integer)
            field_types.append('I' if is_integer else 'F')
            
            data = self._raw[field].copy()
            if is_integer:
                data = np.rint(data).astype(np.int32)
            else:
                data = data.astype(np.float32)
            field_data.append(data)

        points = np.column_stack(field_data)

        # 构建格式字符串
        fmt = ['%.8f' if field_type == 'F' else '%d' for field_type in field_types]

        # 构建 PCD 头部
        header_lines = [
            '# .PCD v0.7 - Point Cloud Data file format',
            'VERSION 0.7',
            f"FIELDS {' '.join(fields)}",
            f"SIZE {' '.join(['4'] * len(fields))}",
            f"TYPE {' '.join(field_types)}",
            f"COUNT {' '.join(['1'] * len(fields))}",
            f'WIDTH {self.count}',
            'HEIGHT 1',
            'VIEWPOINT 0 0 0 1 0 0 0',
            f'POINTS {self.count}',
            'DATA ascii',
        ]

        buffer = StringIO()
        np.savetxt(buffer, points, fmt=fmt)
        return '\n'.join(header_lines) + '\n' + buffer.getvalue()

    def to_ply(self, *, include_extra_fields: bool = False) -> str:
        # 确定要导出的字段
        if include_extra_fields:
            fields = list(self.format.names)
        else:
            fields = [self.FIELD_X, self.FIELD_Y, self.FIELD_Z]

        # 提取字段数据并构建数组
        field_data = []
        property_types = []
        for field in fields:
            field_dtype, _ = self.format.fields[field]
            is_integer = np.issubdtype(field_dtype.type, np.integer)
            property_types.append('int' if is_integer else 'float')
            
            data = self._raw[field].copy()
            if is_integer:
                data = np.rint(data).astype(np.int32)
            else:
                data = data.astype(np.float32)
            field_data.append(data)

        points = np.column_stack(field_data)

        # 构建格式字符串
        fmt = ['%.8f' if pt == 'float' else '%d' for pt in property_types]

        # 构建 PLY 头部
        header_lines = [
            'ply',
            'format ascii 1.0',
            f'element vertex {self.count}',
        ]
        header_lines.extend([f'property {prop_type} {field}' for field, prop_type in zip(fields, property_types)])
        header_lines.append('end_header')

        buffer = StringIO()
        np.savetxt(buffer, points, fmt=fmt)
        return '\n'.join(header_lines) + '\n' + buffer.getvalue()