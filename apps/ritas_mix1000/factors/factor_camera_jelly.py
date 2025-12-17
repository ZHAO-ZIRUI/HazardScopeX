import numpy as np
import cv2
import carla
from shared.scenarios import Factor
from shared.simulator import *
from shared.data import Image


class FactorCameraJelly(Factor):
    NAME = 'F_CameraJelly'

    def __init__(
        self, 
        context: CarlaContext, 
        sensor: CarlaSensor,
        *,
        intensity: float = 2.0,
        focal_length: float | None = None,
    ):
        """
        模拟滚动快门果冻效应
        
        基于sensor的实际tf变化来计算果冻效应。
        滚动快门从上到下逐行扫描，在扫描过程中sensor的tf发生变化，
        导致每一行对应不同的视角，产生扭曲效果。
        
        Args:
            intensity: 效果强度倍数，值越大效果越明显（默认1.0）
            focal_length: 相机焦距（像素），如果为None则根据图像尺寸估算
        """
        super().__init__(context)
        self._sensor = sensor
        self._prev_tf: carla.Transform | None = None
        self._intensity = intensity
        self._focal_length = focal_length

    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def _interpolate_angle(self, a1: np.ndarray, a2: np.ndarray, t: np.ndarray) -> np.ndarray:
        """向量化的角度插值，处理角度环绕"""
        diff = a2 - a1
        # 处理角度环绕（-180到180）
        diff = np.where(diff > 180, diff - 360, diff)
        diff = np.where(diff < -180, diff + 360, diff)
        result = a1 + diff * t
        result = np.where(result > 180, result - 360, result)
        result = np.where(result < -180, result + 360, result)
        return result

    def on_sensor_data_recv(self, data: Image) -> Image:
        """
        模拟滚动快门果冻效应
        滚动快门从上到下逐行扫描，在扫描过程中sensor的tf发生变化，
        导致每一行对应不同的视角，产生扭曲效果
        """
        height, width = data._raw.shape[:2]
        
        # 获取当前sensor的tf
        current_tf = self._sensor.tf_now
        
        # 如果是第一帧，没有上一帧的tf，直接返回
        if self._prev_tf is None:
            self._prev_tf = current_tf
            return data
        
        # 提取角度值（向量化处理）
        prev_yaw = self._prev_tf.rotation.yaw
        prev_pitch = self._prev_tf.rotation.pitch
        curr_yaw = current_tf.rotation.yaw
        curr_pitch = current_tf.rotation.pitch
        
        # 创建扫描进度数组（每一行对应一个进度值）
        scan_progress = np.arange(height, dtype=np.float32) / height
        
        # 向量化插值计算每一行的角度
        yaw_interp = self._interpolate_angle(
            np.full(height, prev_yaw),
            np.full(height, curr_yaw),
            scan_progress
        )
        pitch_interp = self._interpolate_angle(
            np.full(height, prev_pitch),
            np.full(height, curr_pitch),
            scan_progress
        )
        
        # 计算角度差（相对于当前tf）
        yaw_diff = np.radians(yaw_interp - curr_yaw)
        pitch_diff = np.radians(pitch_interp - curr_pitch)
        
        # 估算焦距（如果未提供）
        if self._focal_length is None:
            # 假设水平视场角约为90度，估算焦距
            fov_horizontal = np.radians(90)
            focal_length = width / (2.0 * np.tan(fov_horizontal / 2.0))
        else:
            focal_length = self._focal_length
        
        # 创建坐标网格
        y_coords, x_coords = np.meshgrid(
            np.arange(height, dtype=np.float32), 
            np.arange(width, dtype=np.float32), 
            indexing='ij'
        )
        
        center_x = width / 2.0
        center_y = height / 2.0
        
        # 将坐标转换为以图像中心为原点的坐标系（归一化到焦距）
        x_centered = (x_coords - center_x) / focal_length
        y_centered = (y_coords - center_y) / focal_length
        
        # 向量化应用旋转变换
        # 将角度差扩展到整个图像（每行使用对应的角度）
        yaw_diff_2d = np.tile(yaw_diff[:, np.newaxis], (1, width)) * self._intensity
        pitch_diff_2d = np.tile(pitch_diff[:, np.newaxis], (1, width)) * self._intensity
        
        # 应用旋转变换（使用更准确的模型）
        # 对于yaw旋转（绕垂直轴），主要影响x坐标
        # 对于pitch旋转（绕水平轴），主要影响y坐标
        # 使用tan函数更准确，特别是在角度较大时
        
        # yaw旋转：x' = x * cos(yaw) - y * sin(yaw) / cos(pitch)
        # 简化：对于小角度，tan(yaw) ≈ yaw
        # 考虑焦距的影响：像素位移 = 焦距 * tan(角度)
        x_displaced_normalized = x_centered - y_centered * np.tan(yaw_diff_2d)
        y_displaced_normalized = y_centered - x_centered * np.tan(pitch_diff_2d)
        
        # 转换回像素坐标
        x_coords_displaced = x_displaced_normalized * focal_length + center_x
        y_coords_displaced = y_displaced_normalized * focal_length + center_y
        
        # 限制坐标范围
        x_coords_displaced = np.clip(x_coords_displaced, 0, width - 1)
        y_coords_displaced = np.clip(y_coords_displaced, 0, height - 1)
        
        # 使用OpenCV的remap进行快速重采样（比手动双线性插值快得多）
        map_x = x_coords_displaced.astype(np.float32)
        map_y = y_coords_displaced.astype(np.float32)
        data._raw = cv2.remap(data._raw, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        
        # 更新上一帧的tf
        self._prev_tf = current_tf
        
        return data