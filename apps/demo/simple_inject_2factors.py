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
from shared.prefabs.yolo_aeb_vehicle import YoloAEBVehicle
from shared.data.image import Image
from shared.data.vehicle_direct_control import VehicleDirectControl
from shared.simulator import *
from shared.utils import Logging
from shared.scenarios import Injector, Factor
from shared.scenarios.factorlib import *
from experiment_logger import ExperimentLogger

WEATHER_FACTOR_NAME_DICT = {
    'Rain': FactorWeatherRain,
    'Fog': FactorWeatherFog,
    'Dust': FactorWeatherDustStorm,
}

SENSOR_FACTOR_NAME_DICT = {
    'OverExposure': FactorCameraOverexposure,
    'UnderExposure': FactorCameraUnderexposure,
    'ChromaticAberration': FactorCameraChromaticAberration,
    'ColorCast': FactorCameraColorCast,
    # 'Time': FactorTime,
    # 'CarLight': FactorCarLight,
}

SPEED_RANGES = [30, 40, 50, 60, 70]
# SPEED_RANGES = [50]

if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('YOLO DEBUG WITH INJECTOR')

    csv_logger = ExperimentLogger("yolo_aeb_experiment_data.csv")

    # THIS ROAD SPAWN POINTS -> TOWN10HD_Opt
    # 96-91-0-<CROSS>-93-53-56-107-58
    SPAWN_POINT_EGO = 91
    SPAWN_POINT_ACT = 53

    with CarlaContext() as context:
        # context.change_map('Town04')    
        # context.client.load_world('Town10HD_Opt', reset_settings=False)

        # context.io.create_ros2(topic='/harzed_scope/cam/game').bind_sensor_output(vehicle.cam_game)
        # context.io.create_ros2(topic='/harzed_scope/lidar/main').bind_sensor_output(vehicle.lidar)

        # v_act.apply_direct_control(VehicleDirectControl(brake=1.0, hand_brake=True))
        shm = context.io.create_shm('cam_front')

        for factor1_name, factor1_clazz in WEATHER_FACTOR_NAME_DICT.items():
            for intensity_1 in range(3, 0, -1): # 因子强度
                for factor2_name, factor2_clazz in SENSOR_FACTOR_NAME_DICT.items():
                    for intensity_2 in range(1, 2):
                        for speed in SPEED_RANGES:

                            # 清除上一轮的残留actor
                            context.actors.destroy_all()
                            context.wait_seconds(1)

                            v_ego = YoloAEBVehicle(context, context.spawn_points[SPAWN_POINT_EGO], name='EGO')
                            
                            context.actors.spawn_all()

                            # 实验数据记录
                            currect_active_factors = {
                                factor1_name: intensity_1,
                                factor2_name: intensity_2
                            }

                            current_metrics = {
                                'detect_distance': 0,
                                'final_distance': 5.2,
                                'is_collision': False
                            }

                            logger.info(f'START EXPERIMENT ROUND {intensity_1}')

                            v_ego.clear()
                            # f0 = FactorCaseHighwayMerge(context, v_ego, ego_init_speed=speed, act_init_speed=speed/2, ego_distance_to_merge=70)
                            f0 = FactorCaseFrontVehicleStatic(context, v_ego)
                            f1 = factor1_clazz(context, v_ego, level=intensity_1)
                            f2 = factor2_clazz(context, v_ego, level=intensity_2)
                            factors = [f0, f1, f2]
                            
                            with Injector(context, *factors) as injector:       # 执行注入
                                shm.bind_sensor(v_ego.cam_front)
                                context.actors.wait_stable(v_ego)
                                v_ego.apply_speed(speed)
                                v_ego.actor.set_enable_gravity(True)
                                context.wait_ticks(10, no_log=True)
                                # 绑定传感器到共享内存
                                injector.spin_until_collision(v_ego, f0.act, current_metrics)  # 持续运行直到碰撞发生
                            
                            # 记录数据到 csv
                            csv_logger.log_result(
                                scenario="Front vehicle keep stop",
                                speed=speed,
                                repeat=0,
                                active_factor_dict=currect_active_factors,
                                metrics=current_metrics
                            )
    logger.info('Goodbye!')