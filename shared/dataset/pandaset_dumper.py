import os
import json
import uuid
from pathlib import Path
from typing import Any, Optional

import carla
import numpy as np
import pandas as pd
from pyquaternion import Quaternion
from typing_extensions import Self

from shared.dataset import DatasetDumper
from shared.simulator import CarlaSensor, CarlaContext, CarlaVehicle
from shared.data import BaseData, Image, PointCloud


class PandaSetDumper(DatasetDumper):
    """
    导出为 PandaSet 数据集格式

    输出目录结构（每个 sequence 一个目录）：
      camera/<camera_name>/*.jpg
      camera/<camera_name>/pose.json
      camera/<camera_name>/timestamp.json
      camera/<camera_name>/intrinsics.json

      lidar/*.pkl
      lidar/pose.json
      lidar/timestamp.json

      annotations/cuboids/*.pkl.gz
      annotations/semseg/*.pkl.gz
      annotations/semseg/classes.json
    """

    DATASET_TYPE = 'PandaSet'

    # 需要保存的文件夹名
    ANNOTATIONS_FOLDER = 'annotations'
    ANNOTATIONS_SUB_CUBOIDS = 'cuboids'
    ANNOTATIONS_SUB_SEMSEG = 'semseg'
    CAMERA_FOLDER = 'camera'
    LIDAR_FOLDER = 'lidar'
    META_FOLDER = 'meta'

    # JSON 文件名
    INTRINSICS_JSON = 'intrinsics.json'
    POSE_JSON = 'poses.json'
    TIMESTAMP_JSON = 'timestamps.json'
    GPS_JSON = 'gps.json'
    CLASSES_JSON = 'classes.json'

    # 常量
    TIMESTAMP_INCREMENT_MICROSECONDS = 50000  # 恢复缺失 sample 时的时间戳增量（微秒）
    TIMESTAMP_TO_MICROSECONDS = 1_000_000     # 秒到微秒的转换因子

    # PandaSet 标准类别定义 (index, name)
    PANDASET_CATEGORIES = [
        (1, "Smoke"),
        (2, "Exhaust"),
        (3, "Spray or rain"),
        (4, "Reflection"),
        (5, "Vegetation"),
        (6, "Ground"),
        (7, "Road"),
        (8, "Lane Line Marking"),
        (9, "Stop Line Marking"),
        (10, "Other Road Marking"),
        (11, "Sidewalk"),
        (12, "Driveway"),
        (13, "Car"),
        (14, "Pickup Truck"),
        (15, "Medium-sized Truck"),
        (16, "Semi-truck"),
        (17, "Towed Object"),
        (18, "Motorcycle"),
        (19, "Other Vehicle - Construction Vehicle"),
        (20, "Other Vehicle - Uncommon"),
        (21, "Other Vehicle - Pedicab"),
        (22, "Emergency Vehicle"),
        (23, "Bus"),
        (24, "Personal Mobility Device"),
        (25, "Motorized Scooter"),
        (26, "Bicycle"),
        (27, "Train"),
        (28, "Trolley"),
        (29, "Tram / Subway"),
        (30, "Pedestrian"),
        (31, "Pedestrian with Object"),
        (32, "Animals - Bird"),
        (33, "Animals - Other"),
        (34, "Pylons"),
        (35, "Road Barriers"),
        (36, "Signs"),
        (37, "Cones"),
        (38, "Construction Signs"),
        (39, "Temporary Construction Barriers"),
        (40, "Rolling Containers"),
        (41, "Building"),
        (42, "Other Static Object"),
    ]

    # CARLA semantic tag -> PandaSet class id（0-based）
    CARLA_PANDASET_MAPPING: dict[int, int] = {
        0: 1,    # None -> Smoke(占位/背景)
        1: 7,    # Roads -> Road
        2: 11,   # Sidewalks -> Sidewalk
        3: 41,   # Buildings -> Building
        7: 36,   # TrafficLight -> Signs(近似)
        8: 36,   # TrafficSigns -> Signs
        9: 5,    # Vegetation -> Vegetation
        12: 30,  # Pedestrians -> Pedestrian
        14: 13,  # Car -> Car
        15: 15,  # Truck -> Medium-sized Truck(近似)
        16: 23,  # Bus -> Bus
        17: 27,  # Train -> Train
        18: 18,  # Motorcycle -> Motorcycle
        19: 26,  # Bicycle -> Bicycle
        20: 42,  # Static -> Other Static Object
        21: 40,  # Dynamic -> Rolling Containers(近似)
        22: 42,  # Other -> Other Static Object(近似)
        24: 8,   # RoadLines -> Lane Line Marking
        25: 6,   # Ground -> Ground
        28: 35,  # GuardRail -> Road Barriers
    }

    def __init__(
        self,
        context: CarlaContext,
        *,
        name: str = None,
        path: str | Path | None = None,
        vehicle: str = 'UNKNOWN',
        ego_vehicle: CarlaVehicle | None = None,
    ):
        self._vehicle = vehicle
        self._ego_vehicle = ego_vehicle
        if self._ego_vehicle is None:
            raise ValueError("ego_vehicle is required")

        super().__init__(
            context=context,
            name=name,
            path=path,
        )

        # 目录
        self._camera_folder: Path | None = None
        self._lidar_folder: Path | None = None
        self._meta_folder: Path | None = None
        self._annotations_folder: Path | None = None
        self._cuboids_folder: Path | None = None
        self._semseg_folder: Path | None = None

        # 用户建议的变量定义风格
        self._sensor_folders: dict[CarlaSensor, Path] = {}
        self._sensor_naming_policies: dict[CarlaSensor, 'DatasetDumper.NamingPolicy'] = {}
        self._known_objects: dict[int, str] = {}

        # PandaSet 输出缓存
        self._camera_intrinsics: dict[str, dict[str, float]] = {}
        self._poses_by_sensor: dict[str, list[dict[str, Any]]] = {}
        self._timestamps_by_sensor: dict[str, list[int]] = {}

        self._timestamp_offset: float = 0.0
        self._has_timestamp_offset: bool = False

        # global origin（按论文：每个 sequence 自己的 global 原点在起点）
        self._global_origin_pandaset: Optional[np.ndarray] = None

        # 传感器外参（由你自己的 vehicle 类提供）
        self.sensor_tf = self._ego_vehicle.get_sensor_vehicle_rear_wheels_center_tf()


        # primary lidar（用于写到 lidar/ 下；如果有多个 lidar，优先非 semantic lidar）
        self._primary_lidar_sensor: Optional[CarlaSensor] = None
        self._primary_lidar_name: Optional[str] = None

        # 记录哪些 lidar 帧已经转换为 world 坐标（避免重复变换）
        self._lidar_world_transformed_files: set[Path] = set()
    def __post_init__(self) -> Self:
        super().__post_init__()

        self._camera_folder = self._path / self.CAMERA_FOLDER
        self._lidar_folder = self._path / self.LIDAR_FOLDER
        self._annotations_folder = self._path / self.ANNOTATIONS_FOLDER
        self._cuboids_folder = self._annotations_folder / self.ANNOTATIONS_SUB_CUBOIDS
        self._semseg_folder = self._annotations_folder / self.ANNOTATIONS_SUB_SEMSEG
        self._meta_folder = self._path / self.META_FOLDER

        os.makedirs(self._camera_folder, exist_ok=True)
        os.makedirs(self._lidar_folder, exist_ok=True)
        os.makedirs(self._meta_folder, exist_ok=True)
        os.makedirs(self._cuboids_folder, exist_ok=True)
        os.makedirs(self._semseg_folder, exist_ok=True)

        # tick 钩子：记录 pose/timestamp + annotations
        self._append_hook_befre_next_tick(self._tick_record_pandaset)

        # flush 钩子：最后把 json 写出去
        self.hook_after_final_flush.append(self._export_pandaset_json)

        # 确保 _log_result 在最后执行
        # if self._log_result in self._hook_after_final_flush:
        #     self._hook_after_final_flush.remove(self._log_result)
        #     self._hook_after_final_flush.append(self._log_result)

        return self

    def bind_sensor_output(
        self,
        sensor: CarlaSensor,
        path: str | Path | None = None,
        naming_policy: 'DatasetDumper.NamingPolicy' = None,
    ) -> Self:
        """绑定传感器数据输出到内存缓存（并创建对应输出目录）"""
        sensor_name = self._split_vehicle_sensor(sensor.name)
        
        if path is None:
            # PandaSet 保存结构：camera/<camera_name>/...  lidar/...
            if sensor.is_camera:
                path = Path(self.CAMERA_FOLDER) / sensor_name
            elif sensor.is_lidar:
                path = Path(self.LIDAR_FOLDER)
            else:
                raise ValueError(f"Unsupported sensor type: {sensor.bp.id}")
        else:
            # 允许用户手动传 path，但如果没带顶层目录，就按类型补上 传入的sensor.name
            path = Path(path)

            if sensor.is_camera and (len(path.parts) == 0 or path.parts[0] != self.CAMERA_FOLDER):
                path = Path(self.CAMERA_FOLDER) / path
            if sensor.is_lidar and (len(path.parts) == 0 or path.parts[0] != self.LIDAR_FOLDER):
                path = Path(self.LIDAR_FOLDER) / path
        samples_folder_path = path
        folder_path_abs = (self._path / samples_folder_path).resolve()
        folder_path_abs.mkdir(parents=True, exist_ok=True)

        if naming_policy is None:
            if sensor.is_camera:
                naming_policy = self.NamingPolicy(extension='jpg')
            elif sensor.is_lidar:
                naming_policy = self.NamingPolicy(extension='pkl.gz')
            else:
                raise ValueError(f"Unsupported sensor type: {sensor.bp.id}")

        self._sensor_folders[sensor] = folder_path_abs
        self._sensor_naming_policies[sensor] = naming_policy
        super().bind_sensor_output(sensor, samples_folder_path, naming_policy)

        # 保存相机内参（PandaSet 习惯是每个相机一份 intrinsics.json）
        if sensor.is_camera:
            K = sensor.get_camera_intrinsics_matrix()
            camera_intrinsic = {
                'fx': float(K[0, 0]),
                'fy': float(K[1, 1]),
                'cx': float(K[0, 2]),
                'cy': float(K[1, 2]),
            }
            self._camera_intrinsics.setdefault(sensor_name, camera_intrinsic)


        # 记录主 LiDAR（用于写到 lidar/ 根目录的 pose/timestamp.json）
        if sensor.is_lidar:
            bp_id = sensor.bp.id.lower() if getattr(sensor, "bp", None) else ""
            is_semantic = "semantic" in bp_id
            if self._primary_lidar_sensor is None:
                self._primary_lidar_sensor = sensor
                self._primary_lidar_name = sensor_name
            else:
                prev_bp = self._primary_lidar_sensor.bp.id.lower() if getattr(self._primary_lidar_sensor, "bp", None) else ""
                prev_is_semantic = "semantic" in prev_bp
                # 更偏好非 semantic lidar 作为输出（semantic lidar 通常只用于生成标注）
                if prev_is_semantic and (not is_semantic):
                    self._primary_lidar_sensor = sensor
                    self._primary_lidar_name = sensor_name

        return self


    def _flush_data(self, data: BaseData, file_path: Path) -> None:
        """将传感器数据导出到磁盘。

        约定（对齐 PandaSet devkit）：
        - LiDAR 点云以 pandas.DataFrame 保存为 .pkl，字段为：x,y,z,i,t,d
        - 点云坐标为 PandaSet world（sequence-local）坐标系
        - 我们只实现 1 个 LiDAR，因此 d 字段统一置 0
        """

        if isinstance(data, Image):
            data.to_file(file_path)
            return
        
        if isinstance(data, PointCloud):
            
            suffix_full = "".join(file_path.suffixes).lower()
            # self.logger.debug(f"the suffix is : {suffix_full}")
            # PandaSet LiDAR：写成 DataFrame pickle（.pkl.gz）
            if suffix_full == ".pkl.gz":
                # 1) 确保点坐标已经变换到 PandaSet world(local) 下
                self._ensure_lidar_world_coords_before_flush(data, file_path)

                pts = data.raw
                names = pts.dtype.names or ()
                if not all(k in names for k in (PointCloud.FIELD_X, PointCloud.FIELD_Y, PointCloud.FIELD_Z)):
                    raise ValueError(f"PointCloud missing xyz fields: {names}")

                x = np.asarray(pts[PointCloud.FIELD_X], dtype=np.float32)
                y = np.asarray(pts[PointCloud.FIELD_Y], dtype=np.float32)
                z = np.asarray(pts[PointCloud.FIELD_Z], dtype=np.float32)
                n = int(x.shape[0])

                # intensity：CARLA 没有真正对应的反射强度，这里用 0（你也可以替换为其它字段）
                i = np.zeros(n, dtype=np.float32)

                # t：点级时间戳（float），这里用当前帧时间戳广播到每个点
                frame_idx = self._frame_idx_from_file_path(file_path)
                t_val = self._frame_timestamp_seconds(frame_idx) if frame_idx is not None else 0.0
                t = np.full(n, float(t_val), dtype=np.float64)

                # d：LiDAR id（0=机械 360° LiDAR, 1=前向 LiDAR），这里只实现 0
                d = np.zeros(n, dtype=np.int8)

                df = pd.DataFrame({"x": x, "y": y, "z": z, "i": i, "t": t, "d": d})
                df.to_pickle(file_path,compression="gzip")
                return

            # 如果你仍然需要输出 .bin（兼容旧流程），保留这条分支：只做左右手系转换
            if suffix_full == ".bin":
                points = data.raw
                points_x = np.asarray(points[PointCloud.FIELD_X])
                points_y = np.asarray(points[PointCloud.FIELD_Y])
                points_z = np.asarray(points[PointCloud.FIELD_Z])
                points_xyz_carla = np.stack([points_x, points_y, points_z], axis=1)

                points_xyz_p = self._carla_lidar_points_pandaset_lidar(points_xyz_carla)
                assert points_xyz_p.shape[0] == points.shape[0]

                points[PointCloud.FIELD_X] = points_xyz_p[:, 0].astype(points[PointCloud.FIELD_X].dtype, copy=False)
                points[PointCloud.FIELD_Y] = points_xyz_p[:, 1].astype(points[PointCloud.FIELD_Y].dtype, copy=False)
                points[PointCloud.FIELD_Z] = points_xyz_p[:, 2].astype(points[PointCloud.FIELD_Z].dtype, copy=False)

                data.to_file(file_path)
                return

        raise ValueError(f"Unsupported sensor data type: {type(data)}")

    def _split_vehicle_sensor(self, name: str) -> str:
        """从 sensor.name 中解析传感器后缀名（例如：xxx_front_camera -> front_camera）"""
        sensors = sorted(set(self._ego_vehicle.VEHICLE_SENSORS), key=len, reverse=True)
        for sensor in sensors:
            suffix = "_" + sensor
            if name.endswith(suffix):
                vehicle = name[:-len(suffix)]
                if not vehicle:
                    raise ValueError(f"车辆名为空：{name!r}")
                return sensor
        raise ValueError(f"无法从字符串识别传感器后缀：{name!r}")

    @staticmethod
    def _rotation_matrix_to_quaternion(rotation_matrix: np.ndarray) -> np.ndarray:
        """将旋转矩阵转换为四元数（w,x,y,z）"""
        trace = np.trace(rotation_matrix)

        if trace > 0:
            s = np.sqrt(trace + 1.0) * 2
            w = 0.25 * s
            x = (rotation_matrix[2, 1] - rotation_matrix[1, 2]) / s
            y = (rotation_matrix[0, 2] - rotation_matrix[2, 0]) / s
            z = (rotation_matrix[1, 0] - rotation_matrix[0, 1]) / s
        else:
            if rotation_matrix[0, 0] > rotation_matrix[1, 1] and rotation_matrix[0, 0] > rotation_matrix[2, 2]:
                s = np.sqrt(1.0 + rotation_matrix[0, 0] - rotation_matrix[1, 1] - rotation_matrix[2, 2]) * 2
                w = (rotation_matrix[2, 1] - rotation_matrix[1, 2]) / s
                x = 0.25 * s
                y = (rotation_matrix[0, 1] + rotation_matrix[1, 0]) / s
                z = (rotation_matrix[0, 2] + rotation_matrix[2, 0]) / s
            elif rotation_matrix[1, 1] > rotation_matrix[2, 2]:
                s = np.sqrt(1.0 + rotation_matrix[1, 1] - rotation_matrix[0, 0] - rotation_matrix[2, 2]) * 2
                w = (rotation_matrix[0, 2] - rotation_matrix[2, 0]) / s
                x = (rotation_matrix[0, 1] + rotation_matrix[1, 0]) / s
                y = 0.25 * s
                z = (rotation_matrix[1, 2] + rotation_matrix[2, 1]) / s
            else:
                s = np.sqrt(1.0 + rotation_matrix[2, 2] - rotation_matrix[0, 0] - rotation_matrix[1, 1]) * 2
                w = (rotation_matrix[1, 0] - rotation_matrix[0, 1]) / s
                x = (rotation_matrix[0, 2] + rotation_matrix[2, 0]) / s
                y = (rotation_matrix[1, 2] + rotation_matrix[2, 1]) / s
                z = 0.25 * s

        return np.array([w, x, y, z], dtype=float)

    def _matrix_to_pandaset_pose(self, T: np.ndarray) -> dict[str, Any]:
        t = T[:3, 3].astype(float)
        R = T[:3, :3].astype(float)
        q = self._rotation_matrix_to_quaternion(R)
        return {
            "position": {"x": float(t[0]), "y": float(t[1]), "z": float(t[2])},
            "heading": {"w": float(q[0]), "x": float(q[1]), "y": float(q[2]), "z": float(q[3])},
        }

    def _initialize_timestamp(self, snapshot: carla.WorldSnapshot) -> int:
        """初始化并计算相对时间戳（微秒，int）"""
        if not self._has_timestamp_offset:
            self._timestamp_offset = snapshot.timestamp.elapsed_seconds
            self._has_timestamp_offset = True

        rel_s = snapshot.timestamp.elapsed_seconds - self._timestamp_offset
        return int(round(rel_s * self.TIMESTAMP_TO_MICROSECONDS))

    def _get_vehicle_from_sensors(self) -> Optional[CarlaVehicle]:
        """从已绑定传感器里找到车辆对象"""
        for sensor in self._sensor_folders.keys():
            vehicle = sensor.parent if getattr(sensor, "parent", None) else None
            if vehicle is not None:
                return vehicle
        return None

    def _carla_to_pandaset_extrinsic(self, T: np.ndarray) -> np.ndarray:
        """CARLA(左手系, x前y右z上) 4x4 -> PandaSet(右手系, x前y左z上) 4x4.

        优先使用 ego_vehicle 上的 carla_ego_to_pandaset_ego_extrinsic；如果没有，则回退到
        carla_ego_to_nuscenes_ego_extrinsic（你旧代码里常用的命名）。
        """
        if hasattr(self._ego_vehicle, "carla_ego_to_pandaset_ego_extrinsic"):
            return self._ego_vehicle.carla_ego_to_pandaset_ego_extrinsic(T)
        if hasattr(self._ego_vehicle, "carla_ego_to_nuscenes_ego_extrinsic"):
            return self._ego_vehicle.carla_ego_to_nuscenes_ego_extrinsic(T)
        raise AttributeError("ego_vehicle 缺少坐标系变换函数：carla_ego_to_pandaset_ego_extrinsic / carla_ego_to_nuscenes_ego_extrinsic")

    def _ego_rear_world_matrix_pandaset(self, vehicle: CarlaVehicle) -> np.ndarray:
        """
        计算“后轴中心(ego frame)”在 PandaSet world 坐标系下的 4x4 pose。

        约定：
        - vehicle.tf_now.get_matrix() 给出 CARLA world<-vehicle_center 的 4x4
        - self.sensor_tf["vehicle_to_vehicle_rear"] 为 CARLA rear<-vehicle_center 的 4x4
        - PandaSet world/ego 轴：x 前, y 左, z 上（右手系）
        """
        vehicle_tf = vehicle.tf_now
        T_w_center_carla = np.array(vehicle_tf.get_matrix(), dtype=float)

        # rear<-center（CARLA）
        T_rear_center_carla = np.array(self.sensor_tf["vehicle_center_to_rear_carla"], dtype=float)

        # world<-rear = world<-center @ center<-rear
        T_center_rear_carla = np.linalg.inv(T_rear_center_carla)
        T_w_rear_carla = T_w_center_carla @ T_center_rear_carla

        # CARLA -> PandaSet（复用 vehicle 中的基变换）
        T_w_rear_pandaset = self._carla_to_pandaset_extrinsic(T_w_rear_carla)
        return T_w_rear_pandaset

    def _find_sensor_file_path_for_frame(self, sensor: CarlaSensor, frame_idx: int) -> Optional[Path]:
        sensor_folder = self._sensor_folders.get(sensor)
        naming_policy = self._sensor_naming_policies.get(sensor)
        if sensor_folder is None or naming_policy is None:
            return None

        counter_str = str(frame_idx).rjust(naming_policy.zfill_length, naming_policy.zfill_char)
        fp = (sensor_folder / f"{counter_str}.{naming_policy.extension}").resolve()
        if fp in self._data_buffer or fp.exists():
            return fp

        # fallback：前一帧
        prev_idx = max(0, frame_idx - 1)
        prev_str = str(prev_idx).rjust(naming_policy.zfill_length, naming_policy.zfill_char)
        fp2 = (sensor_folder / f"{prev_str}.{naming_policy.extension}").resolve()
        if fp2 in self._data_buffer or fp2.exists():
            return fp2

        return None

    @staticmethod
    def _carla_lidar_points_pandaset_lidar(points_carla: np.ndarray) -> np.ndarray:
        """
        CARLA LiDAR 点：x 前, y 右, z 上（左手）
        PandaSet/右手系（与 ego/world 一致）：x 前, y 左, z 上（右手）

        坐标变换（仅做左右手转换）：
          x_p =  x_c
          y_p = -y_c
          z_p =  z_c
        """
        assert points_carla.ndim == 2 and points_carla.shape[1] >= 3
        xyz = points_carla[:, :3].astype(float, copy=False)
        out = np.empty_like(xyz, dtype=float)
        out[:, 0] = xyz[:, 0]
        out[:, 1] = -xyz[:, 1]
        out[:, 2] = xyz[:, 2]
        return out


    def _frame_idx_from_file_path(self, file_path: Path) -> Optional[int]:
        """从文件名提取帧号，例如 000123.pkl -> 123"""
        try:
            return int(file_path.stem)
        except Exception:
            return None

    def _frame_timestamp_seconds(self, frame_idx: Optional[int]) -> float:
        """返回某帧的时间戳（秒，float）。"""
        if frame_idx is None:
            return 0.0

        sensor_name = self._primary_lidar_name
        if sensor_name is None:
            for k in self._timestamps_by_sensor.keys():
                if k not in self._camera_intrinsics:
                    sensor_name = k
                    break
        if sensor_name is None:
            return 0.0

        ts_list = self._timestamps_by_sensor.get(sensor_name, [])
        if frame_idx < 0 or frame_idx >= len(ts_list):
            return 0.0
        return float(ts_list[frame_idx]) / float(self.TIMESTAMP_TO_MICROSECONDS)

    def _pandaset_pose_to_matrix(self, pose: dict[str, Any]) -> np.ndarray:
        """pose.json 的一条记录 -> 4x4 (world<-sensor)"""
        p = pose.get("position", {})
        h = pose.get("heading", {})
        t = np.array([float(p.get("x", 0.0)), float(p.get("y", 0.0)), float(p.get("z", 0.0))], dtype=float)

        q = Quaternion(
            float(h.get("w", 1.0)),
            float(h.get("x", 0.0)),
            float(h.get("y", 0.0)),
            float(h.get("z", 0.0)),
        )
        R = q.rotation_matrix.astype(float)

        T = np.eye(4, dtype=float)
        T[:3, :3] = R
        T[:3, 3] = t
        return T

    def _ensure_lidar_world_coords_before_flush(self, data: PointCloud, file_path: Path) -> None:
        """flush 阶段兜底：保证 LiDAR 点云在 world(local) 坐标系下。"""
        try:
            if file_path.suffix.lower() != ".pkl":
                return
            if file_path.parent.name != self.LIDAR_FOLDER:
                return
        except Exception:
            return

        if file_path in self._lidar_world_transformed_files:
            return

        frame_idx = self._frame_idx_from_file_path(file_path)
        if frame_idx is None:
            return

        lidar_name = self._primary_lidar_name
        if lidar_name is None:
            return

        poses = self._poses_by_sensor.get(lidar_name, [])
        if frame_idx < 0 or frame_idx >= len(poses):
            return

        T_w_s_local = self._pandaset_pose_to_matrix(poses[frame_idx])

        pts = data.raw
        names = pts.dtype.names or ()
        if not all(k in names for k in (PointCloud.FIELD_X, PointCloud.FIELD_Y, PointCloud.FIELD_Z)):
            return

        xyz_carla = np.stack(
            [
                np.asarray(pts[PointCloud.FIELD_X], dtype=float),
                np.asarray(pts[PointCloud.FIELD_Y], dtype=float),
                np.asarray(pts[PointCloud.FIELD_Z], dtype=float),
            ],
            axis=1,
        )

        xyz_sensor = self._carla_lidar_points_pandaset_lidar(xyz_carla)

        ones = np.ones((xyz_sensor.shape[0], 1), dtype=float)
        xyz1 = np.concatenate([xyz_sensor[:, :3], ones], axis=1)
        xyz_w = (T_w_s_local @ xyz1.T).T[:, :3]

        pts[PointCloud.FIELD_X] = xyz_w[:, 0].astype(pts[PointCloud.FIELD_X].dtype, copy=False)
        pts[PointCloud.FIELD_Y] = xyz_w[:, 1].astype(pts[PointCloud.FIELD_Y].dtype, copy=False)
        pts[PointCloud.FIELD_Z] = xyz_w[:, 2].astype(pts[PointCloud.FIELD_Z].dtype, copy=False)

        self._lidar_world_transformed_files.add(file_path)

    def _apply_world_transform_to_lidar_in_buffer(
        self,
        sensor: CarlaSensor,
        frame_idx: int,
        T_w_s_abs: np.ndarray,
        origin_abs: np.ndarray,
    ) -> None:
        """把当前帧 lidar 点云直接变换到 world(local) 并写回 buffer。"""
        fp = self._find_sensor_file_path_for_frame(sensor, frame_idx)
        if fp is None:
            return

        pc = self._data_buffer.get(fp)
        if not isinstance(pc, PointCloud):
            return

        pts = pc.raw
        names = pts.dtype.names or ()
        if not all(k in names for k in (PointCloud.FIELD_X, PointCloud.FIELD_Y, PointCloud.FIELD_Z)):
            return

        xyz_carla = np.stack(
            [
                np.asarray(pts[PointCloud.FIELD_X], dtype=float),
                np.asarray(pts[PointCloud.FIELD_Y], dtype=float),
                np.asarray(pts[PointCloud.FIELD_Z], dtype=float),
            ],
            axis=1,
        )

        xyz_sensor = self._carla_lidar_points_pandaset_lidar(xyz_carla)

        ones = np.ones((xyz_sensor.shape[0], 1), dtype=float)
        xyz1 = np.concatenate([xyz_sensor[:, :3], ones], axis=1)
        xyz_w_abs = (T_w_s_abs @ xyz1.T).T[:, :3]

        xyz_w_local = xyz_w_abs - origin_abs.reshape(1, 3)

        pts[PointCloud.FIELD_X] = xyz_w_local[:, 0].astype(pts[PointCloud.FIELD_X].dtype, copy=False)
        pts[PointCloud.FIELD_Y] = xyz_w_local[:, 1].astype(pts[PointCloud.FIELD_Y].dtype, copy=False)
        pts[PointCloud.FIELD_Z] = xyz_w_local[:, 2].astype(pts[PointCloud.FIELD_Z].dtype, copy=False)

        self._lidar_world_transformed_files.add(fp)

    def _get_or_create_uuid(self, object_id: int) -> str:
        if object_id not in self._known_objects:
            self._known_objects[object_id] = str(uuid.uuid4())
        return self._known_objects[object_id]

    def _export_annotations_for_frame(self, frame_idx: int, origin: np.ndarray) -> None:
        """导出 semseg + cuboids（按 PandaSet devkit 习惯存 DataFrame）"""
        # 找 semantic lidar（blueprint id 包含 semantic）
        semantic_lidar: Optional[CarlaSensor] = None
        for s in self._sensor_folders.keys():
            if s.is_lidar and "semantic" in s.bp.id.lower():
                semantic_lidar = s
                break

        if semantic_lidar is None:
            return

        fp = self._find_sensor_file_path_for_frame(semantic_lidar, frame_idx)
        # self.logger.debug(f"semantic fp={fp}, transformed={fp in self._lidar_world_transformed_files}")
        if fp is None:
            return

        pc = self._data_buffer.get(fp)
        if not isinstance(pc, PointCloud):
            return

        pts = pc.raw.copy()
        names = pts.dtype.names or ()
        if PointCloud.FIELD_OBJECT_ID not in names or PointCloud.FIELD_OBJECT_SEMANTIC_TAG not in names:
            return

        object_ids = np.asarray(pts[PointCloud.FIELD_OBJECT_ID])
        semantic_tags = np.asarray(pts[PointCloud.FIELD_OBJECT_SEMANTIC_TAG])

        # semseg：DataFrame columns == ['class']
        mapped = np.zeros_like(semantic_tags, dtype=np.int32)
        for carla_id, pandaset_id in self.CARLA_PANDASET_MAPPING.items():
            mapped[semantic_tags == int(carla_id)] = int(pandaset_id)

        semseg_df = pd.DataFrame({"class": mapped.astype(np.int32)})
        semseg_path = self._semseg_folder / f"{str(frame_idx).rjust(6, '0')}.pkl.gz"
        semseg_df.to_pickle(semseg_path, compression="gzip")

        # cuboids
        unique_object_ids = np.unique(object_ids)
        unique_object_ids = unique_object_ids[unique_object_ids > 0]

        class_name = {int(i): str(n) for i, n in self.PANDASET_CATEGORIES}
        self.logger.debug(f"PandaSet cuboids categories: {class_name}")

        rows: list[dict[str, Any]] = []

        for oid in unique_object_ids:
            actor = self._context.world.get_actor(int(oid))
            self.logger.debug(f"Processing actor id={oid}, actor.type_id={actor.type_id }")
            if actor is None:
                continue
            # 跳过 ego（按你原来的逻辑）
            if actor.type_id == "vehicle.tesla.model3":
                continue

            mask = object_ids == oid

            if not np.any(mask):
                continue

            carla_sem = int(semantic_tags[mask][0])
            cls_id = int(self.CARLA_PANDASET_MAPPING.get(carla_sem, 0))
            label = class_name.get(cls_id, str(cls_id))

            info = self._get_actor_info(actor)

            cx, cy, cz = info["center_translation_pandaset"]
            cx -= float(origin[0])
            cy -= float(origin[1])
            cz -= float(origin[2])

            w, l, h = info["size_pandaset"]
            yaw = info["yaw_pandaset"]

            v = info["velocity"]
            speed = float(np.sqrt(v.x * v.x + v.y * v.y + v.z * v.z))
            stationary = bool(speed < 0.1)

            rows.append(
                {
                    "uuid": self._get_or_create_uuid(int(oid)),
                    "label": label,
                    "yaw": float(yaw),
                    "stationary": stationary,
                    "camera_used": int(-1),
                    "position.x": float(cx),
                    "position.y": float(cy),
                    "position.z": float(cz),
                    "dimensions.x": float(w),
                    "dimensions.y": float(l),
                    "dimensions.z": float(h),
                    "attributes.object_motion": "stationary" if stationary else "Moving",
                    "cuboids.sibling_id": "",
                    "cuboids.sensor_id": int(-1),
                    "attributes.rider_status": "",
                    "attributes.pedestrian_behavior": "",
                    "attributes.pedestrian_age": "",
                }
            )

        cuboids_df = pd.DataFrame(rows)
        cuboids_path = self._cuboids_folder / f"{str(frame_idx).rjust(6, '0')}.pkl.gz"
        cuboids_df.to_pickle(cuboids_path, compression="gzip")

    def _append_pose_and_timestamp(self, sensor_name: str, pose: dict, timestamp: int) -> None:
        self._poses_by_sensor.setdefault(sensor_name, []).append(pose)
        self._timestamps_by_sensor.setdefault(sensor_name, []).append(int(timestamp))

    def _tick_record_pandaset(self, snapshot: carla.WorldSnapshot) -> Self:
        """
        1) timestamp（微秒）
        2) ego(后轴中心) world pose
        3) 每个 sensor 的 world pose：T_w_s = T_w_e * T_e_s
        4) 全部以“首帧主 LiDAR 的 world 位置”为 global origin（仅平移归零），写入 pose.json
        """
        timestamp = self._initialize_timestamp(snapshot)

        vehicle = self._get_vehicle_from_sensors()
        if vehicle is None:
            self.logger.warning("No vehicle found from bound sensors; skip pose recording.")
            return self

        # world<-ego(rear) in PandaSet basis
        T_w_e = self._ego_rear_world_matrix_pandaset(vehicle)

        # -------------------------------------------------------------
        # global origin：优先使用“首帧主 LiDAR 的 world 位置”
        # 这样第 0 帧 lidar pose 的 position 会是 (0,0,0)（符合 PandaSet 常见习惯）
        # -------------------------------------------------------------
        if self._global_origin_pandaset is None:
            origin = None

            primary = getattr(self, "_primary_lidar_sensor", None)
            if primary is not None:
                
                primary_name = self._split_vehicle_sensor(primary.name)
                self.logger.debug(f"the primary lidar sensor name is : {primary_name}")
                T_e_l = self.sensor_tf.get(primary_name, None)
                if T_e_l is not None:
                    T_w_l = T_w_e @ np.array(T_e_l, dtype=float)
                    origin = T_w_l[:3, 3].copy()
                else:
                    self.logger.warning(f"Primary lidar '{primary_name}' extrinsic not found in sensor_tf; fallback to ego origin.")
            else:
                self.logger.warning("Primary lidar sensor not set; fallback to ego origin.")
            
            self.logger.debug(f"PandaSet local origin for sequence set to: {origin}")

            # fallback：用 ego(rear) 首帧位置
            if origin is None:
                origin = T_w_e[:3, 3].copy()

            self._global_origin_pandaset = origin

        origin = self._global_origin_pandaset

        # -------------------------------------------------------------
        # 写每个 sensor 的 world pose（减 origin 平移归零）
        # -------------------------------------------------------------
        for sensor in self._sensor_folders.keys():
            if not (sensor.is_camera or sensor.is_lidar):
                continue

            sensor_name = self._split_vehicle_sensor(sensor.name)
            if sensor_name not in self.sensor_tf:
                continue

            T_e_s = np.array(self.sensor_tf[sensor_name], dtype=float)  # ego<-sensor (PandaSet basis)
            T_w_s = T_w_e @ T_e_s                                       # world<-sensor

            pose = self._matrix_to_pandaset_pose(T_w_s)
            pose["position"]["x"] -= float(origin[0])
            pose["position"]["y"] -= float(origin[1])
            pose["position"]["z"] -= float(origin[2])

            self._append_pose_and_timestamp(sensor_name, pose, timestamp)

            # 如果这是主 LiDAR：将当前帧点云直接变换到 PandaSet world(local) 坐标系（同一个 origin）
            if sensor.is_lidar and (getattr(self, "_primary_lidar_sensor", None) is not None) and (sensor == self._primary_lidar_sensor):
                self._apply_world_transform_to_lidar_in_buffer(sensor, self._frame_counter, T_w_s, origin)

        # annotations（基于 semantic lidar）
        self._export_annotations_for_frame(self._frame_counter, origin)

        return self


    # def _tick_record_pandaset(self, snapshot: carla.WorldSnapshot) -> Self:
    #     """
    #     1) timestamp（微秒）
    #     2) ego(后轴中心) world pose
    #     3) 每个 sensor 的 world pose：T_w_s = T_w_e * T_e_s
    #     4) 全部以“首帧位置”为 global origin，写入 pose.json（平移）
    #     """
    #     timestamp = self._initialize_timestamp(snapshot)

    #     vehicle = self._get_vehicle_from_sensors()
    #     if vehicle is None:
    #         self.logger.warning("No vehicle found from bound sensors; skip pose recording.")
    #         return self

    #     T_w_e = self._ego_rear_world_matrix_pandaset(vehicle) # 当前时刻下ego在自己定义的pandaset 整体坐标系下的旋转矩阵

    #     # 起点作为 global origin
    #     if self._global_origin_pandaset is None:
    #         self._global_origin_pandaset = T_w_e[:3, 3].copy()
    #     origin = self._global_origin_pandaset

    #     for sensor in self._sensor_folders.keys():
    #         if not (sensor.is_camera or sensor.is_lidar):
    #             continue

    #         sensor_name = self._split_vehicle_sensor(sensor.name)
    #         if sensor_name not in self.sensor_tf:
    #             continue

    #         T_e_s = np.array(self.sensor_tf[sensor_name], dtype=float)
    #         T_w_s = T_w_e @ T_e_s

    #         pose = self._matrix_to_pandaset_pose(T_w_s)
    #         pose["position"]["x"] -= float(origin[0])
    #         pose["position"]["y"] -= float(origin[1])
    #         pose["position"]["z"] -= float(origin[2])

    #         self._append_pose_and_timestamp(sensor_name, pose, timestamp)

    #         # 如果这是主 LiDAR：将当前帧点云直接变换到 PandaSet world(local) 坐标系
    #         if sensor.is_lidar and (self._primary_lidar_sensor is not None) and (sensor == self._primary_lidar_sensor):
    #             self._apply_world_transform_to_lidar_in_buffer(sensor, self._frame_counter, T_w_s, origin)

    #     # annotations（基于 semantic lidar）
    #     self._export_annotations_for_frame(self._frame_counter, origin)

    #     return self

    def _export_pandaset_json(self) -> Self:
        """把 pose/timestamp/intrinsics/classes 写成 PandaSet devkit 习惯的 json"""
        # camera: intrinsics + pose + timestamp
        for cam_name, intr in self._camera_intrinsics.items():
            cam_dir = self._path / self.CAMERA_FOLDER / cam_name
            cam_dir.mkdir(parents=True, exist_ok=True)

            with open(cam_dir / self.INTRINSICS_JSON, "w", encoding="utf-8") as f:
                json.dump(intr, f, ensure_ascii=False, indent=2)

            with open(cam_dir / self.POSE_JSON, "w", encoding="utf-8") as f:
                json.dump(self._poses_by_sensor.get(cam_name, []), f, ensure_ascii=False, indent=2)

            with open(cam_dir / self.TIMESTAMP_JSON, "w", encoding="utf-8") as f:
                json.dump(self._timestamps_by_sensor.get(cam_name, []), f, ensure_ascii=False, indent=2)


        # lidar: pose + timestamp（写到 lidar 根目录）
        lidar_dir = self._path / self.LIDAR_FOLDER
        lidar_dir.mkdir(parents=True, exist_ok=True)

        lidar_key = self._primary_lidar_name
        if lidar_key is None:
            # fallback：挑一个非相机的 key
            lidar_keys = [k for k in self._poses_by_sensor.keys() if k not in self._camera_intrinsics]
            lidar_key = lidar_keys[0] if lidar_keys else None

        with open(lidar_dir / self.POSE_JSON, "w", encoding="utf-8") as f:
            json.dump(self._poses_by_sensor.get(lidar_key, []), f, ensure_ascii=False, indent=2)

        with open(lidar_dir / self.TIMESTAMP_JSON, "w", encoding="utf-8") as f:
            json.dump(self._timestamps_by_sensor.get(lidar_key, []), f, ensure_ascii=False, indent=2)


        # semseg classes.json
        classes = {str(i): name for i, name in self.PANDASET_CATEGORIES}
        with open(self._semseg_folder / self.CLASSES_JSON, "w", encoding="utf-8") as f:
            json.dump(classes, f, ensure_ascii=False, indent=2)

        return self

    def _get_actor_info(self, actor: carla.Actor) -> dict[str, Any]:
        """
        获取 actor 的 bbox 信息，并统一转换到 PandaSet world/ego 右手系（x 前, y 左, z 上）。
        这里的“yaw”是从转换后的 3x3 旋转矩阵里提取的绕 z 轴角（标准 atan2(R[1,0], R[0,0])）。
        """
        actor_transform = actor.get_transform()
        T_w_actor_carla = np.array(actor_transform.get_matrix(), dtype=float)
        T_w_actor_p = self._carla_to_pandaset_extrinsic(T_w_actor_carla)

        # bbox 中心点（先在 CARLA world 求出，再做坐标系变换）
        bbox = actor.bounding_box
        bbox_center_world_carla = actor_transform.transform(bbox.location)

        T_tmp = np.eye(4, dtype=float)
        T_tmp[:3, 3] = [bbox_center_world_carla.x, bbox_center_world_carla.y, bbox_center_world_carla.z]
        T_tmp_p = self._carla_to_pandaset_extrinsic(T_tmp)
        center_translation_p = T_tmp_p[:3, 3].tolist()

        # 尺寸：CARLA bbox.extent: x 前后, y 左右, z 上下（在 actor 局部系）
        extents = bbox.extent
        w = 2 * float(extents.y)  # 左右宽
        l = 2 * float(extents.x)  # 前后长
        h = 2 * float(extents.z)  # 高
        size_p = [w, l, h]

        # yaw（PandaSet world/ego）
        R_p = T_w_actor_p[:3, :3]
        yaw_p = float(np.arctan2(R_p[1, 0], R_p[0, 0]))

        actor_velocity = actor.get_velocity()

        return {
            "size_pandaset": size_p,
            "center_translation_pandaset": center_translation_p,
            "yaw_pandaset": yaw_p,
            "velocity": actor_velocity,
        }

