# 最简车辆与传感器程序, 用于测试通信功能
# 在 CARLA 中创建一辆车辆, 并为其安装传感器, 然后开始 CARLA AUTOPILOT 自动驾驶
from shared.simulator import *
from shared.utils import Config, Logging
from shared.simulator import CarlaTransform

if __name__ == "__main__":
    # 基础组件初始化
    config = Config.from_yaml('config.yaml')                # 读取配置文件
    logger = Logging.from_config(config).get_logger('Main') # 设置日志记录器

    logger.info('Starting simple server')
    with CarlaContext.from_config(config) as context:

        vehicle = context.actors.create_actor(
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

        context.io.create_shm(topic='sensor_data').bind_sensor_output(cam_front)

        # NOTE: create_ros2 在传感器回调中中发布消息, 会产生一定的性能问题
        # context.io.create_ros2(topic='/harzed_scope/cam/front').bind_sensor_output(cam_front)
        # context.io.create_ros2(topic='/harzed_scope/cam/game').bind_sensor_output(cam_game)
        # context.io.create_ros2(topic='/harzed_scope/lidar/main').bind_sensor_output(lidar_main)

        # NOTE: create_ros2_hp 先使用 SHM, 再在单独的子进程中处理 ROS2 的消息发布, 可以避免因为 Python GIL 锁导致的问题
        context.io.create_ros2_hp(ros_topic_name='/harzed_scope/cam/front').bind_sensor_output(cam_front)
        context.io.create_ros2_hp(ros_topic_name='/harzed_scope/cam/game').bind_sensor_output(cam_game)
        context.io.create_ros2_hp(ros_topic_name='/harzed_scope/lidar/main').bind_sensor_output(lidar_main)
        context.spin()
    logger.info('Goodbye!')
