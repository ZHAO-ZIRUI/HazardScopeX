# ==============================================================
# 简单的录制程序样例
# 
# 数据会保存在 recorder/ 目录下，以时间戳命名. 后缀为 .carla 的文件为录制数据, 后缀为 .yaml 的文件为元数据, 记录了传感器的属性与位置
#
#
# 逻辑：
# 1. 创建一个携带传感器的预制车辆
# 2. 对车辆启动 CARLA AUTOPILOT
# 3. 录制 30 秒数据
# ==============================================================
from shared.simulator import CarlaContext
from shared.utils import Logging
from shared.prefabs import PlayerVehicle

if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('DEMO FOR RECORDER')


    with CarlaContext() as context:
        
        # 创建一个携带传感器的预制车辆
        vehicle = PlayerVehicle(context, context.spawn_points[0])

        # 等待车辆稳定
        context.actors.spawn_all()
        context.actors.wait_stable(vehicle)

        # 录制 30 秒数据
        with context.recorder.record():
            vehicle.set_carla_autopilot(enable=True)
            context.wait_seconds(30)

    logger.info('GOODBYE!')
