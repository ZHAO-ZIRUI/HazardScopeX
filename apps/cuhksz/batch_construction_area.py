import carla
import numpy as np
from shared.simulator import CarlaContext
from shared.utils import Logging

from shared.prefabs import NuScenesVehicle
from shared.scenarios.factorlib import *
from shared.scenarios.injector import Injector
from shared.simulator import CarlaBlueprints
from shared.dataset import NuScenesDumper
from shared.scenarios import Factor
from shared.data import VehicleDirectControl

from pre_combine import get_weather_light_pre_combine


def get_weather_light_tag(f_weather_list: list) -> str:
    light_tag = ''
    weather_tag = ''
    for factor in f_weather_list:
        if isinstance(factor, FactorEnvLight):
            light_tag = f'Light{factor.level.value}'
        elif isinstance(factor, FactorWeatherRain):
            weather_tag = f'Rain{factor.level.value}'
        elif isinstance(factor, FactorWeatherFog):
            weather_tag = f'Fog{factor.level.value}'
    return f'{light_tag}{weather_tag}' if light_tag else 'UNK'


if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('BATCH COLLECTION - STATIC OBSTACLE')

    SPAWN_POINT_EGO = 0
    MAPS = ('Carla/Maps/Town10HD_Opt', 'Carla/Maps/Town03')
    DISTANCE_THRESHOLD_BEGIN_RECORD = 100.0
    DATASET_NAME_PREFIX = 'ConstructionArea_Town04_100M_NPC_'

    M_OBSTACLE_NAME_BP = {
        CarlaBlueprints.STATIC_PROP_SHOPPINGCART: 'ShoppingCart',
        CarlaBlueprints.STATIC_PROP_BOX01: 'Box',
        CarlaBlueprints.STATIC_PROP_TRASHCAN01: 'TrashCan',
    }

    with CarlaContext() as context:

        # USE TOWN 04 MAP
        context.change_map('Town04')

        v_ego = NuScenesVehicle(context, context.spawn_points[SPAWN_POINT_EGO], name='EGO')
        f_weather_light_combines = get_weather_light_pre_combine(context, v_ego)

        context.actors.spawn_all()
        context.actors.wait_stable()


        for exp_id, f_weather_list in enumerate(f_weather_light_combines):
            f_construction_area = FactorCaseConstructionArea(context, v_ego)
            # TOWN04 CONFIG
            f_construction_area = FactorCaseConstructionArea(context, v_ego, distance=200.0)

            # 忽略交通灯
            context.traffic.ignore_lights_percentage(v_ego.actor, 100.0)

            # 恢复天气状态
            context.world.set_weather(carla.WeatherParameters.ClearNoon)

            context.wait_seconds(2)

            with Injector(context, *f_weather_list, f_construction_area) as injector:
                weather_light_tag = get_weather_light_tag(f_weather_list)
                dataset_name = DATASET_NAME_PREFIX + weather_light_tag
                logger.warning(f'Experiment {exp_id} [{weather_light_tag}] - {dataset_name}, ({exp_id} / {len(f_weather_light_combines)})')

                while True:  # LOOP FOR FAILED RETRY
                    # 让自车在每次重试前退出自动驾驶模式, 并回到因子定义起点
                    f_construction_area.move_ego_vehicle_to_init_tf()
                    v_ego.actor.apply_control(carla.VehicleControl(throttle=0.0, steer=0.0, brake=1.0, hand_brake=False, reverse=False))
                    context.wait_seconds(1)

                    is_failed = False

                    # 重试内重新设置自车自动驾驶与路线
                    v_ego.set_carla_autopilot(enable=True)
                    context.traffic.update_vehicle_lights(v_ego.actor, True)
                    context.traffic.set_route(v_ego.actor, ['Straight', 'Right', 'Straight'])

                    # 等待距离差小于阈值开始记录
                    last_distance_diff = []
                    while True:
                        context.wait_ticks(1, no_log=True)
                        distance_diff = f_construction_area.get_ego_vehicle_distance_to_obstacle()
                        logger.debug(f'Distance diff: {distance_diff:.2f} m')
                        if distance_diff < DISTANCE_THRESHOLD_BEGIN_RECORD:
                            break
                        # 记录最后5个距离差
                        if len(last_distance_diff) >= 20:
                            last_distance_diff.pop(0)
                        last_distance_diff.append(distance_diff)

                        # 如果最后五个距离差的方差小于0.1，则认为试验失败
                        if len(last_distance_diff) >= 20 and np.var(last_distance_diff) < 0.1:
                            is_failed = True
                            break

                    if is_failed:
                        logger.warning(f'Experiment {exp_id} [{weather_light_tag}] - {dataset_name} failed')
                        continue

                    with NuScenesDumper(context, ego_vehicle=v_ego, name=dataset_name) as dumper:
                        dumper.bind_sensor_output(v_ego.cam_front, 'CAM_FRONT')
                        dumper.bind_sensor_output(v_ego.cam_front_left, 'CAM_FRONT_LEFT')
                        dumper.bind_sensor_output(v_ego.cam_front_right, 'CAM_FRONT_RIGHT')
                        dumper.bind_sensor_output(v_ego.cam_back, 'CAM_BACK')
                        dumper.bind_sensor_output(v_ego.cam_back_left, 'CAM_BACK_LEFT')
                        dumper.bind_sensor_output(v_ego.cam_back_right, 'CAM_BACK_RIGHT')
                        dumper.bind_sensor_output(v_ego.lidar, 'LIDAR_TOP')

                        context.wait_ticks(450)

                        v_ego.set_carla_autopilot(enable=False)
                        v_ego.actor.set_target_velocity(carla.Vector3D(x=0.0, y=0.0, z=0.0))
                        context.wait_ticks(10)
                    # NOT FAILED
                    break

    logger.info('GOODBYE!')