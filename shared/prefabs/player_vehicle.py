import carla
from typing import TYPE_CHECKING, Dict, Any
from typing_extensions import Unpack

from shared.simulator import CarlaTransform, CarlaSensor, CarlaVehicle, CarlaBlueprints

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


class PlayerVehicle(CarlaVehicle):
    """
    玩家车辆, 包含车后视角相机

    相机:
        - cam_main
        - cam_game
    
    激光雷达:
        - lidar_main
    """

    CAM_MAIN_NAME = 'CAM_MAIN'
    CAM_MAIN_TF = CarlaTransform(x=0.0, y=0.0, z=1.85, yaw=0.0)

    CAM_GAME_NAME = 'CAM_GAME'
    CAM_GAME_TF = CarlaTransform(x=-5.5, y=0.0, z=2.5, pitch=-15.0)

    LIDAR_MAIN_NAME = 'LIDAR_MAIN'
    LIDAR_MAIN_TF = CarlaTransform(x=0.0, y=0.0, z=2.2)

    def __init__(
            self,
            context: 'CarlaContext',
            tf: CarlaTransform | carla.Transform,
            bp: carla.ActorBlueprint | str | CarlaBlueprints = CarlaBlueprints.VEHICLE_TESLA_MODEL3,
            name: str = '',
            **attributes: Unpack[Dict[str, Any]],
        ):
            self._context = context
            resolved_bp = self._context.actors.resolve_blueprint(bp)
            super().__init__(bp=resolved_bp, name=name)
            self._context.actors.resolve_transform(self, tf)
            self._context.actors.resolve_attributes(self, attributes)
            self._context.actors.add(self)

            self.cam_main: CarlaSensor | None = None
            self.cam_game: CarlaSensor | None = None
            self.lidar_main: CarlaSensor | None = None

            self._post_init()
    
    @property
    def cam_main(self) -> CarlaSensor:
        return self.cam_main

    @property
    def lidar_main(self) -> CarlaSensor:
        return self.lidar_main
    
    @property
    def cam_game(self) -> CarlaSensor:
        return self.cam_game

    def _post_init(self):
        self.cam_main = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_MAIN_NAME,
            tf=self.CAM_MAIN_TF,
            parent=self,
        )

        self.cam_game = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_GAME_NAME,
            tf=self.CAM_GAME_TF,
            parent=self,
        )

        self.lidar_main = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_LIDAR_RAY_CAST,
            name=self.LIDAR_MAIN_NAME,
            tf=self.LIDAR_MAIN_TF,
            parent=self,
            rotation_frequency=self._context.fps,
            points_per_second=1000000,
            channels=64,
            range=100,
            upper_fov=2,
            lower_fov=-24.8,
        )