import carla
from shared.simulator import CarlaContext, CarlaBlueprints
from shared.data import VehicleDirectControl
from shared.utils import Logging

from shared.prefabs import PandaSetVehicle
from shared.scenarios.factorlib import *
from shared.scenarios.injector import Injector
from shared.dataset import PandaSetDumper
from shared.define import FactorLevel

if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('YOLO DEBUG')

    # THIS ROAD SPAWN POINTS
    # 96-107-0-<CROSS>-109-49-51-123-53
    SPAWN_POINT_EGO = 93 
    SPAWN_POINT_ACT = 49

    NAME_FACTORS = {
        'FOG_0': (FactorWeatherFog, FactorLevel.NONE),
        'FOG_1': (FactorWeatherFog, FactorLevel.LOW),
        'FOG_2': (FactorWeatherFog, FactorLevel.MEDIUM),
        'FOG_3': (FactorWeatherFog, FactorLevel.HIGH),
        'RAIN_0': (FactorWeatherRain, FactorLevel.NONE),
        'RAIN_1': (FactorWeatherRain, FactorLevel.LOW),
        'RAIN_2': (FactorWeatherRain, FactorLevel.MEDIUM),
        'RAIN_3': (FactorWeatherRain, FactorLevel.HIGH),
    }
    
    for name, (factor_class, level) in NAME_FACTORS.items():

        with CarlaContext() as context:


            v_ego = PandaSetVehicle(context, context.spawn_points[SPAWN_POINT_EGO], name='EGO')

            context.actors.spawn_all()
            context.actors.wait_stable()

            context.traffic.ignore_lights_percentage(v_ego.actor, 100.0)
            context.traffic.set_route(v_ego.actor, ["Straight"])

            # Factors
            f1 = factor_class(context, v_ego, level=level)
            f2 = FactorTemp(context, v_ego)

            with Injector(context, f1, f2) as injector:

                v_ego.set_carla_autopilot(enable=True)
                # injector.spin_until_finished(f)

                context.wait_seconds(3)

                with PandaSetDumper(context, ego_vehicle=v_ego, name=name) as dumper:
                    dumper.bind_sensor_output(v_ego.cam_front)
                    dumper.bind_sensor_output(v_ego.cam_front_left)
                    dumper.bind_sensor_output(v_ego.cam_front_right)
                    dumper.bind_sensor_output(v_ego.cam_back)
                    dumper.bind_sensor_output(v_ego.left_camera)
                    dumper.bind_sensor_output(v_ego.right_camera)
                    
                    dumper.bind_sensor_output(v_ego.lidar)
                    context.wait_ticks(120, no_log=True)
                # context.spin()

    logger.info('GOODBYE!')