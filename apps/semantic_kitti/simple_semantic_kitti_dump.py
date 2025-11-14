# 简单的 Semantic KITTI 数据集导出样例
from shared.simulator import *
from shared.utils import Config, Logging
from shared.dataset import SemanticKittiDumper
from shared.prefabs import KittiVehicle

if __name__ == "__main__":
    # 基础组件初始化
    config = Config.from_yaml('config.yaml')                # 读取配置文件
    logger = Logging.from_config(config).get_logger('Main') # 设置日志记录器

    with CarlaContext.from_config(config) as context:
        vehicle = KittiVehicle(context, context.spawn_points[0])

        context.actors.spawn_all()
        context.actors.wait_stable()

        vehicle.set_carla_autopilot(enable=True)

        with SemanticKittiDumper(context, './export') as dumper:
            dumper.bind_main_lidar(vehicle.main_lidar)
            dumper.bind_main_camera(vehicle.main_camera)

            # 其他相机传感器
            dumper.bind_sensor_output(vehicle.cam_left_rgb, 'CAM_LEFT_RGB')
            dumper.bind_sensor_output(vehicle.cam_right_rgb, 'CAM_RIGHT_RGB')
            dumper.bind_sensor_output(vehicle.cam_back_rgb, 'CAM_BACK_RGB')
            dumper.bind_sensor_output(vehicle.cam_left_depth, 'CAM_LEFT_DEPTH')
            dumper.bind_sensor_output(vehicle.cam_right_depth, 'CAM_RIGHT_DEPTH')
            dumper.bind_sensor_output(vehicle.cam_back_depth, 'CAM_BACK_DEPTH')
            dumper.bind_sensor_output(vehicle.cam_front_depth, 'CAM_FRONT_DEPTH')

            context.wait_seconds(30)    # 共录制 30 秒数据

    logger.info('Goodbye!')
