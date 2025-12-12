# 简单的数据集导出程序
# 在 CARLA 中创建一辆车辆, 并为其安装传感器, 然后开始 CARLA AUTOPILOT 自动驾驶
# 将传感器数据导出为数据集

import threading
from pathlib import Path
from shared.simulator import *
from shared.utils import Logging
from shared.dataset import DatasetDumper

if __name__ == "__main__":
    # 基础组件初始化
    config = Path('config.yaml')                            # 读取配置文件
    logger = Logging.load(config).get_logger('Main')        # 设置日志记录器

    with CarlaContext(config) as context:
        vehicle = context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_AUDI_A2,
            tf=context.spawn_points[0],
        )

        cam_front = context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name='CAM_FRONT',
            tf=CarlaTransform(x=1.6, y=0.0, z=1.7),
            parent=vehicle,
        )

        cam_game = context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name='CAM_GAME',
            tf=CarlaTransform(x=-5.5, y=0.0, z=2.5, pitch=-15.0),
            parent=vehicle,
        )

        lidar_main = context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_LIDAR_RAY_CAST,
            name='LIDAR_MAIN',
            tf=CarlaTransform(x=0.0, y=0.0, z=2.2),
            parent=vehicle,
        )

        context.actors.spawn_all()
        context.actors.wait_stable(vehicle)

        vehicle.set_carla_autopilot(enable=True)
        

        with DatasetDumper(context, './export') as dumper:
            dumper.bind_sensor_output(cam_front, 'cam_front')
            dumper.bind_sensor_output(cam_game, 'cam_game')
            dumper.bind_sensor_output(lidar_main, 'lidar_main')
            context.wait_seconds(5)

    logger.info('Goodbye!')
