import carla
from typing import TYPE_CHECKING, Dict, Any
from typing_extensions import Unpack

from shared.simulator import CarlaTransform, CarlaSensor, CarlaVehicle, CarlaBlueprints

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


class NuScenesVehicle(CarlaVehicle):
    """
    与 nuScenes 数据集一致的仿真车辆

    相机:
        - cam_front (CAM_FRONT)
        - cam_front_left (CAM_FRONT_RIGHT)
        - cam_front_right (CAM_FRONT_LEFT)
        - cam_back (CAM_BACK)
        - cam_back_left (CAM_BACK_RIGHT)
        - cam_back_right (CAM_BACK_LEFT)

    激光雷达:
        - lidar (LIDAR_TOP)

    注意: nuScenes 的相机命名约定是从车辆前方看，左侧是 FRONT_LEFT，右侧是 FRONT_RIGHT
    """

    CAM_GAME_NAME = 'CAM_GAME'
    CAM_GAME_TF = CarlaTransform(x=-5.5, y=0.0, z=2.5, pitch=-15.0)

    CAM_FRONT_NAME = 'CAM_FRONT'
    CAM_FRONT_TF = CarlaTransform(x=1.50, y=0.00, z=2.00, yaw=0.0)

    CAM_FRONT_LEFT_NAME = 'CAM_FRONT_LEFT'
    CAM_FRONT_LEFT_TF = CarlaTransform(x=1.50, y=-0.70, z=2.00, yaw=55.0)

    CAM_FRONT_RIGHT_NAME = 'CAM_FRONT_RIGHT'
    CAM_FRONT_RIGHT_TF = CarlaTransform(x=1.50, y=0.70, z=2.00, yaw=-55.0)

    CAM_BACK_NAME = 'CAM_BACK'
    CAM_BACK_TF = CarlaTransform(x=-1.50, y=0.00, z=2.00, yaw=180.0)

    CAM_BACK_LEFT_NAME = 'CAM_BACK_LEFT'
    CAM_BACK_LEFT_TF = CarlaTransform(x=-0.70, y=-0.70, z=2.00, yaw=110.0)

    CAM_BACK_RIGHT_NAME = 'CAM_BACK_RIGHT'
    CAM_BACK_RIGHT_TF = CarlaTransform(x=-0.70, y=0.70, z=2.00, yaw=-110.0)

    LIDAR_NAME = 'LIDAR_TOP'
    LIDAR_TF = CarlaTransform(x=0.00, y=0.00, z=2.0)

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

        self.cam_game: CarlaSensor | None = None
        self.cam_front: CarlaSensor | None = None
        self.cam_front_left: CarlaSensor | None = None
        self.cam_front_right: CarlaSensor | None = None
        self.cam_back: CarlaSensor | None = None
        self.cam_back_left: CarlaSensor | None = None
        self.cam_back_right: CarlaSensor | None = None
        self.lidar: CarlaSensor | None = None

        self._post_init()

    @property
    def main_camera(self) -> CarlaSensor:
        return self.cam_front

    @property
    def main_lidar(self) -> CarlaSensor:
        return self.lidar

    def _post_init(self):
        # self就是vehicle，不需要再创建
        self.cam_game = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_GAME_NAME,
            tf=self.CAM_GAME_TF,
            parent=self,
        )

        self.cam_front = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_FRONT_NAME,
            tf=self.CAM_FRONT_TF,
            parent=self,
            image_size_x=1600,
            image_size_y=900,
            fov=70,
        )

        self.cam_front_left = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_FRONT_LEFT_NAME,
            tf=self.CAM_FRONT_LEFT_TF,
            parent=self,
            image_size_x=1600,
            image_size_y=900,
            fov=70,
        )

        self.cam_front_right = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_FRONT_RIGHT_NAME,
            tf=self.CAM_FRONT_RIGHT_TF,
            parent=self,
            image_size_x=1600,
            image_size_y=900,
            fov=70,
        )

        self.cam_back = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_BACK_NAME,
            tf=self.CAM_BACK_TF,
            parent=self,
            image_size_x=1600,
            image_size_y=900,
            fov=70,
        )

        self.cam_back_left = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_BACK_LEFT_NAME,
            tf=self.CAM_BACK_LEFT_TF,
            parent=self,
            image_size_x=1600,
            image_size_y=900,
            fov=70,
        )

        self.cam_back_right = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_BACK_RIGHT_NAME,
            tf=self.CAM_BACK_RIGHT_TF,
            parent=self,
            image_size_x=1600,
            image_size_y=900,
            fov=70,
        )

        self.lidar = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_LIDAR_RAY_CAST_SEMANTIC,
            name=self.LIDAR_NAME,
            tf=self.LIDAR_TF,
            parent=self,
            rotation_frequency=self._context.fps,
            points_per_second=280000,
            channels=128,
            range=80,
            upper_fov=10,
            lower_fov=-40,
        )

