from queue import Queue
import carla
import numpy as np
import cv2
import torch
from copy import deepcopy
from enum import Enum
from typing import Dict, Any, List
from typing_extensions import Unpack
from ultralytics import YOLO
from ultralytics.engine.results import Results

from shared.simulator import CarlaContext, CarlaBlueprints, CarlaTransform, CarlaSensor
from shared.simulator import CarlaVehicle
from shared.data import Image
from shared.data import Collision


class YoloAEBVehicle(CarlaVehicle):

    CAM_FRONT_NAME = 'CAM_FRONT'
    CAM_FRONT_TF = CarlaTransform(x=0.0, y=0.0, z=1.85, yaw=0.0)

    CAM_GAME_NAME = 'CAM_GAME'
    CAM_GAME_TF = CarlaTransform(x=-5.5, y=0.0, z=2.5, pitch=-15.0)

    LIDAR_NAME = 'LIDAR'
    LIDAR_TF = CarlaTransform(x=0.0, y=0.0, z=2.2)

    COLLISION_NAME = 'COLLISION'
    COLLISION_TF = CarlaTransform(x=0.0, y=0.0, z=0.0)

    # 检测区域，使用像素百分比 (x%, y%)
    DETECT_AREA = [
        (17, 80),
        (100-17, 80),
        (100-49, 50),
        (49, 50),
    ]
    DETECT_CLASS_NAMES = [
        'person',
        'car',
        'truck',
        'bus',
        'motorcycle',
        'bicycle',
    ]
    DETECT_DRAW_DEBUG = False
    DETECT_DRAW_DEBUG_FILE = 'yolo_detect_debug.png'

    DETECT_THR_CONF = 0.75          # 置信度阈值
    DETECT_THR_AREA = 0.3           # 检测框面积 与 同检测区域相交面积 的比值
    DETECT_THR_CONTINUOUS = 2       # 连续检测到目标的帧数

    PREF_THR_STOP_SPEED_KMH = 3.0

    class ControlMode(Enum):
        NONE = 0
        CARLA_AUTOPILOT = 1
        EXTERNAL_AUTOPILOT = 2
        MANUAL = 3
        AEB = 4
        STOP = 5

    def __init__(
        self,
        context: 'CarlaContext',
        tf: CarlaTransform | carla.Transform,
        bp: carla.ActorBlueprint | str | CarlaBlueprints = CarlaBlueprints.VEHICLE_TESLA_MODEL3,
        name: str = 'Player',
        **attributes: Unpack[Dict[str, Any]],
    ):
        self._context = context
        self._yolo_model = YOLO(context.project_root / 'apps' / 'huawei' / 'yolo26n.pt')
        self._brake_force: carla.Vector3D | None = None
        self._control_mode = self.ControlMode.NONE
        self._reached_speed_kmh = 0.0
        self._target_speed_kmh = 0.0
        self._detect_continuous_count = 0
        self._is_reached_speed = False
        self._cache_speed: Queue[float] = Queue(maxsize=4)

        # RESULTS
        self.is_safe_stop = False
        self.is_collision = False
        self.last_accpet_acceleration = 0.0

        super().__init__(
            context=context,
            bp=bp,
            tf=tf,
            name=name,
            **attributes,
        )

    def __post_init__(self):
        super().__post_init__()
        
        self._cam_front = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.name + '_' + self.CAM_FRONT_NAME,
            tf=self.CAM_FRONT_TF,
            parent=self,
        )

        self._cam_game = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.name + '_' + self.CAM_GAME_NAME,
            tf=self.CAM_GAME_TF,
            parent=self,
        )

        self._lidar = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_LIDAR_RAY_CAST_SEMANTIC,
            name=self.name + '_' + self.LIDAR_NAME,
            tf=self.LIDAR_TF,
            parent=self,
            rotation_frequency=self._context.fps,
            points_per_second=120_000 * self._context.fps,
            channels=64,
            range=120,
            upper_fov=2,
            lower_fov=-24.5,
        )

        self._collision = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_OTHER_COLLISION,
            name=self.name + '_' + self.COLLISION_NAME,
            tf=self.COLLISION_TF,
            parent=self,
        )

        self._cam_front.hook_sensor_data_ready.append(self._detect)
        self._collision.hook_sensor_data_ready.append(self._on_collision)
        self._context.hook_on_tick.append(self._hookfunc_update_speed)
        self._context.hook_on_tick.append(self._hookfunc_on_stop)
        self._context.hook_on_tick.append(self._hookfunc_on_reached_speed)
        self._context.hook_on_tick.append(self._hookfunc_dump_accept_acceleration)

    def clear(self):
        # 禁用常速度模式，重置速度状态
        if self.is_alive:
            self.actor.disable_constant_velocity()
        
        self._detect_continuous_count = 0
        self._control_mode = self.ControlMode.NONE
        self._reached_speed_kmh = 0.0
        self._target_speed_kmh = 0.0
        self._is_reached_speed = False
        with self._cache_speed.mutex:
            self._cache_speed.queue.clear()
        self.is_safe_stop = False
        self.is_collision = False
        self.last_accpet_acceleration = 0.0

    def respawn_front_camera(self, camera_bp: carla.ActorBlueprint) -> CarlaSensor:
        """动态式的重新构建前置摄像头"""
        self._cam_front.destroy()
        self._cam_front = self._context.actors.create_sensor(
            bp=camera_bp,
            name=self.name + '_' + self.CAM_FRONT_NAME,
            tf=self.CAM_FRONT_TF,
            parent=self,
        )
        self._cam_front.spawn()
        self._cam_front.hook_sensor_data_ready.append(self._detect)
        return self._cam_front

    @property
    def last_accept_speed(self) -> float:
        if self._cache_speed.empty():
            return 0
        return self._cache_speed.queue[-2]

    def destroy(self):
        self._context.hook_on_tick.remove(self._hookfunc_update_speed)
        self._context.hook_on_tick.remove(self._hookfunc_on_stop)
        self._context.hook_on_tick.remove(self._hookfunc_on_reached_speed)
        self._context.hook_on_tick.remove(self._hookfunc_dump_accept_acceleration)
        return super().destroy()

    def apply_speed(self, speed_kmh: float):
        # 获取车头朝向向量（可能包含 z 分量）
        forward_vector = self.tf_now.get_forward_vector()
        # 将 z 分量设为 0，强制在水平面上
        forward_vector = carla.Vector3D(
            x=forward_vector.x,
            y=forward_vector.y,
            z=0.0,
        )
        # 归一化为单位向量
        forward_vector = forward_vector.make_unit_vector()
        # 计算速度向量（km/h 转 m/s）
        speed_ms = speed_kmh / 3.6
        forward_vector = forward_vector * speed_ms * -1
        self.actor.enable_constant_velocity(forward_vector)
        self.logger.info(f"Set speed to {speed_kmh} km/h")
        self._control_mode = self.ControlMode.EXTERNAL_AUTOPILOT
        self._target_speed_kmh = speed_kmh

    def apply_aeb(self):
        self.logger.info(f"Apply AEB")
        self.actor.disable_constant_velocity()  # 解除速度请求
        self.actor.apply_control(carla.VehicleControl(brake=1, hand_brake=True))

    def apply_stop(self):
        self.logger.info(f"Apply STOP")
        # 应用刹车
        self.actor.apply_control(carla.VehicleControl(
            brake=1.0,
        ))
        self._control_mode = self.ControlMode.STOP

    def _hookfunc_update_speed(self, snapshot: carla.WorldSnapshot):
        if not self.is_alive:
            return
        self._reached_speed_kmh = max(self.speed_kmh, self._reached_speed_kmh)
        if self._cache_speed.full():
            self._cache_speed.get()
        self._cache_speed.put(self.speed_ms)

    def _hookfunc_on_stop(self, snapshot: carla.WorldSnapshot):
        if not self.is_alive:
            return
        if self.speed_kmh > self.PREF_THR_STOP_SPEED_KMH:
            return
        if self._target_speed_kmh == 0.0:
            return
        if self._reached_speed_kmh < self._target_speed_kmh * 0.9:
            return
        if self._control_mode == self.ControlMode.STOP:
            return

        self.logger.info(f"Speed below threshold, detected stop")
        self.is_safe_stop = True
        self.apply_stop()

    def _hookfunc_on_reached_speed(self, snapshot: carla.WorldSnapshot):
        if not self.is_alive:
            return
        if self._reached_speed_kmh < self._target_speed_kmh * 0.95:
            return
        if self._is_reached_speed:
            return
        self._is_reached_speed = True
        self.logger.info(f"Reached speed: {self._reached_speed_kmh:.2f} km/h")
        self.actor.disable_constant_velocity()
        return self

    def _hookfunc_dump_accept_acceleration(self, snapshot: carla.WorldSnapshot):
        """
        记录当前帧的加速度, 用于弥补 CARLA 的物理模拟误差
        """
        if not self.is_alive:
            return
        a = self.actor.get_acceleration().length()
        if a < 2.0 or a > 40.0:
            return
        self.last_accpet_acceleration = a

    def _on_collision(self, collision: Collision):
        self.logger.info(f"Collision detected")
        self.apply_stop()
        self.is_collision = True
        self.is_safe_stop = False

    def _detect(self, image: Image):
        bgr_image = image._raw[:, :, :3]
        rgb_image = bgr_image[:, :, ::-1]
        
        # 使用 YOLO 模型进行检测
        results = self._yolo_model(rgb_image, verbose=False)

        # 筛选检测结果
        results = self._filter_detect_class(results)
        results = self._filter_detect_area(results, image.width, image.height)
        results = self._filter_detect_conf(results)

        if len(results) == 0:
            self._detect_continuous_count = 0
        else:
            self._detect_continuous_count += 1

        # 打印检测结果
        results_str = ""
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                conf = float(box.conf[0])
                results_str += f"{cls_name} {conf:.2f} "
        if len(results) > 0:
            self.logger.debug(f"Detect results: {results_str}")

        if self.DETECT_DRAW_DEBUG:
            debug_image = self._draw_detect_area(image)
            debug_image = self._draw_boxes(debug_image, results)
            debug_image.to_file(self.DETECT_DRAW_DEBUG_FILE)

        if len(results) == 0:
            return
        if self._detect_continuous_count < self.DETECT_THR_CONTINUOUS:
            return
        if self._control_mode == self.ControlMode.AEB or self._control_mode == self.ControlMode.STOP:
            return

        self._control_mode = self.ControlMode.AEB
        self.apply_aeb()

    def _filter_detect_class(self, results: List[Results]) -> List[Results]:
        """根据类别名称过滤检测结果"""
        filtered_results = []
        for result in results:
            valid_indices = []
            
            for i, box in enumerate(result.boxes):
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                
                # 保留类别名称在 DETECT_CLASS_NAMES 中的检测框
                if cls_name in self.DETECT_CLASS_NAMES:
                    valid_indices.append(i)
            
            # 如果存在有效的检测框，创建新的 Results 对象
            if valid_indices:
                filtered_result = deepcopy(result)
                valid_indices_tensor = torch.tensor(valid_indices, dtype=torch.long)
                filtered_result.boxes = result.boxes[valid_indices_tensor]
                filtered_results.append(filtered_result)
        
        return filtered_results

    def _filter_detect_conf(self, results: List[Results]) -> List[Results]:
        """根据置信度过滤检测结果"""
        filtered_results = []
        for result in results:
            valid_indices = []
            
            for i, box in enumerate(result.boxes):
                if box.conf[0] >= self.DETECT_THR_CONF:
                    valid_indices.append(i)
            
            # 如果存在有效的检测框，创建新的 Results 对象
            if valid_indices:
                filtered_result = deepcopy(result)
                valid_indices_tensor = torch.tensor(valid_indices, dtype=torch.long)
                filtered_result.boxes = result.boxes[valid_indices_tensor]
                filtered_results.append(filtered_result)
        
        return filtered_results

    def _filter_detect_area(self, results: List[Results], image_width: int, image_height: int) -> List[Results]:
        # 将检测区域从百分比转换为像素坐标
        detect_area_pixels = np.array([
            (int(x_percent * image_width / 100), int(y_percent * image_height / 100))
            for x_percent, y_percent in self.DETECT_AREA
        ], dtype=np.int32)
        
        # 创建检测区域的 mask
        detect_area_mask = np.zeros((image_height, image_width), dtype=np.uint8)
        cv2.fillPoly(detect_area_mask, [detect_area_pixels], 255)
        
        filtered_results = []
        for result in results:
            # 获取所有检测框的索引
            valid_indices = []
            
            for i, box in enumerate(result.boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                # 转换为整数并裁剪到图像边界内
                x1 = max(0, min(int(x1), image_width - 1))
                y1 = max(0, min(int(y1), image_height - 1))
                x2 = max(0, min(int(x2), image_width - 1))
                y2 = max(0, min(int(y2), image_height - 1))
                
                # 确保边界框有效
                if x1 >= x2 or y1 >= y2:
                    continue
                
                # 计算检测框面积
                box_area = (x2 - x1) * (y2 - y1)
                if box_area == 0:
                    continue
                
                # 创建检测框的 mask
                box_mask = np.zeros((image_height, image_width), dtype=np.uint8)
                cv2.rectangle(box_mask, (x1, y1), (x2, y2), 255, -1)
                
                # 计算相交区域
                intersection_mask = cv2.bitwise_and(detect_area_mask, box_mask)
                intersection_area = np.sum(intersection_mask > 0)
                
                # 计算相交面积与检测框面积的比值
                area_ratio = intersection_area / box_area
                
                # 保留比值大于等于阈值的检测框
                if area_ratio >= self.DETECT_THR_AREA:
                    valid_indices.append(i)
            
            # 如果存在有效的检测框，创建新的 Results 对象
            if valid_indices:
                # 使用索引过滤 boxes
                filtered_result = deepcopy(result)
                # 将索引转换为 tensor 以确保兼容性
                valid_indices_tensor = torch.tensor(valid_indices, dtype=torch.long)
                filtered_result.boxes = result.boxes[valid_indices_tensor]
                filtered_results.append(filtered_result)
        
        return filtered_results

    def _draw_detect_area(self, image: Image) -> Image:
        image = deepcopy(image)
        detect_area_pixels = np.array([
            (int(x_percent * image.width / 100), int(y_percent * image.height / 100))
            for x_percent, y_percent in self.DETECT_AREA
        ])

        mask = np.zeros((image.height, image.width), dtype=np.uint8)
        cv2.fillPoly(mask, [detect_area_pixels], 255)

        # 创建绿色叠加层（BGR格式）
        green_overlay = np.zeros((image.height, image.width, 3), dtype=np.uint8)
        green_overlay[:, :] = (0, 255, 0)  # 绿色，BGR格式

        # 30%透明度混合：只在mask区域内混合BGR通道，Alpha通道保持255
        alpha = 0.3
        for c in range(3):
            image._raw[:, :, c] = np.where(
                mask > 0,
                (image._raw[:, :, c] * (1 - alpha) + green_overlay[:, :, c] * alpha).astype(np.uint8),
                image._raw[:, :, c]
            )
        # Alpha通道保持255（完全不透明）
        image._raw[:, :, 3] = 255
        
        return image

    def _draw_boxes(self, image: Image, results: List[Results]) -> Image:
        image = deepcopy(image)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        
        # 提取BGR通道用于绘制（OpenCV函数需要3通道）
        bgr_image = image._raw[:, :, :3].copy()
        
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                cls_name = result.names[cls_id]
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                # 转换为整数并裁剪到图像边界内
                x1 = max(0, min(int(x1), image.width - 1))
                y1 = max(0, min(int(y1), image.height - 1))
                x2 = max(0, min(int(x2), image.width - 1))
                y2 = max(0, min(int(y2), image.height - 1))
                
                # 确保边界框有效（左上角在右下角之前）
                if x1 >= x2 or y1 >= y2:
                    continue
                
                # 绘制边界框（红色，BGR格式）
                cv2.rectangle(bgr_image, (x1, y1), (x2, y2), (0, 0, 255), 2)
                
                # 准备标签文本
                label = f"{cls_name} {conf:.2f}"
                
                # 计算文字大小
                (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
                
                # 标签位置：边界框左上角，如果上方空间不足则放在框内
                label_x = x1
                label_y = y1 - 10 if y1 >= text_height + 10 else y1 + text_height + 10
                
                # 确保标签在图像范围内
                label_y = max(text_height, min(label_y, image.height - baseline - 1))
                
                # 绘制标签背景矩形（红色背景，BGR格式）
                padding = 4
                bg_x1 = max(0, label_x - padding)
                bg_y1 = max(0, label_y - text_height - padding)
                bg_x2 = min(image.width, label_x + text_width + padding)
                bg_y2 = min(image.height, label_y + baseline + padding)
                cv2.rectangle(bgr_image, (bg_x1, bg_y1), (bg_x2, bg_y2), (0, 0, 255), -1)
                
                # 绘制标签文字（白色，BGR格式）
                cv2.putText(bgr_image, label, (label_x, label_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
        
        # 将绘制结果写回BGRA图像（保持Alpha通道为255）
        image._raw[:, :, :3] = bgr_image
        image._raw[:, :, 3] = 255  # Alpha通道保持完全不透明

        return image


    @property
    def cam_front(self) -> CarlaSensor:
        return self._cam_front

    @property
    def lidar(self) -> CarlaSensor:
        return self._lidar
    
    @property
    def cam_game(self) -> CarlaSensor:
        return self._cam_game