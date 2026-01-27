import carla
from shared.simulator import CarlaContext, CarlaBlueprints
from shared.data import VehicleDirectControl
from shared.utils import Logging

from shared.prefabs import NuScenesVehicle
from shared.scenarios.factorlib import *
from shared.scenarios.injector import Injector
from shared.dataset import NuScenesDumper
from shared.define import FactorLevel

if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('YOLO DEBUG')

    # THIS ROAD SPAWN POINTS
    # 96-107-0-<CROSS>-109-49-51-123-53
    SPAWN_POINT_EGO = 107 
    SPAWN_POINT_ACT = 49

    with CarlaContext() as context:


        v_ego = NuScenesVehicle(context, context.spawn_points[SPAWN_POINT_EGO], name='EGO')

        context.actors.spawn_all()
        context.actors.wait_stable()

        context.traffic.ignore_lights_percentage(v_ego.actor, 100.0)
        context.traffic.set_route(v_ego.actor, ["Straight"])

        # # # SHOPPING CART
        # f = FactorWeatherFog(context, v_ego, level=FactorLevel.HIGH)
        f = FactorWeatherRain(context, v_ego, level=FactorLevel.MEDIUM)

        with Injector(context, f) as injector:

            # v_ego.set_carla_autopilot(enable=True)
            # injector.spin_until_finished(f)


            v_ego.set_carla_autopilot(enable=True)

            context.spin()

    logger.info('GOODBYE!')