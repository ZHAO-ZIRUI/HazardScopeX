# ==============================================================
# 简单的因子注入程序样例
# 
# 以继承方式实现了两个因子, 并执行注入过程
#
# 因子 FactorSensorCameraTag: 传感器注入样例, 在相机画面上中心绘制一个 DEMO FACTOR SENSOR TAG 标签
# 因子 FactorDemoTrigger: 事件触发样例, 等待 3 秒后触发, 然后等待 3 秒后完成
# ==============================================================
import cv2
from typing_extensions import Self
from shared.data.image import Image
from shared.scenarios.evaluator import ConstantRiskEvaluator, SimpleRiskEvaluator
from shared.simulator import *
from shared.utils import Logging
from shared.prefabs import PlayerVehicle
from shared.scenarios import Injector, Factor


class FactorSensorCameraTag(Factor):
    NAME = 'F_SensorCameraTag'

    def __init__(self, context: CarlaContext, camera: CarlaSensor):
        super().__init__(context)
        assert isinstance(camera, CarlaSensor) and camera.is_camera
        self._camera = camera        

    def __post_init__(self) -> Self:
        self.hook_bringup.append(lambda: self._camera.hook_sensor_data_recv.append(self.on_sensor_data_recv))
        self.hook_teardown.append(lambda: self._camera.hook_sensor_data_recv.remove(self.on_sensor_data_recv))
        return self

    def on_sensor_data_recv(self, data: Image) -> Image:
        # 设置文字参数
        text = 'DEMO FACTOR SENSOR TAG'
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
        
        self.stage = self.FactorStage.COMPLETED

        return data

class FactorDemoTrigger(Factor):
    NAME = 'F_DemoTrigger'

    def __init__(self, context: CarlaContext):
        super().__init__(context)
        self._wait_trigger_seconds = 3.0
        self._triggered_seconds = 3.0

        self._count_before_trigger = 0
        self._count_after_trigger = 0

    def __post_init__(self) -> Self:
        self.hook_update.append(self.trigger)
        self.hook_update.append(self.post_trigger)
        return self

    def trigger(self) -> None:
        # 如果因子不在等待触发阶段, 则直接返回
        if self.stage != self.FactorStage.WAIT_FOR_TRIGGER:
            return
        # 如果等待触发帧数达到阈值, 则触发因子
        if self._count_before_trigger >= self._wait_trigger_seconds * self._context.fps:
            self.stage = self.FactorStage.TRIGGERED
            self.logger.warning(f'Factor {self.NAME} triggered')  # 以警告级别输出
        self._count_before_trigger += 1
        return

    def post_trigger(self) -> None:
        # 如果因子不在触发阶段, 则直接返回
        if self.stage != self.FactorStage.TRIGGERED:
            return
        # 如果触发帧数达到阈值, 则完成因子
        if self._count_after_trigger >= self._triggered_seconds * self._context.fps:
            self.stage = self.FactorStage.COMPLETED
            self.logger.warning(f'Factor {self.NAME} completed')  # 以警告级别输出
        self._count_after_trigger += 1
        return


if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('DEMO FOR SIMPLE INJECT')

    with CarlaContext() as context:    

        context.change_map('Town10HD')
        vehicle = PlayerVehicle(context, context.spawn_points[0])

        context.actors.spawn_all()
        context.actors.wait_stable(vehicle)

        evaluator = SimpleRiskEvaluator(context)
        evaluator.bind_evaluate_actor('hero', vehicle)

        # 绑定传感器输出到内存
        context.io.create_shm(topic='cam_game').bind_sensor_output(vehicle.cam_game)
        
        # context.io.create_ros2(topic='/harzed_scope/cam/game').bind_sensor_output(vehicle.cam_game)
        # context.io.create_ros2(topic='/harzed_scope/lidar/main').bind_sensor_output(vehicle.lidar)

        vehicle.set_carla_autopilot(enable=True)

        f1 = FactorSensorCameraTag(context, vehicle.cam_game)
        f2 = FactorDemoTrigger(context)
        factors = [f1, f2]
        
        with Injector(context, *factors) as injector:       # 执行注入
            injector.spin_until_evaluator_threshold(evaluator=evaluator, threshold=0.99)

    logger.info('Goodbye!')
