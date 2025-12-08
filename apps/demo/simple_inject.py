# 简单的因子注入样例
import numpy as np
import cv2
import random
from pathlib import Path
from shared.data.image import Image
from shared.simulator import *
from shared.utils import Logging
from shared.prefabs import PlayerVehicle
from shared.scenarios import Injector, Factor


class FactorImageTag(Factor):
    NAME = 'F_ImageTag'

    def __init__(self, context: 'CarlaContext', sensor: CarlaSensor):
        super().__init__(context)
        self._sensor = sensor

    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def on_sensor_data_recv(self, data: Image) -> Image:
        # 设置文字参数
        text = 'DEMO FACTOR'
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        
        # 计算文字大小
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        # 计算文字位置（图像中心）
        text_x = (data.width - text_width) // 2
        text_y = (data.height + text_height) // 2
        
        # 设置背景矩形参数（红色背景，带边距）
        padding = 10
        rect_x1 = max(0, text_x - padding)
        rect_y1 = max(0, text_y - text_height - padding)
        rect_x2 = min(data.width, text_x + text_width + padding)
        rect_y2 = min(data.height, text_y + baseline + padding)
        
        # 绘制红色背景矩形 (BGRA格式: B=0, G=0, R=255, A=255)
        data._raw[rect_y1:rect_y2, rect_x1:rect_x2] = [0, 0, 255, 255]
        
        # 绘制白色文字 (BGRA格式: B=255, G=255, R=255, A=255)
        cv2.putText(data._raw, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
        
        return data

class FactorSensorDataRandomLoss(Factor):
    NAME = 'F_SensorDataRandomLoss'
    PRIORITY = True

    def __init__(self, context: 'CarlaContext', sensor: CarlaSensor):
        super().__init__(context)
        self._sensor = sensor
        self._last_data: Image | None = None

    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def on_sensor_data_recv(self, data: Image) -> Image:
        if random.random() < 0.9:
            return self._last_data
        else:
            self._last_data = data
            return data

if __name__ == "__main__":
    # 基础组件初始化
    config = Path('config.yaml')                            # 读取配置文件
    logger = Logging.load(config).get_logger('Main')        # 设置日志记录器

    with CarlaContext(config) as context:
        context.change_map('Town04')

        vehicle = PlayerVehicle(context, context.spawn_points[0])

        context.actors.spawn_all()
        context.actors.wait_stable(vehicle)

        context.io.create_ros2_hp(ros_topic_name='/harzed_scope/cam/game').bind_sensor_output(vehicle.cam_game)
        context.io.create_ros2_hp(ros_topic_name='/harzed_scope/lidar/main').bind_sensor_output(vehicle.lidar_main)

        vehicle.set_carla_autopilot(enable=True)

        f1 = FactorImageTag(context, vehicle.cam_game)
        f2 = FactorSensorDataRandomLoss(context, vehicle.cam_game)
        factors = [f1, f2]
        
        with Injector(context, *factors) as injector:       # 执行注入
            context.spin()

    logger.info('Goodbye!')
