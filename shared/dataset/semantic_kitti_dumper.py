import os
import carla
import numpy as np
from typing import TYPE_CHECKING
from typing_extensions import Self
from io import StringIO

from shared.dataset import DatasetDumper
from shared.simulator import CarlaSensor, CarlaBlueprints
from shared.data import *

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


class SemanticKittiDumper(DatasetDumper):
    """
    导出为 SemanticKitti 数据集格式
    """

    DATASET_CLASS = 'SemanticKitti'
    
    FOLDER_SEM_LIDAR_VELODYNE = 'velodyne'
    FOLDER_SEM_LIDAR_LABLE = 'labels'
    
    FILE_TIMESTAMP = 'times.txt'
    FILE_CALIB = 'calib.txt'
    FILE_POSE = 'pose.txt'

    CARLA_KITTI_SEMANTIC_MAPPING = {
        1: 40,      # road -> road
        2: 48,      # sidewalk -> sidewalk
        3: 50,      # building -> building
        4: 52,      # wall -> other-structure
        5: 51,      # fence -> fence
        6: 80,      # pole -> pole
        7: 99,      # traffic light -> other-object
        8: 81,      # traffic sign -> traffic-sign
        9: 70,      # vegetation -> vegetation
        10: 72,     # terrain -> terrain
        11: 0,      # sky -> unlabeled
        12: 30,     # pedestrian -> person
        13: 31,     # rider -> bicyclist
        14: 10,     # car -> car
        15: 18,     # truck -> truck
        16: 13,     # bus -> bus
        17: 16,     # train -> on-rails
        18: 15,     # motorcycle -> motorcycle
        19: 11,     # bicycle -> bicycle
        20: 20,     # static -> outlier
        21: 259,    # dynamic -> moving-other-vehicle
        22: 99,     # other -> other-object
        23: 49,     # water -> other-ground
        24: 60,     # road line -> lane-marking
        25: 49,     # ground -> other-ground
        26: 52,     # bridge -> other-structure
        27: 49,     # rail -> other-ground
        28: 51,     # guard rail -> fence
        29: 60,     # lane-marking -> lane-marking
        30: 44,     # parking -> parking
    }

    def __init__(
        self,
        context: 'CarlaContext',
        folder_path: str,
        *,
        name: str = None,
        safe_memory_usage_threshold: float = DatasetDumper.SAFE_MEMORY_USAGE_THRESHOLD,
        create_folder: bool = True
    ):
        """初始化 SemanticKitti 数据集导出器

        至少需要一个摄像头传感器(cam_0)和语义激光雷达传感器(semantic_lidar)

        Args:
            context (CarlaContext): 仿真上下文
            folder_path (str): 数据集保存路径
            name (str, optional): 数据集名称. 默认为 None, 将根据时间自动生成.
            safe_memory_usage_threshold (float, optional): 安全内存使用阈值, 当内存使用率超过该阈值时, 将自动导出数据集到磁盘. 默认为 SAFE_MEMORY_USAGE_THRESHOLD.
            create_folder (bool, optional): 是否创建数据集文件夹, 如果为 False, 则需要确保数据集文件夹存在. 默认为 True.
        """
        super().__init__(
            context=context,
            folder_path=folder_path,
            name=name,
            safe_memory_usage_threshold=safe_memory_usage_threshold,
            create_folder=create_folder,
        )
        self._main_camera: CarlaSensor | None = None
        self._main_lidar: CarlaSensor | None = None
        self._other_cameras: list[CarlaSensor] = []

        self._folder_main_lidar_velodyne: str = None
        self._folder_main_lidar_labels: str = None
        self._file_timestamp: str = None
        self._file_calib: str = None
        self._file_pose: str = None

        self._timestamp_offset: float = 0.0
        self._pose_offset: np.ndarray | None = None

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._context.hook_on_tick.remove(self._ensure_main_sensors_ready)
        self._context.hook_on_tick.remove(self._tick_cache_timestamp)
        self._context.hook_on_tick.remove(self._tick_cache_pose)
        return super().__exit__(exc_type, exc_value, traceback)

    def _post_init(self) -> Self:
        super()._post_init()
        self._context.hook_on_tick.append(self._ensure_main_sensors_ready)
        self._context.hook_on_tick.append(self._tick_cache_timestamp)
        self._context.hook_on_tick.append(self._tick_cache_pose)
        self.hook_after_main_flush.append(self._calc_and_flush_calib)
        return self

    def bind_main_camera(self, sensor: CarlaSensor) -> Self:
        """定义主摄像头传感器, 该摄像头用于计算位置映射, 是 SemanticKITTI 的必要条件

        Args:
            sensor (CarlaSensor): 主摄像头传感器实例

        Returns:
            Self: 返回自身
        """
        self._main_camera = sensor

        self.bind_sensor_output(sensor, sensor.name, self.NamingPolicy(extension='png'))
        return self

    def bind_main_lidar(self, sensor: CarlaSensor) -> Self:
        """定义主激光雷达传感器, 该激光雷达用于生成点云和语义分割标签

        Args:
            sensor (CarlaSensor): 主激光雷达传感器实例

        Returns:
            Self: 返回自身
        """
        if sensor.bp.id.lower() != CarlaBlueprints.SENSOR_LIDAR_RAY_CAST_SEMANTIC.value:
            self.logger.critical(f'Main lidar must be a semantic lidar: {sensor.bp.id}, given: {sensor.bp.id}')
            raise SystemExit(429)

        self._main_lidar = sensor

        self.bind_sensor_output(sensor, self.FOLDER_SEM_LIDAR_VELODYNE, self.NamingPolicy(extension='bin'))
        self.bind_sensor_output(sensor, self.FOLDER_SEM_LIDAR_LABLE, self.NamingPolicy(extension='label'))

        return self

    def bind_sensor_output(self, sensor: CarlaSensor, folder_path: str = None, naming_policy: 'DatasetDumper.NamingPolicy' = None) -> Self:
        """绑定传感器数据输出到内存缓存, 并追踪非主相机以外的其他相机传感器
        
        Args:
            sensor (CarlaSensor): 传感器
            folder_path (str): 文件夹路径
            naming_policy (NamingPolicy, optional): 命名策略. 默认为 None, 将根据传感器类型自动确定.
        
        Returns:
            Self: 返回自身
        """
        # 如果是相机传感器且不是主相机，则添加到其他相机列表
        if sensor.is_camera:
            if sensor != self._main_camera and sensor not in self._other_cameras:
                self._other_cameras.append(sensor)
        
        # 调用父类方法
        return super().bind_sensor_output(sensor, folder_path, naming_policy)

    def _flush_data(self, data: BaseData, file_path: str) -> Self:
        """将传感器数据导出到磁盘

        Args:
            data (BaseData): 传感器数据
            file_path (str): 文件路径

        Returns:
            Self: 返回自身
        """
        if isinstance(data, Image):
            data.to_file(file_path)
            return self
        if isinstance(data, PointCloud):
            raw = data.raw
            if file_path.endswith('.bin'):
                points = raw[:, :3].astype(np.float32).copy()
                points[:, 1] *= -1
                intensity = np.ones((points.shape[0], 1), dtype=np.float32)
                bin_points = np.hstack((points, intensity))
                bin_points.tofile(file_path)
                return self

            if file_path.endswith('.label'):
                semantic_tags = np.rint(raw[:, 6]).astype(np.int32)
                object_ids = np.rint(raw[:, 5]).astype(np.int32)

                mapped_semantics = np.zeros_like(semantic_tags, dtype=np.uint16)
                for carla_id, kitti_id in self.CARLA_KITTI_SEMANTIC_MAPPING.items():
                    mapped_semantics[semantic_tags == carla_id] = kitti_id

                instance_ids = np.clip(object_ids, 0, np.iinfo(np.uint16).max).astype(np.uint16)
                labels = np.column_stack((mapped_semantics, instance_ids))
                labels.tofile(file_path)
                return self
        if isinstance(data, StringIO):
            if file_path.endswith(self.FILE_TIMESTAMP) or file_path.endswith(self.FILE_POSE):
                content = data.getvalue()
                with open(file_path, 'w') as f:
                    f.write(content)
                data.close()
                return self
            else:
                raise ValueError(f'Unsupported file type: {file_path}')
        raise ValueError(f'Unsupported sensor data type: {type(data)}')

    def _ensure_main_sensors_ready(self, _) -> Self:
        """当没有主摄像头和主激光雷达时, 系统退出"""
        if self._main_camera is None or self._main_lidar is None:
            self.logger.critical('Program Logic Error: No main camera and lidar defined, system exit')
            raise SystemExit(429)
        return self

    def _tick_cache_timestamp(self, snapshot: carla.WorldSnapshot) -> Self:
        """在 TICK 时缓存时间戳
        
        时间戳以秒为单位, 使用科学记数法, 保留小数点后 6 位, 例如: 8.000000e-01
        """
        # 首次调用时的初始化
        if self._file_timestamp is None:
            self._file_timestamp = os.path.join(self._folder_path, self.FILE_TIMESTAMP)
            self._file_timestamp = os.path.abspath(self._file_timestamp)
            with open(self._file_timestamp, 'w') as f:
                f.write('')
            self.logger.debug(f'Timestamp file is created: {self._file_timestamp}')
            
            self._dataset[self._file_timestamp] = StringIO()
            self._timestamp_offset = snapshot.timestamp.elapsed_seconds
            self.logger.debug(f'Timestamp offset is set to: {self._timestamp_offset}')

        # 缓存时间戳
        timestamp = snapshot.timestamp.elapsed_seconds - self._timestamp_offset
        self._dataset[self._file_timestamp].write(f'{timestamp:.6e}\n')
        
        return self

    def _tick_cache_pose(self, snapshot: carla.WorldSnapshot) -> Self:
        """在 TICK 时缓存主相机的位姿数据

        主相机位姿数据, 用于计算相对位姿, 使用 KITTI 坐标系, 格式为 12 个浮点数, 按行展开, 保留小数点后 6 位
        """
        if self._main_camera is None:
            return self

        # 首次调用时的初始化
        if self._file_pose is None:
            self._file_pose = os.path.join(self._folder_path, self.FILE_POSE)
            self._file_pose = os.path.abspath(self._file_pose)
            with open(self._file_pose, 'w') as f:
                f.write('')
            self.logger.debug(f'Pose file is created: {self._file_pose}')
            
            self._dataset[self._file_pose] = StringIO()
            
            # 获取初始帧的位姿并转换为 KITTI 坐标系
            cam_0_tf_init = self._main_camera.tf_now
            cam_0_matrix_init = np.array(cam_0_tf_init.get_matrix())
            self._pose_offset = self._carla_to_kitti_transform(cam_0_matrix_init, self._main_camera)
            self.logger.debug(f'Pose offset is set')

        # 获取当前帧的位姿
        cam_0_tf = self._main_camera.tf_now
        cam_0_matrix = np.array(cam_0_tf.get_matrix())
        cam_0_matrix_kitti = self._carla_to_kitti_transform(cam_0_matrix, self._main_camera)
        
        # 计算当前帧相对于初始帧的位姿变换
        # 公式: T_relative = T_offset^-1 * T_current
        pose_relative = np.linalg.inv(self._pose_offset) @ cam_0_matrix_kitti
        
        # 提取 3×4 变换矩阵
        pose_matrix = pose_relative[:3, :]
        
        # 横向展开为 1×12 的行向量, 格式化为科学计数法, 保留小数点后 6 位
        pose_matrix_flat = pose_matrix.flatten()
        pose_matrix_str = ' '.join([f'{value:.6e}' for value in pose_matrix_flat])
        
        # 缓存到位姿文件
        self._dataset[self._file_pose].write(f'{pose_matrix_str}\n')
        
        return self

    def _carla_to_kitti_transform(self, matrix_4x4: np.ndarray, sensor: CarlaSensor) -> np.ndarray:
        """将 CARLA 坐标系的变换矩阵转换为 KITTI 坐标系

        CARLA 坐标系: 左手坐标系 (X前, Y右, Z上)
        KITTI 坐标系: 右手坐标系
            - 相机: (X右, Y下, Z前)
            - 激光雷达: (X前, Y左, Z上)

        转换公式:
            - 旋转矩阵: R_kitti = O @ R_carla @ O^T
            - 平移向量: t_kitti = O @ t_carla
        其中 O 是根据传感器类型选择的坐标系转换矩阵。

        Args:
            matrix_4x4 (np.ndarray): CARLA 坐标系的 4x4 变换矩阵
            sensor (CarlaSensor): 传感器实例, 用于判断传感器类型 (相机或激光雷达)

        Returns:
            np.ndarray: KITTI 坐标系的 4x4 变换矩阵

        Raises:
            ValueError: 如果传感器类型不是相机或激光雷达
        """
        if sensor.is_camera:
            # CARLA相机: X前, Y右, Z上 -> KITTI相机: X右, Y下, Z前
            orientation_transform = np.array([
                [0, 0, 1],
                [1, 0, 0],
                [0, -1, 0]
            ])
        elif sensor.is_lidar:
            # CARLA: X前, Y右, Z上 -> KITTI: X前, Y左, Z上 (右手系)
            orientation_transform = np.array([
                [1, 0, 0],
                [0, -1, 0],
                [0, 0, 1]
            ])
        else:
            raise ValueError(f"Unsupported sensor type: {sensor.bp.id}")

        # 提取旋转矩阵和平移向量
        R_carla = matrix_4x4[:3, :3]
        t_carla = matrix_4x4[:3, 3]

        # 转换旋转矩阵: R_kitti = O @ R_carla @ O^T
        R_kitti = orientation_transform @ R_carla @ orientation_transform.T
        # 转换平移向量: t_kitti = O @ t_carla
        t_kitti = orientation_transform @ t_carla

        # 构建 KITTI 坐标系的 4x4 变换矩阵
        matrix_kitti = np.eye(4)
        matrix_kitti[:3, :3] = R_kitti
        matrix_kitti[:3, 3] = t_kitti

        return matrix_kitti

    def _calc_and_flush_calib(self):
        """计算并导出 KITTI 格式的标定文件, 包含对坐标系的转换"""
        if self._main_camera is None or self._main_lidar is None:
            self.logger.critical('Program Logic Error: Main camera or lidar not set')
            raise SystemExit(429)

        # 创建标定文件
        self._file_calib = os.path.join(self._folder_path, self.FILE_CALIB)
        self._file_calib = os.path.abspath(self._file_calib)
        with open(self._file_calib, 'w') as f:
            f.write('')
        self.logger.info(f'Calib file is created: {self._file_calib}')
        
        # 获取传感器当前变换
        cam_0_tf = self._main_camera.tf_now
        lidar_tf = self._main_lidar.tf_now
        
        # 获取主相机内参矩阵 K (3×3)
        K = self._main_camera.get_camera_intrinsics_matrix()
        
        # 获取传感器变换矩阵 (4×4)
        cam_0_matrix = np.array(cam_0_tf.get_matrix())
        lidar_matrix = np.array(lidar_tf.get_matrix())
        cam_0_matrix_kitti = self._carla_to_kitti_transform(cam_0_matrix, self._main_camera)
        lidar_matrix_kitti = self._carla_to_kitti_transform(lidar_matrix, self._main_lidar)
        
        # 计算 P0 投影矩阵 (3×4): P0 = K * [I|0], P0 即为 CAM0 相对于自身的变换矩阵
        R_cam0_relative = np.eye(3)
        t_cam0_relative = np.zeros((3, 1))
        RT_cam0 = np.hstack((R_cam0_relative, t_cam0_relative))
        P0 = K @ RT_cam0
        
        # 计算激光雷达到 CAM0 的变换矩阵 Tr (3×4)
        T_cam0_kitti = cam_0_matrix_kitti.copy()
        T_lidar_kitti = lidar_matrix_kitti.copy()
        lidar_to_cam0 = np.linalg.inv(T_cam0_kitti) @ T_lidar_kitti
        Tr = lidar_to_cam0[:3, :]
        
        # 计算其他相机的投影矩阵 P_n (3×4)
        other_camera_projections = []
        for cam in self._other_cameras:
            if cam is None:
                continue
            
            # 获取相机内参矩阵
            cam_K = cam.get_camera_intrinsics_matrix()
            
            # 获取相机变换并转换到 KITTI 坐标系
            cam_tf = cam.tf_now
            cam_matrix = np.array(cam_tf.get_matrix())
            cam_matrix_kitti = self._carla_to_kitti_transform(cam_matrix, cam)
            
            # 计算相机相对于 CAM0 的变换
            # 公式: T_cam_relative = T_cam0^-1 * T_cam
            T_cam_kitti = cam_matrix_kitti.copy()
            cam_to_cam0 = np.linalg.inv(T_cam0_kitti) @ T_cam_kitti
            R_cam_relative = cam_to_cam0[:3, :3]
            t_cam_relative = cam_to_cam0[:3, 3].reshape(3, 1)
            
            # 计算投影矩阵 P = K * [R|t]
            RT_cam = np.hstack((R_cam_relative, t_cam_relative)) 
            P_cam = cam_K @ RT_cam 
            other_camera_projections.append(P_cam)
        
        # 写入标定文件
        with open(self._file_calib, 'w') as f:
            # P0
            f.write('P0:')
            f.write(' '.join([f'{value:.12e}' for value in P0.flatten()]))
            f.write('\n')
            
            # Pn
            for i, P_cam in enumerate(other_camera_projections, start=1):
                f.write(f'P{i}:')
                f.write(' '.join([f'{value:.12e}' for value in P_cam.flatten()]))
                f.write('\n')
            
            # Tr
            f.write('Tr:')
            f.write(' '.join([f'{value:.12e}' for value in Tr.flatten()]))
            f.write('\n')
        
        self.logger.debug(f'Calib file is created: {self._file_calib}')
        return self

    def _log_result(self) -> None:
        """记录导出结果"""
        # 检查主文件夹是否存在
        if not os.path.exists(self._folder_path):
            self.logger.error(f'Dataset export result check: False')
            self.logger.error(f'Main folder does not exist: "{self._folder_path}"')
            return
        
        # 获取所有子文件夹
        subfolders = []
        for item in os.listdir(self._folder_path):
            item_path = os.path.join(self._folder_path, item)
            if os.path.isdir(item_path):
                subfolders.append(item_path)
        
        # 统计每个子文件夹中的文件数量
        file_counts = {}
        for subfolder in subfolders:
            folder_name = os.path.basename(subfolder)
            files = [f for f in os.listdir(subfolder) if os.path.isfile(os.path.join(subfolder, f))]
            file_counts[folder_name] = len(files)

        # 统计 pose 和 time 的有效行数量
        pose_lines = 0
        time_lines = 0
        with open(self._file_pose, 'r') as f:
            for line in f:
                if line.strip():
                    pose_lines += 1
        with open(self._file_timestamp, 'r') as f:
            for line in f:
                if line.strip():
                    time_lines += 1
        
        # 检查文件数量是否一致
        counts = list(file_counts.values())
        is_consistent = len(set(counts)) == 1
        
        # 打印结果
        if is_consistent:
            self.logger.info(f'Dataset export result check: True')
        else:
            self.logger.error(f'Dataset export result check: False')
            
        for folder_name, count in file_counts.items():
            self.logger.debug(f'Folder "{folder_name}": {count} file(s)')
        self.logger.debug(f'Pose file lines: {pose_lines}')
        self.logger.debug(f'Time file lines: {time_lines}')
        return self