import carla
from shared.simulator import CarlaContext
from shared.utils import Logging

from shared.prefabs import NuScenesVehicle
from shared.scenarios.factorlib import *
from shared.scenarios.injector import Injector
from shared.simulator import CarlaBlueprints
from shared.dataset import NuScenesDumper
from shared.scenarios import Factor

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
    # 75M CONFIG
    # DISTANCE_THRESHOLD_BEGIN_RECORD = 75.0
    # DATASET_NAME_PREFIX = 'StaticObstacle_Town10_75M_'

    # 100M CONFIG
    DISTANCE_THRESHOLD_BEGIN_RECORD = 100.0
    DATASET_NAME_PREFIX = 'StaticObstacle_Town10_100M_'

    M_OBSTACLE_NAME_BP = {
        CarlaBlueprints.STATIC_PROP_SHOPPINGCART: 'ShoppingCart',
        CarlaBlueprints.STATIC_PROP_BOX01: 'Box',
        CarlaBlueprints.STATIC_PROP_TRASHCAN01: 'TrashCan',
    }

    with CarlaContext() as context:
        v_ego = NuScenesVehicle(context, context.spawn_points[SPAWN_POINT_EGO], name='EGO')
        f_weather_light_combines = get_weather_light_pre_combine(context, v_ego)

        # 静态障碍物因子
        # obstacle_bp = CarlaBlueprints.STATIC_PROP_TRASHCAN01
        # obstacle_bp = CarlaBlueprints.STATIC_PROP_SHOPPINGCART
        obstacle_bp = CarlaBlueprints.STATIC_PROP_BOX01
        obstacle_name = M_OBSTACLE_NAME_BP[obstacle_bp]

        context.actors.spawn_all()
        context.actors.wait_stable()

        for exp_id, f_weather_list in enumerate(f_weather_light_combines):
            f_static_obstacle = FactorCaseStaticObstacle(context, v_ego, obstical_bp=obstacle_bp)
            # MANY BOXES
            f_static_obstacle = FactorCaseStaticObstacle(context, v_ego, obstical_bp=obstacle_bp, obstacle_random_xy=2.0, obstacle_count=5)
            DATASET_NAME_PREFIX = 'StaticObstacle_Town10_100M_Many_'
            # 100M OVERRIDE
            f_static_obstacle.M_WORLD_LOCATION = {
                'Carla/Maps/Town10HD_Opt': {
                    Factor.K_VEHICLE_EGO: 94,
                    Factor.K_OBSTACLE: 119,
                    Factor.K_VEHICLE_NPC: [93, 53, 56, 107, 59, 58, 91],
                },
            }
            context.traffic.ignore_lights_percentage(v_ego.actor, 100.0)

            # 恢复天气状态
            context.world.set_weather(carla.WeatherParameters.ClearNoon)
            context.wait_seconds(2)

            with Injector(context, *f_weather_list, f_static_obstacle) as injector:
                weather_light_tag = get_weather_light_tag(f_weather_list)
                dataset_name = DATASET_NAME_PREFIX + obstacle_name + '_' + weather_light_tag
                logger.warning(f'Experiment {exp_id} [{weather_light_tag}] - {dataset_name}, ({exp_id} / {len(f_weather_light_combines)})')
                
                v_ego.set_carla_autopilot(enable=True)
                context.traffic.update_vehicle_lights(v_ego.actor, True)
                context.traffic.set_route(v_ego.actor, ['Straight', 'Straight', 'Straight'])

                # 等待距离差小于阈值开始记录
                while True:
                    context.wait_ticks(1, no_log=True)
                    distance_diff = f_static_obstacle.get_ego_vehicle_distance_to_obstacle()
                    logger.debug(f'Distance diff: {distance_diff:.2f} m')
                    if distance_diff < DISTANCE_THRESHOLD_BEGIN_RECORD:
                        break

                with NuScenesDumper(context, ego_vehicle=v_ego, name=dataset_name) as dumper:
                    dumper.bind_sensor_output(v_ego.cam_front, 'CAM_FRONT')
                    dumper.bind_sensor_output(v_ego.cam_front_left, 'CAM_FRONT_LEFT')
                    dumper.bind_sensor_output(v_ego.cam_front_right, 'CAM_FRONT_RIGHT')
                    dumper.bind_sensor_output(v_ego.cam_back, 'CAM_BACK')
                    dumper.bind_sensor_output(v_ego.cam_back_left, 'CAM_BACK_LEFT')
                    dumper.bind_sensor_output(v_ego.cam_back_right, 'CAM_BACK_RIGHT')
                    dumper.bind_sensor_output(v_ego.lidar, 'LIDAR_TOP')

                    context.wait_ticks(300)

    logger.info('GOODBYE!')