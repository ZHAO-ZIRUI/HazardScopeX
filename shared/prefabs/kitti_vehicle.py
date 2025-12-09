import carla
from typing import TYPE_CHECKING, Dict, Any
from typing_extensions import Unpack

from shared.simulator import CarlaTransform, CarlaSensor, CarlaVehicle, CarlaBlueprints

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


class KittiVehicle(CarlaVehicle):
    """
    与 KITTI 数据集一致的仿真车辆

    相机:
        - cam_front_rgb
        - cam_front_depth
        - cam_left_rgb
        - cam_left_depth
        - cam_right_rgb
        - cam_right_depth
        - cam_back_rgb
        - cam_back_depth
        - cam_game
    
    激光雷达:
        - lidar
    """

    CAM_FRONT_NAME = 'CAM_FRONT'
    CAM_FRONT_TF = CarlaTransform(x=0.06, y=0.0, z=1.85, yaw=0.0)

    CAM_LEFT_NAME = 'CAM_LEFT'
    CAM_LEFT_TF = CarlaTransform(x=0.06, y=-0.27, z=1.85, yaw=-90.0)

    CAM_RIGHT_NAME = 'CAM_RIGHT'
    CAM_RIGHT_TF = CarlaTransform(x=0.06, y=0.27, z=1.85, yaw=90.0)

    CAM_BACK_NAME = 'CAM_BACK'
    CAM_BACK_TF = CarlaTransform(x=-0.06, y=0.0, z=1.85, yaw=180.0)

    CAM_GAME_NAME = 'CAM_GAME'
    CAM_GAME_TF = CarlaTransform(x=-5.5, y=0.0, z=2.5, pitch=-15.0)

    LIDAR_NAME = 'LIDAR_MAIN'
    LIDAR_TF = CarlaTransform(x=0.0, y=0.0, z=1.93)

    def __init__(
        self,
        context: 'CarlaContext',
        tf: CarlaTransform | carla.Transform,
        bp: carla.ActorBlueprint | str | CarlaBlueprints = CarlaBlueprints.VEHICLE_TESLA_MODEL3,
        name: str = 'KittiVehicle',
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

        self._cam_front_rgb: CarlaSensor | None = None
        self._cam_front_depth: CarlaSensor | None = None
        self._cam_left_rgb: CarlaSensor | None = None
        self._cam_left_depth: CarlaSensor | None = None
        self._cam_right_rgb: CarlaSensor | None = None
        self._cam_right_depth: CarlaSensor | None = None
        self._cam_back_rgb: CarlaSensor | None = None
        self._cam_back_depth: CarlaSensor | None = None
        self._cam_game: CarlaSensor | None = None
        self._lidar: CarlaSensor | None = None

    def __post_init__(self):
        super().__post_init__()
        self._cam_front_rgb = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.name + '_' + self.CAM_FRONT_NAME + '_RGB',
            tf=self.CAM_FRONT_TF,
            parent=self,
        )

        self._cam_left_rgb = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.name + '_' + self.CAM_LEFT_NAME + '_RGB',
            tf=self.CAM_LEFT_TF,
            parent=self,
        )

        self._cam_right_rgb = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.name + '_' + self.CAM_RIGHT_NAME + '_RGB',
            tf=self.CAM_RIGHT_TF,
            parent=self,
        )

        self._cam_back_rgb = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.name + '_' + self.CAM_BACK_NAME + '_RGB',
            tf=self.CAM_BACK_TF,
            parent=self,
        )

        self._cam_front_depth = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_DEPTH,
            name=self.name + '_' + self.CAM_FRONT_NAME + '_DEPTH',
            tf=self.CAM_FRONT_TF,
            parent=self,
        )

        self._cam_left_depth = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_DEPTH,
            name=self.name + '_' + self.CAM_LEFT_NAME + '_DEPTH',
            tf=self.CAM_LEFT_TF,
            parent=self,
        )

        self._cam_right_depth = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_DEPTH,
            name=self.name + '_' + self.CAM_RIGHT_NAME + '_DEPTH',
            tf=self.CAM_RIGHT_TF,
            parent=self,
        )

        self._cam_back_depth = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_DEPTH,
            name=self.name + '_' + self.CAM_BACK_NAME + '_DEPTH',
            tf=self.CAM_BACK_TF,
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

    @property
    def cam_front_rgb(self) -> CarlaSensor:
        return self._cam_front_rgb

    @property
    def cam_front_depth(self) -> CarlaSensor:
        return self._cam_front_depth

    @property
    def cam_left_rgb(self) -> CarlaSensor:
        return self._cam_left_rgb

    @property
    def cam_left_depth(self) -> CarlaSensor:
        return self._cam_left_depth

    @property
    def cam_right_rgb(self) -> CarlaSensor:
        return self._cam_right_rgb

    @property
    def cam_right_depth(self) -> CarlaSensor:
        return self._cam_right_depth

    @property
    def cam_back_rgb(self) -> CarlaSensor:
        return self._cam_back_rgb

    @property
    def cam_back_depth(self) -> CarlaSensor:
        return self._cam_back_depth

    @property
    def cam_game(self) -> CarlaSensor:
        return self._cam_game

    @property
    def lidar(self) -> CarlaSensor:
        return self._lidar

    @property
    def main_camera(self) -> CarlaSensor:
        return self._cam_front_rgb

    @property
    def main_lidar(self) -> CarlaSensor:
        return self._lidar