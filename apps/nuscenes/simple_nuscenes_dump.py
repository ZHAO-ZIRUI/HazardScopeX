# 简单的 nuScenes 数据集导出样例
from shared.simulator import *
from shared.utils import Logging
from shared.dataset import NuScenesDumper
from shared.prefabs import NuScenesVehicle

if __name__ == "__main__":
    # 基础组件初始化
    # config = Config.from_yaml('config.yaml')                # 读取配置文件
    # logger = Logging.from_config(config).get_logger('Main') # 设置日志记录器
    logger = Logging.load('config.yaml').get_logger('Main')

    with CarlaContext() as context:

        vehicle = NuScenesVehicle(context, context.spawn_points[93])

        v1 = context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_AUDI_A2,
            tf=context.spawn_points[53],
        )

        # 等待车辆稳定
        context.actors.spawn_all()
        context.actors.wait_stable(vehicle)

        context.actors.spawn_all()
        context.actors.wait_stable()

        v1.set_carla_autopilot(enable=True)
        vehicle.set_carla_autopilot(enable=True)

        with NuScenesDumper(context,carla_vehicle=vehicle) as dumper:
            # 绑定所有相机传感器
            dumper.bind_sensor_output(vehicle.cam_front, vehicle.cam_front.name)
            dumper.bind_sensor_output(vehicle.cam_front_left, vehicle.cam_front_left.name)
            dumper.bind_sensor_output(vehicle.cam_front_right, vehicle.cam_front_right.name)
            dumper.bind_sensor_output(vehicle.cam_back, vehicle.cam_back.name)
            dumper.bind_sensor_output(vehicle.cam_back_left, vehicle.cam_back_left.name)
            dumper.bind_sensor_output(vehicle.cam_back_right, vehicle.cam_back_right.name)
            
            # 绑定语义激光雷达
            dumper.bind_sensor_output(vehicle.lidar, vehicle.lidar.name)

            context.wait_seconds(5)    # 共录制 30 秒数据

    logger.info('Goodbye!')

