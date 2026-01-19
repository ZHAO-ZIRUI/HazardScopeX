import carla
from typing import TYPE_CHECKING, Dict, Any
from typing_extensions import Unpack

from shared.prefabs.nuscenes_vehicle import NuScenesVehicle
from shared.simulator import CarlaContext, CarlaTransform, CarlaBlueprints, CarlaSensor

if TYPE_CHECKING:
    from shared.simulator import CarlaContext

class AutowareVehicle(NuScenesVehicle):

    GNSS_NAME = 'GNSS'
    GNSS_TF = CarlaTransform(x=0.0, y=0.0, z=0.0)

    IMU_NAME = 'IMU'
    IMU_TF = CarlaTransform(x=0.0, y=0.0, z=0.0)

    
    def __init__(
        self,
        context: 'CarlaContext',
        tf: CarlaTransform | carla.Transform,
        bp: carla.ActorBlueprint | str | CarlaBlueprints = CarlaBlueprints.VEHICLE_TESLA_MODEL3,
        name: str = 'NuScenesVehicle',
        **attributes: Unpack[Dict[str, Any]],
    ):
        super().__init__(context, tf, bp, name, **attributes)


    def __post_init__(self):
        super().__post_init__()
        self._gnss = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_OTHER_GNSS,
            name=self.name + '_' + self.GNSS_NAME,
            tf=self.GNSS_TF,
            parent=self,
        )
        self._imu = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_OTHER_IMU,
            name=self.name + '_' + self.IMU_NAME,
            tf=self.IMU_TF,
            parent=self,
        )

    @property
    def gnss(self) -> CarlaSensor:
        return self._gnss

    @property
    def imu(self) -> CarlaSensor:
        return self._imu