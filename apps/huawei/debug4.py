import carla
from shared.simulator import CarlaContext, CarlaBlueprints
from shared.data import VehicleDirectControl
from shared.utils import Logging

from shared.prefabs import NuScenesVehicle
from shared.scenarios.factorlib import *
from shared.scenarios.injector import Injector
from shared.dataset import NuScenesDumper

if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('YOLO DEBUG')

    # THIS ROAD SPAWN POINTS
    # 96-107-0-<CROSS>-109-49-51-123-53
    SPAWN_POINT_EGO = 107 
    SPAWN_POINT_ACT = 49

    with CarlaContext() as context:

        # context.change_map('Town03')

        v_ego = NuScenesVehicle(context, context.spawn_points[SPAWN_POINT_EGO], name='EGO')

        context.actors.spawn_all()
        context.actors.wait_stable()

        context.traffic.ignore_lights_percentage(v_ego.actor, 100.0)
        context.traffic.set_route(v_ego.actor, ["Straight"])

        # # # SHOPPING CART
        f = FactorCaseConstructionArea(context, v_ego, triggered_seconds=20)

        with Injector(context, f) as injector:

            # v_ego.set_carla_autopilot(enable=True)
            # injector.spin_until_finished(f)


            v_ego.set_carla_autopilot(enable=True)

            context.wait_seconds(13)
            with NuScenesDumper(context, ego_vehicle=v_ego) as dumper:
                dumper.bind_sensor_output(v_ego.cam_front, v_ego.cam_front.name)
                dumper.bind_sensor_output(v_ego.cam_front_left, v_ego.cam_front_left.name)
                dumper.bind_sensor_output(v_ego.cam_front_right, v_ego.cam_front_right.name)
                dumper.bind_sensor_output(v_ego.cam_back, v_ego.cam_back.name)
                dumper.bind_sensor_output(v_ego.cam_back_left, v_ego.cam_back_left.name)
                dumper.bind_sensor_output(v_ego.cam_back_right, v_ego.cam_back_right.name)
                
                # 绑定语义激光雷达
                dumper.bind_sensor_output(v_ego.lidar, v_ego.lidar.name)

                context.wait_seconds(20)
                # injector.spin_until_finished(f)

            # context.spin()

    logger.info('GOODBYE!')