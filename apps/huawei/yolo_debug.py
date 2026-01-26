import carla
from shared.simulator import CarlaContext, CarlaBlueprints
from shared.simulator import CarlaVehicle
from shared.data import VehicleDirectControl
from shared.utils import Logging

from apps.huawei.yolo_aeb_vehicle import YoloAEBVehicle

def calc_distance(v_ego: YoloAEBVehicle, v_act: CarlaVehicle) -> float:
    d_ego_center_end = v_ego.actor.bounding_box.extent.x
    d_act_center_end = v_act.actor.bounding_box.extent.x
    d_ego_act_center = v_ego.tf_now_center.location.distance(v_act.tf_now_center.location)
    return d_ego_act_center - (d_ego_center_end + d_act_center_end)

def calc_remaining_stop_distance(v_ego: YoloAEBVehicle) -> float:
    a = v_ego.last_accpet_acceleration
    v = v_ego.last_accept_speed
    if a == 0.0:
        return float('inf')
    return v * v / (2 * a)

if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('YOLO DEBUG')

    # THIS ROAD SPAWN POINTS -> TOWN10HD_Opt
    # 96-91-0-<CROSS>-93-53-56-107-58
    SPAWN_POINT_EGO = 91 
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
        v_ego.apply_speed(50)

        # 启动主线程阻塞循环
        while True:
            d_ego_act = calc_distance(v_ego, v_act)
            d_remaining_stop = calc_remaining_stop_distance(v_ego)
            if v_ego.is_safe_stop:
                logger.warning('EXPERIMENT END WITH SAFE STOP')
                logger.warning(f'SAFETY_STOP_DISTANCE: {d_ego_act:.2f}m')
                context.wait_ticks(5, no_log=True)
                break
            if v_ego.is_collision:
                logger.warning('EXPERIMENT END WITH COLLISION')
                logger.warning(f'REMAINING_STOP_DISTANCE: {d_remaining_stop:.2f}m')
                # TODO: 计算碰撞时的结果
                context.wait_ticks(5, no_log=True)
                break
            context.wait_ticks(1, no_log=True)

    logger.info('GOODBYE!')