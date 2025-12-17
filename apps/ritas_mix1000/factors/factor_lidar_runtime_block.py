import numpy as np
import random
from shared.scenarios import Factor
from shared.simulator import *
from shared.data import PointCloud


class FactorLidarRuntimeBlock(Factor):
    NAME = 'F_LidarRuntimeBlock'

    def __init__(
        self, 
        context: CarlaContext, 
        sensor: CarlaSensor,
        *,
        start_horizontal_min: float = -40.0,
        start_horizontal_max: float = -30.0,
        target_horizontal_min: float = 20.0,
        target_horizontal_max: float = 30.0,
        vertical_min: float = -10.0,
        vertical_max: float = 10.0,
        delay_frames: int = 30,
        move_frames: int = 60,
        block_start_frames: int = 20,
        block_expand_frames: int = 40,
        obstacle_start_distance: float = 100.0,
        obstacle_distance: float = 5.0,
        obstacle_width: float = 1.0,
        obstacle_height: float = 0.5,
        motion_noise: float = 0.15,
        shape_noise: float = 0.1,
    ):
        """
        模拟动态障碍物遮挡雷达
        
        障碍物延迟启动后从初始位置出现, 移动到目标位置, 遮挡点云, 并在遮挡区域偶尔产生噪点.
        障碍物点云为高斯噪声分布, 点数等于被遮挡的点数. 到达最终位置后不再产生点云.
        
        Args:
            start_horizontal_min: 初始水平角度下界(度), 默认-40.0
            start_horizontal_max: 初始水平角度上界(度), 默认-30.0
            target_horizontal_min: 目标水平角度下界(度), 默认20.0
            target_horizontal_max: 目标水平角度上界(度), 默认30.0
            vertical_min: 垂直角度下界(度), 默认-10.0
            vertical_max: 垂直角度上界(度), 默认10.0
            delay_frames: 延迟启动帧数, 默认30
            move_frames: 移动所需的帧数, 默认60
            block_start_frames: 开始遮挡的延迟帧数(障碍物出现后), 默认20
            block_expand_frames: 遮挡范围扩展的帧数, 默认40
            obstacle_start_distance: 障碍物初始距离(米), 默认100.0
            obstacle_distance: 障碍物最终距离(米), 默认5.0
            obstacle_width: 障碍物宽度(米), 默认1.0
            obstacle_height: 障碍物高度(米), 默认0.5
            motion_noise: 运动随机噪声强度(0-1), 控制角度/距离/速度的随机性, 默认0.15
            shape_noise: 形态随机噪声强度(0-1), 控制大小和厚度的随机性, 默认0.1
        """
        super().__init__(context)
        self._sensor = sensor
        self._start_horizontal_min = np.radians(start_horizontal_min)
        self._start_horizontal_max = np.radians(start_horizontal_max)
        self._target_horizontal_min = np.radians(target_horizontal_min)
        self._target_horizontal_max = np.radians(target_horizontal_max)
        self._vertical_min = np.radians(vertical_min)
        self._vertical_max = np.radians(vertical_max)
        self._delay_frames = delay_frames
        self._move_frames = move_frames
        self._block_start_frames = block_start_frames
        self._block_expand_frames = block_expand_frames
        self._obstacle_start_distance = obstacle_start_distance
        self._obstacle_distance = obstacle_distance
        # 障碍物绝对尺寸(米)
        self._obstacle_width = obstacle_width
        self._obstacle_height = obstacle_height
        # 根据motion_noise计算各项运动噪声
        self._motion_noise_angle = np.radians(2.0 * motion_noise)
        self._motion_noise_distance = 0.2 * motion_noise
        self._motion_noise_speed = 0.1 * motion_noise
        # 根据shape_noise计算各项形态噪声
        self._noise_std = 0.02 * shape_noise
        self._shape_noise_size = 0.15 * shape_noise
        self._shape_noise_thickness = 0.02 * shape_noise
        # 固定参数
        self._noise_probability = 0.02
        self._noise_count = 5
        
        self._frame_count = 0
        self._is_started = False
        self._is_moving = False
        self._is_blocking = False
        self._current_horizontal_min = self._start_horizontal_min
        self._current_horizontal_max = self._start_horizontal_max
        self._current_obstacle_distance = obstacle_start_distance
        self._block_start_frame = 0
        self._max_block_distance = obstacle_distance * 10.0  # 最大遮挡距离
        # 用于累积随机噪声的状态
        self._angle_noise_h = 0.0
        self._angle_noise_v = 0.0
        self._distance_noise = 0.0
        self._speed_noise = 0.0

    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def on_sensor_data_recv(self, data: PointCloud) -> PointCloud:
        """
        模拟动态障碍物: 延迟启动, 移动, 产生点云, 遮挡, 产生噪点
        """
        if data.count == 0:
            return data
        
        self._frame_count += 1
        
        # 检查是否应该启动
        if not self._is_started:
            if self._frame_count >= self._delay_frames:
                self._is_started = True
                self._is_moving = True
                self._block_start_frame = self._frame_count + self._block_start_frames
            else:
                return data
        
        # 更新障碍物位置和距离(添加随机性)
        if self._is_moving:
            # 添加速度随机噪声
            speed_noise_delta = np.random.normal(0, self._motion_noise_speed)
            self._speed_noise = self._speed_noise * 0.9 + speed_noise_delta * 0.1  # 平滑噪声
            
            # 计算基础进度, 添加速度噪声
            base_progress = (self._frame_count - self._delay_frames) / self._move_frames
            move_progress = min(1.0, base_progress + self._speed_noise)
            
            # 添加角度随机噪声(平滑变化)
            angle_noise_h_delta = np.random.normal(0, self._motion_noise_angle)
            angle_noise_v_delta = np.random.normal(0, self._motion_noise_angle)
            self._angle_noise_h = self._angle_noise_h * 0.9 + angle_noise_h_delta * 0.1
            self._angle_noise_v = self._angle_noise_v * 0.9 + angle_noise_v_delta * 0.1
            
            # 添加距离随机噪声(平滑变化)
            distance_noise_delta = np.random.normal(0, self._motion_noise_distance)
            self._distance_noise = self._distance_noise * 0.9 + distance_noise_delta * 0.1
            
            # 线性插值从初始位置到目标位置, 添加角度噪声
            base_h_min = self._start_horizontal_min + (self._target_horizontal_min - self._start_horizontal_min) * move_progress
            base_h_max = self._start_horizontal_max + (self._target_horizontal_max - self._start_horizontal_max) * move_progress
            self._current_horizontal_min = base_h_min + self._angle_noise_h
            self._current_horizontal_max = base_h_max + self._angle_noise_h
            
            # 线性插值从初始距离到最终距离, 添加距离噪声
            base_distance = self._obstacle_start_distance + (self._obstacle_distance - self._obstacle_start_distance) * move_progress
            self._current_obstacle_distance = base_distance + self._distance_noise
            # 确保距离不会太小
            self._current_obstacle_distance = max(self._current_obstacle_distance, self._obstacle_distance * 0.5)
            
            if move_progress >= 1.0:
                self._is_moving = False
                self._current_obstacle_distance = self._obstacle_distance
        
        # 检查是否应该开始遮挡
        if self._is_started and not self._is_blocking:
            if self._frame_count >= self._block_start_frame:
                self._is_blocking = True
        
        # 计算当前遮挡距离阈值(渐进扩展)
        # 遮挡距离从当前障碍物距离开始, 逐渐向后扩展
        current_block_distance = self._current_obstacle_distance
        if self._is_blocking:
            block_progress = min(1.0, (self._frame_count - self._block_start_frame) / self._block_expand_frames)
            # 遮挡距离从当前障碍物距离逐渐扩展到最大距离
            current_block_distance = self._current_obstacle_distance + (self._max_block_distance - self._current_obstacle_distance) * block_progress
        
        # 获取xyz坐标
        xyz = data._raw[:, :3]
        x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
        
        # 计算水平角度和垂直角度
        horizontal_angle = np.arctan2(y, x)
        horizontal_distance = np.sqrt(x**2 + y**2)
        vertical_angle = np.arctan2(z, horizontal_distance)
        
        # 计算障碍物中心角度(基于遮挡范围的中心)
        obstacle_center_horizontal = (self._current_horizontal_min + self._current_horizontal_max) / 2
        obstacle_center_vertical = (self._vertical_min + self._vertical_max) / 2
        
        # 根据障碍物绝对尺寸和当前距离计算角度范围
        # 水平角度范围 = 2 * atan(宽度 / 2 / 距离)
        obstacle_size_horizontal_angle = 2 * np.arctan(self._obstacle_width / 2.0 / self._current_obstacle_distance)
        # 垂直角度范围 = 2 * atan(高度 / 2 / 距离)
        obstacle_size_vertical_angle = 2 * np.arctan(self._obstacle_height / 2.0 / self._current_obstacle_distance)
        
        # 计算障碍物的角度范围(以中心为基准)
        obstacle_horizontal_min = obstacle_center_horizontal - obstacle_size_horizontal_angle / 2
        obstacle_horizontal_max = obstacle_center_horizontal + obstacle_size_horizontal_angle / 2
        obstacle_vertical_min = obstacle_center_vertical - obstacle_size_vertical_angle / 2
        obstacle_vertical_max = obstacle_center_vertical + obstacle_size_vertical_angle / 2
        
        # 判断点是否在遮挡范围内(使用遮挡角度范围)
        in_horizontal_range = (horizontal_angle >= self._current_horizontal_min) & (horizontal_angle <= self._current_horizontal_max)
        in_vertical_range = (vertical_angle >= self._vertical_min) & (vertical_angle <= self._vertical_max)
        in_blocked_range = in_horizontal_range & in_vertical_range
        
        # 判断点是否在遮挡距离范围内
        distance = np.sqrt(x**2 + y**2 + z**2)
        
        # 需要遮挡的点: 在角度范围内且在遮挡距离范围内
        # 只有在开始遮挡后才进行遮挡
        if self._is_blocking:
            should_block = in_blocked_range & (distance > self._current_obstacle_distance) & (distance <= current_block_distance)
        else:
            should_block = np.zeros(len(distance), dtype=bool)
        
        # 统计被遮挡的点数
        blocked_count = np.sum(should_block)
        
        # 保留不在遮挡范围内的点
        mask = ~should_block
        data._raw = data._raw[mask]
        
        # 生成障碍物点云: 只在移动过程中生成点云, 到达最终位置后不再产生点云
        if self._is_started and self._is_moving:
            # 如果还没开始遮挡, 生成固定数量的点云
            if not self._is_blocking:
                obstacle_point_count = max(50, blocked_count)  # 至少50个点
            else:
                obstacle_point_count = max(blocked_count, 50)  # 至少50个点, 或等于被遮挡的点数
            
            obstacle_points = self._generate_obstacle_points_gaussian(
                obstacle_center_horizontal, 
                obstacle_center_vertical,
                obstacle_size_horizontal_angle,
                obstacle_size_vertical_angle,
                self._current_obstacle_distance,
                obstacle_point_count
            )
            
            # 确保障碍物点云的格式与原始数据一致
            if data._raw.shape[1] > 3:
                # 如果有额外列(如intensity), 需要填充
                extra_cols = data._raw.shape[1] - 3
                extra_data = np.zeros((obstacle_points.shape[0], extra_cols), dtype=data._raw.dtype)
                obstacle_points_full = np.hstack([obstacle_points, extra_data])
            else:
                obstacle_points_full = obstacle_points
            
            data._raw = np.vstack([data._raw, obstacle_points_full])
        
        # 如果障碍物已到达目标位置, 偶尔在遮挡区域产生噪点
        if not self._is_moving and random.random() < self._noise_probability:
            noise_points = self._generate_noise_points(
                self._current_horizontal_min,
                self._current_horizontal_max,
                self._vertical_min,
                self._vertical_max,
                self._obstacle_distance,
                self._noise_count
            )
            
            if noise_points.shape[0] > 0:
                if data._raw.shape[1] > 3:
                    extra_cols = data._raw.shape[1] - 3
                    extra_data = np.zeros((noise_points.shape[0], extra_cols), dtype=data._raw.dtype)
                    noise_points_full = np.hstack([noise_points, extra_data])
                else:
                    noise_points_full = noise_points
                
                data._raw = np.vstack([data._raw, noise_points_full])
        
        return data
    
    def _generate_obstacle_points_gaussian(
        self, 
        center_h: float, 
        center_v: float,
        size_h: float,
        size_v: float,
        distance: float,
        count: int
    ) -> np.ndarray:
        """生成障碍物点云, 使用高斯噪声分布, 添加形态随机性"""
        # 为每个点生成随机的大小缩放因子(模拟不规则形状)
        size_scale_h = np.random.uniform(1.0 - self._shape_noise_size, 1.0 + self._shape_noise_size, count)
        size_scale_v = np.random.uniform(1.0 - self._shape_noise_size, 1.0 + self._shape_noise_size, count)
        
        # 应用大小缩放
        effective_size_h = size_h * size_scale_h
        effective_size_v = size_v * size_scale_v
        
        # 生成高斯分布的随机角度, 使用有效大小
        h_angles = np.random.normal(center_h, effective_size_h / 3.0, count)
        v_angles = np.random.normal(center_v, effective_size_v / 3.0, count)
        
        # 限制角度在基础范围内
        h_angles = np.clip(h_angles, center_h - size_h/2, center_h + size_h/2)
        v_angles = np.clip(v_angles, center_v - size_v/2, center_v + size_v/2)
        
        # 生成距离的高斯噪声, 添加厚度随机性
        base_distances = np.random.normal(distance, self._noise_std, count)
        # 添加厚度随机变化(模拟障碍物表面不规则)
        thickness_noise = np.random.normal(0, self._shape_noise_thickness, count)
        distances = base_distances + thickness_noise
        distances = np.maximum(distances, distance * 0.5)  # 确保距离不会太小
        
        # 转换为笛卡尔坐标
        x = distances * np.cos(v_angles) * np.cos(h_angles)
        y = distances * np.cos(v_angles) * np.sin(h_angles)
        z = distances * np.sin(v_angles)
        
        points = np.column_stack([x, y, z])
        return points.astype(np.float32)
    
    def _generate_noise_points(
        self,
        h_min: float,
        h_max: float,
        v_min: float,
        v_max: float,
        distance: float,
        count: int
    ) -> np.ndarray:
        """在遮挡区域生成随机噪点"""
        points = []
        for _ in range(count):
            # 随机角度
            h = random.uniform(h_min, h_max)
            v = random.uniform(v_min, v_max)
            # 随机距离(在障碍物后面)
            d = random.uniform(distance * 1.1, distance * 3.0)
            
            # 转换为笛卡尔坐标
            x = d * np.cos(v) * np.cos(h)
            y = d * np.cos(v) * np.sin(h)
            z = d * np.sin(v)
            points.append([x, y, z])
        
        return np.array(points, dtype=np.float32)