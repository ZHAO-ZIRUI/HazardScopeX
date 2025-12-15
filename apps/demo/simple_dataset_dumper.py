# ==============================================================
# 简单的数据集导出程序样例
# 
# 数据会保存在 export/ 目录下，以时间戳命名. 传感器数据会被导出为数据集格式
#
#
# 逻辑：
# 1. 创建一辆车辆并为其安装传感器
# 2. 对车辆启动 CARLA AUTOPILOT
# 3. 导出传感器数据为数据集
# ==============================================================
from shared.simulator import CarlaContext
from shared.utils import Logging
from shared.dataset import DatasetDumper
from shared.prefabs import PlayerVehicle

if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('DEMO FOR DATASET DUMPER')

    with CarlaContext() as context:
        
        # 创建一辆车辆
        vehicle = PlayerVehicle(context, context.spawn_points[0])

        # 等待车辆稳定
        context.actors.spawn_all()
        context.actors.wait_stable(vehicle)

        # 导出传感器数据为数据集
        vehicle.set_carla_autopilot(enable=True)
        with DatasetDumper(context) as dumper:
            dumper.bind_sensor_output(vehicle.cam_front, 'cam_front')
            dumper.bind_sensor_output(vehicle.cam_game, 'cam_game')
            dumper.bind_sensor_output(vehicle.lidar, 'lidar_main')
            context.wait_seconds(10)

        context.spin()

    logger.info('GOODBYE!')
