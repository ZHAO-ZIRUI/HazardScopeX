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

    with CarlaContext() as context:


        v_ego = PandaSetVehicle(context, context.spawn_points[SPAWN_POINT_EGO], name='EGO')

        context.actors.spawn_all()
        context.actors.wait_stable()

        context.traffic.ignore_lights_percentage(v_ego.actor, 100.0)
        context.traffic.set_route(v_ego.actor, ["Straight"])

        # # # SHOPPING CART
        # f1 = FactorWeatherFog(context, v_ego, level=FactorLevel.HIGH)
        f1 = FactorWeatherRain(context, v_ego, level=FactorLevel.HIGH)
        f2 = FactorTemp(context, v_ego)

        with Injector(context, f1, f2) as injector:

            v_ego.set_carla_autopilot(enable=True)
            # injector.spin_until_finished(f)

            context.wait_seconds(3)

            with PandaSetDumper(context, ego_vehicle=v_ego) as dumper:
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