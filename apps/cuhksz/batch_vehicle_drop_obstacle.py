import carla
import numpy as np
from shared.scenarios.factorlib import f_case_vehicle_drop_obstacle
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
    logger.info('BATCH COLLECTION - VEHICLE DROP OBSTACLE')

    SPAWN_POINT_EGO = 0
    DISTANCE_THRESHOLD_BEGIN_RECORD = 100.0
    DATASET_NAME_PREFIX = 'VehicleDropObstacle_Town03_NPC_TrashCan_'

    M_OBSTACLE_NAME_BP = {
        CarlaBlueprints.STATIC_PROP_SHOPPINGCART: 'ShoppingCart',
        CarlaBlueprints.STATIC_PROP_BOX01: 'Box',
        CarlaBlueprints.STATIC_PROP_TRASHCAN01: 'TrashCan',
    }

    with CarlaContext() as context:

        # USE TOWN 04 MAP
        context.change_map('Town03')

        v_ego = NuScenesVehicle(context, context.spawn_points[SPAWN_POINT_EGO], name='EGO')
        f_weather_light_combines = get_weather_light_pre_combine(context, v_ego)

        context.actors.spawn_all()
        context.actors.wait_stable()


        for exp_id, f_weather_list in enumerate(f_weather_light_combines):
            f_drop_obstacle = FactorCaseVehicleDropObstacle(context, v_ego, obstical_bp=CarlaBlueprints.STATIC_PROP_TRASHCAN01)

            # 忽略交通灯
            context.traffic.ignore_lights_percentage(v_ego.actor, 100.0)

            # 恢复天气状态
            context.world.set_weather(carla.WeatherParameters.ClearNoon)

            context.wait_seconds(2)

            with Injector(context, *f_weather_list, f_drop_obstacle) as injector:
                weather_light_tag = get_weather_light_tag(f_weather_list)
                dataset_name = DATASET_NAME_PREFIX + weather_light_tag
                logger.warning(f'Experiment {exp_id} [{weather_light_tag}] - {dataset_name}, ({exp_id} / {len(f_weather_light_combines)})')

                while True:  # LOOP FOR FAILED RETRY
                    # 让自车在每次重试前退出自动驾驶模式, 并回到因子定义起点
                    f_drop_obstacle.move_ego_vehicle_to_init_tf()
                    v_ego.actor.apply_control(carla.VehicleControl(throttle=0.0, steer=0.0, brake=1.0, hand_brake=False, reverse=False))
                    context.wait_seconds(1)

                    is_failed = False

                    # 重试内重新设置自车自动驾驶与路线
                    v_ego.set_carla_autopilot(enable=True)
                    context.traffic.update_vehicle_lights(v_ego.actor, True)
                    context.traffic.set_route(v_ego.actor, ['Straight', 'Right', 'Straight'])

                    # 等待2s预热
                    context.wait_seconds(4)

                    with NuScenesDumper(context, ego_vehicle=v_ego, name=dataset_name) as dumper:
                        dumper.bind_sensor_output(v_ego.cam_front, 'CAM_FRONT')
                        dumper.bind_sensor_output(v_ego.cam_front_left, 'CAM_FRONT_LEFT')
                        dumper.bind_sensor_output(v_ego.cam_front_right, 'CAM_FRONT_RIGHT')
                        dumper.bind_sensor_output(v_ego.cam_back, 'CAM_BACK')
                        dumper.bind_sensor_output(v_ego.cam_back_left, 'CAM_BACK_LEFT')
                        dumper.bind_sensor_output(v_ego.cam_back_right, 'CAM_BACK_RIGHT')
                        dumper.bind_sensor_output(v_ego.lidar, 'LIDAR_TOP') 

                        context.wait_ticks(190)

                        v_ego.set_carla_autopilot(enable=False)
                        v_ego.actor.set_target_velocity(carla.Vector3D(x=0.0, y=0.0, z=0.0))
                        context.wait_ticks(10)
                    # NOT FAILED
                    break

    logger.info('GOODBYE!')