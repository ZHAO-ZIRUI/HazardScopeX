# ==============================================================
# 简单的 nuScenes 数据集导出程序样例
# 
# 数据会保存在 export/ 目录下，以时间戳命名. 传感器数据会被导出为 nuScenes 格式
#
#
# 逻辑：
# 1. 创建一辆车辆并为其安装传感器
# 2. 创建另一辆车辆
# 3. 对两辆车辆启动 CARLA AUTOPILOT
# 3. 导出传感器数据为 nuScenes 数据集
# ==============================================================
from shared.simulator import *
from shared.utils import Logging
from shared.dataset import NuScenesDumper
from shared.prefabs import NuScenesVehicle

if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('DEMO FOR NUSCENES DUMPER')

    with CarlaContext() as context:

        vehicle = NuScenesVehicle(context, context.spawn_points[93])

        another_vehicle = context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_AUDI_A2,
            tf=context.spawn_points[53],
        )

        # 等待车辆稳定
        context.actors.spawn_all()
        context.actors.wait_stable()

        another_vehicle.set_carla_autopilot(enable=True)
        vehicle.set_carla_autopilot(enable=True)

        with NuScenesDumper(context, ego_vehicle=vehicle) as dumper:
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

