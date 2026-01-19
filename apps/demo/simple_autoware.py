# ==============================================================
# 简单的 Autoware 联合仿真程序样例
# ==============================================================
from shared.simulator import CarlaContext
from shared.utils import Logging
from shared.prefabs import AutowareVehicle
from geometry_msgs.msg import PoseWithCovarianceStamped
from shared.data import TimestampSource

if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('DEMO FOR SIMPLE AUTOWARE')


    with CarlaContext() as context:

        vehicle = AutowareVehicle(context, context.spawn_points[0])

        # 等待车辆稳定
        context.actors.spawn_all()
        context.actors.wait_stable(vehicle)

        # 绑定传感器输出到 ROS2
        context.io.create_ros2_pub(topic='/hs/cam/front').bind_sensor(vehicle.cam_front)
        context.io.create_ros2_pub(topic='/hs/cam/game').bind_sensor(vehicle.cam_game)
        context.io.create_ros2_pub(topic='/hs/lidar/main', frame_id='velodyne_top').bind_sensor(vehicle.lidar)
        context.io.create_ros2_pub(topic='/hs/gnss', msg=PoseWithCovarianceStamped).bind_sensor(vehicle.gnss)
        context.io.create_ros2_pub(topic='/hs/imu').bind_sensor(vehicle.imu)

        # 绑定时钟输出到 ROS2
        context.io.create_ros2_pub(topic='/hs/clock',timestamp_source=TimestampSource.SIM).bind_clock()

        # 绑定 TF 输出到 ROS2
        context.io.create_ros2_tf_static('base_link', 'cam_front').bind_sensor(vehicle.cam_front)
        context.io.create_ros2_tf_static('base_link', 'cam_game').bind_sensor(vehicle.cam_game)
        context.io.create_ros2_tf_static('base_link', 'velodyne_top').bind_sensor(vehicle.lidar)
        context.io.create_ros2_tf_static('base_link', 'gnss').bind_sensor(vehicle.gnss)
        context.io.create_ros2_tf_static('base_link', 'imu').bind_sensor(vehicle.imu)

        # 启动 CARLA AUTOPILOT 自动驾驶
        vehicle.set_carla_autopilot(enable=True)

        # 启动主线程阻塞循环
        context.spin()

    logger.info('GOODBYE!')
