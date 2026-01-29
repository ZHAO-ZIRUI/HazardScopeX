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
   

    with CarlaContext() as context:

        context.change_map('SUSTech_COE_ParkingLot')

    logger.info('GOODBYE!')