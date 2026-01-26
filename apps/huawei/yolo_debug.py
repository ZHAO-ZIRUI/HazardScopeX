import carla
from shared.simulator import CarlaContext, CarlaBlueprints
from shared.data import VehicleDirectControl
from shared.utils import Logging

from apps.huawei.yolo_aeb_vehicle import YoloAEBVehicle

if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('YOLO DEBUG')

    SPAWN_POINT_EGO = 93
    SPAWN_POINT_ACT = 53


    with CarlaContext() as context:

        v_ego = YoloAEBVehicle(context, context.spawn_points[SPAWN_POINT_EGO], name='EGO')
        v_act = context.actors.create_vehicle(
            CarlaBlueprints.VEHICLE_TESLA_MODEL3,
            context.spawn_points[SPAWN_POINT_ACT],
            name='ACT',
        )

        context.actors.spawn_all()
        context.actors.wait_stable()

        # 设置 ACT 的行为
        v_act.apply_direct_control(VehicleDirectControl(brake=1.0, hand_brake=True))

        # 给 EGO 实验速度
        v_ego.apply_speed(20)

        # 启动主线程阻塞循环
        while True:
            if v_ego.is_safe_stop:
                logger.warning('EXPERIMENT END WITH SAFE STOP')
                context.wait_ticks(5, no_log=True)
                break
            if v_ego.is_collision:
                logger.warning('EXPERIMENT END WITH COLLISION')
                context.wait_ticks(5, no_log=True)
                break
            context.wait_ticks(1, no_log=True)

    logger.info('GOODBYE!')