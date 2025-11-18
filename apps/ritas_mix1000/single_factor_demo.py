# 简单的因子注入样例
from shared.simulator import *
from shared.utils import Config, Logging
from shared.prefabs import PlayerVehicle
from shared.scenarios import Injector

from factors import *


if __name__ == "__main__":
    # 基础组件初始化
    config = Config.from_yaml('config.yaml')                # 读取配置文件
    logger = Logging.from_config(config).get_logger('Main') # 设置日志记录器

    with CarlaContext.from_config(config) as context:
        context.change_map('Town04')

        vehicle = PlayerVehicle(context, context.spawn_points[0])

        context.actors.spawn_all()
        context.actors.wait_stable(vehicle)

        context.io.create_ros2_hp(ros_topic_name='/harzed_scope/cam/game').bind_sensor_output(vehicle.cam_game)
        context.io.create_ros2_hp(ros_topic_name='/harzed_scope/lidar/main').bind_sensor_output(vehicle.lidar_main)

        # f1 = FactorEnvNoon(context)
        f1 = FactorCaseRampWrongWay(context, vehicle)
        factors = [f1]
        
        with Injector(context, *factors) as injector:       # 执行注入

            # vehicle.set_carla_autopilot(enable=True)
            context.spin()

    logger.info('Goodbye!')
