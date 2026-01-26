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
        - Cam_Front
        - Cam_Game
    
    激光雷达:
        - Lidar
    """

    CAM_FRONT_NAME = 'CAM_FRONT'
    CAM_FRONT_TF = CarlaTransform(x=0.0, y=0.0, z=1.85, yaw=0.0)

    CAM_GAME_NAME = 'CAM_GAME'
    CAM_GAME_TF = CarlaTransform(x=-5.5, y=0.0, z=2.5, pitch=-15.0)

    LIDAR_NAME = 'LIDAR'
    LIDAR_TF = CarlaTransform(x=0.0, y=0.0, z=2.2)

    def __init__(
        self,
        context: 'CarlaContext',
        tf: CarlaTransform | carla.Transform,
        bp: carla.ActorBlueprint | str | CarlaBlueprints = CarlaBlueprints.VEHICLE_TESLA_MODEL3,
        name: str = 'Player',
        **attributes: Unpack[Dict[str, Any]],
    ):
        self._context = context
        super().__init__(
            context=context,
            bp=bp,
            tf=tf,
            name=name,
            **attributes,
        )

        self._cam_front: CarlaSensor | None = None
        self._cam_game: CarlaSensor | None = None
        self._lidar: CarlaSensor | None = None

    def __post_init__(self):
        super().__post_init__()
        self._cam_front = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.name + '_' + self.CAM_FRONT_NAME,
            tf=self.CAM_FRONT_TF,
            parent=self,
        )

        self._cam_game = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.name + '_' + self.CAM_GAME_NAME,
            tf=self.CAM_GAME_TF,
            parent=self,
        )

        self._lidar = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_LIDAR_RAY_CAST_SEMANTIC,
            name=self.name + '_' + self.LIDAR_NAME,
            tf=self.LIDAR_TF,
            parent=self,
            rotation_frequency=self._context.fps,
            points_per_second=120_000 * self._context.fps,
            channels=64,
            range=120,
            upper_fov=2,
            lower_fov=-24.5,
        )
    
    def recreate_camera(self, bp) -> CarlaSensor:
        if self._cam_front is not None:
            self._cam_front.destroy()
            self._cam_front = self._context.actors.create_sensor(
                bp=bp,
                name=self.name + '_' + self.CAM_FRONT_NAME,
                tf=self.CAM_FRONT_TF,
                parent=self,
            )
            self._cam_front.spawn()
            
        return self._cam_front

    @property
    def cam_front(self) -> CarlaSensor:
        return self._cam_front

    @property
    def lidar(self) -> CarlaSensor:
        return self._lidar
    
    @property
    def cam_game(self) -> CarlaSensor:
        return self._cam_game