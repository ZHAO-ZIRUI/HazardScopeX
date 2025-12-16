# ==============================================================
# 简单的车辆与传感器程序样例
# 
# 在 CARLA 中创建一辆车辆, 并为其安装传感器, 然后开始 CARLA AUTOPILOT 自动驾驶
# 用于测试通信功能
#
#
# 逻辑：
# 1. 创建一辆车辆
# 2. 为车辆安装多个传感器（前置相机、游戏视角相机、激光雷达）
# 3. 绑定传感器输出到 ROS2 和共享内存
# 4. 启动 CARLA AUTOPILOT 自动驾驶
# ==============================================================
from shared.simulator import CarlaContext, CarlaBlueprints, CarlaTransform
from shared.utils import Logging
from shared.prefabs import PlayerVehicle

if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('DEMO FOR VEHICLE AND SENSORS')


    with CarlaContext() as context:

# region: 以手工方式创建车辆与传感器
        # 创建一辆车辆
        vehicle = context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_AUDI_A2,
            tf=context.spawn_points[0],
        )

        # 创建前置相机传感器
        cam_front = context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name='CAM_FRONT',
            tf=CarlaTransform(x=1.6, y=0.0, z=1.7),
            parent=vehicle,
        )

        # 创建游戏视角相机传感器
        cam_game = context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name='CAM_GAME',
            tf=CarlaTransform(x=-5.5, y=0.0, z=2.5, pitch=-15.0),
            parent=vehicle,
        )

        # 创建激光雷达传感器
        lidar_main = context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_LIDAR_RAY_CAST,
            name='LIDAR',
            tf=CarlaTransform(x=0.0, y=0.0, z=2.2),
            parent=vehicle,
        )

# endregion

# region: 以预制车辆方式创建车辆与传感器
        # 与上述手工方式等价, 但更简洁
        # vehicle = PlayerVehicle(context, context.spawn_points[0])
        # cam_front = vehicle.cam_front
        # cam_game = vehicle.cam_game
        # lidar_main = vehicle.lidar
# endregion

        # 等待车辆稳定
        context.actors.spawn_all()
        context.actors.wait_stable(vehicle)

        # 绑定传感器输出到共享内存
        context.io.create_shm(topic='cam_front').bind_sensor_output(cam_front)
        context.io.create_shm(topic='cam_game').bind_sensor_output(cam_game)
        context.io.create_shm(topic='lidar').bind_sensor_output(lidar_main)

        # 绑定传感器输出到 ROS2
        context.io.create_ros2(topic='/harzed_scope/cam/front').bind_sensor_output(cam_front)
        context.io.create_ros2(topic='/harzed_scope/cam/game').bind_sensor_output(cam_game)
        context.io.create_ros2(topic='/harzed_scope/lidar/main').bind_sensor_output(lidar_main)

        # 启动 CARLA AUTOPILOT 自动驾驶
        vehicle.set_carla_autopilot(enable=True)

        # 启动主线程阻塞循环
        context.spin()

    logger.info('GOODBYE!')
