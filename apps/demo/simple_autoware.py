# ==============================================================
# 简单的 Autoware 联合仿真程序样例
# ==============================================================
from shared.simulator import CarlaContext
from shared.utils import Logging
from shared.prefabs import AutowareVehicle
from shared.define import TimestampSource
from shared.data import VehicleDirectControl
from shared.simulator import CarlaTransform

# ROS2 & Autoware Import
from rosgraph_msgs.msg import Clock as ROS2Clock
from autoware_vehicle_msgs.msg import VelocityReport
from sensor_msgs.msg import Image as ROS2Image
from sensor_msgs.msg import PointCloud2 as ROS2PointCloud2
from sensor_msgs.msg import Imu as ROS2Imu
from geometry_msgs.msg import PoseWithCovarianceStamped as ROS2PoseWithCovarianceStamped
from tier4_vehicle_msgs.msg import ActuationCommandStamped as ROS2ActuationCommandStamped



if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('DEMO FOR SIMPLE AUTOWARE')


    with CarlaContext() as context:

        vehicle = AutowareVehicle(context, context.spawn_points[0])

        # 等待车辆稳定
        context.actors.spawn_all()
        context.actors.wait_stable(vehicle)

        # 绑定传感器输出到 ROS2
        context.io.create_ros2_pub(topic='/hs/cam/front', msg=ROS2Image).bind_sensor(vehicle.cam_front)
        context.io.create_ros2_pub(topic='/hs/cam/game', msg=ROS2Image).bind_sensor(vehicle.cam_game)
        context.io.create_ros2_pub(topic='/hs/lidar/main', msg=ROS2PointCloud2, frame_id='velodyne_top').bind_sensor(vehicle.lidar)
        context.io.create_ros2_pub(topic='/hs/gnss', msg=ROS2PoseWithCovarianceStamped).bind_sensor(vehicle.gnss)
        context.io.create_ros2_pub(topic='/hs/imu', msg=ROS2Imu).bind_sensor(vehicle.imu)

        # 绑定时钟输出到 ROS2
        context.io.create_ros2_pub(topic='/hs/clock', msg=ROS2Clock, timestamp_source=TimestampSource.SIM).bind_clock()

        # 绑定车辆状态回报
        context.io.create_ros2_pub(
            topic='/hs/velocity_report', 
            msg=VelocityReport, 
            timestamp_source=TimestampSource.SIM
        ).bind_other(lambda: vehicle.get_velocity_report_msg())

        # 绑定 TF 输出到 ROS2
        context.io.create_ros2_tf('base_link', 'cam_front').bind_relation(vehicle.cam_front.tf_init)
        context.io.create_ros2_tf('base_link', 'cam_game').bind_relation(vehicle.cam_game.tf_init)
        context.io.create_ros2_tf('base_link', 'velodyne_top').bind_relation(vehicle.lidar.tf_init)
        context.io.create_ros2_tf('base_link', 'gnss').bind_relation(vehicle.gnss.tf_init)
        context.io.create_ros2_tf('base_link', 'imu').bind_relation(vehicle.imu.tf_init)

        # 定义回调
        def initpose_callback(msg: ROS2PoseWithCovarianceStamped):
            quat = msg.pose.pose.orientation
            roll, pitch, yaw = CarlaTransform.quat_to_euler(quat)
            vehicle.set_transform(
                CarlaTransform(
                    x=msg.pose.pose.position.x,
                    y=msg.pose.pose.position.y,
                    z=msg.pose.pose.position.z,
                    yaw=yaw,
                    pitch=pitch,
                    roll=roll,
                ), no_log=True)

        # 绑定输入
        context.io.create_ros2_sub(topic='/hs/cmd', msg=ROS2ActuationCommandStamped) \
            .bind_callback(lambda msg: vehicle.apply_direct_control(VehicleDirectControl.from_ros2(msg)))

        context.io.create_ros2_sub(topic='/hs/init', msg=ROS2PoseWithCovarianceStamped).bind_callback(initpose_callback)

        # 启动 CARLA AUTOPILOT 自动驾驶
        vehicle.control_mode = vehicle.ControlMode.EXTERNAL_AUTOPILOT

        # 启动主线程阻塞循环
        context.spin()

    logger.info('GOODBYE!')
