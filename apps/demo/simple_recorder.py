# 简单的录制程序
# 在 CARLA 中创建一辆车辆, 并为其安装传感器, 然后录制仿真数据
from shared.simulator import *
from shared.utils import Config, Logging
from shared.simulator import CarlaTransform

if __name__ == "__main__":
    # 基础组件初始化
    config = Config.from_yaml('config.yaml')                # 读取配置文件
    logger = Logging.from_config(config).get_logger('Main') # 设置日志记录器

    logger.info('Starting simple server')
    with CarlaContext.from_config(config) as context:
        
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

        # 以上下文管理器方式录制仿真数据
        # 特别注意, 传感器要在开始录制前被 SPAWN
        with context.recorder.record('demo'):
            vehicle.set_carla_autopilot(enable=True)
            context.wait_seconds(30)

        # 上方代码等价于
        # ------------------------------------------------------------
        # context.recorder.start_record('demo')
        # vehicle.set_carla_autopilot(enable=True)
        # context.wait_seconds(30)
        # context.recorder.stop_record()
        # ------------------------------------------------------------

    logger.info('Goodbye!')
