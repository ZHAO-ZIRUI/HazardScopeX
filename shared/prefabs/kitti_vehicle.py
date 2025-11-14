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

    LIDAR_NAME = 'LIDAR_MAIN'
    LIDAR_TF = CarlaTransform(x=0.0, y=0.0, z=1.93)

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

        self.cam_front_rgb: CarlaSensor | None = None
        self.cam_front_depth: CarlaSensor | None = None
        self.cam_left_rgb: CarlaSensor | None = None
        self.cam_left_depth: CarlaSensor | None = None
        self.cam_right_rgb: CarlaSensor | None = None
        self.cam_right_depth: CarlaSensor | None = None
        self.cam_back_rgb: CarlaSensor | None = None
        self.cam_back_depth: CarlaSensor | None = None
        self.lidar: CarlaSensor | None = None

        self._post_init()

    @property
    def main_camera(self) -> CarlaSensor:
        return self.cam_front_rgb

    @property
    def main_lidar(self) -> CarlaSensor:
        return self.lidar

    def _post_init(self):
        # self就是vehicle，不需要再创建
        self.cam_front_rgb = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_FRONT_NAME + '_RGB',
            tf=self.CAM_FRONT_TF,
            parent=self,
        )

        self.cam_left_rgb = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_LEFT_NAME + '_RGB',
            tf=self.CAM_LEFT_TF,
            parent=self,
        )

        self.cam_right_rgb = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_RIGHT_NAME + '_RGB',
            tf=self.CAM_RIGHT_TF,
            parent=self,
        )

        self.cam_back_rgb = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_BACK_NAME + '_RGB',
            tf=self.CAM_BACK_TF,
            parent=self,
        )

        self.cam_front_depth = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_DEPTH,
            name=self.CAM_FRONT_NAME + '_DEPTH',
            tf=self.CAM_FRONT_TF,
            parent=self,
        )

        self.cam_left_depth = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_DEPTH,
            name=self.CAM_LEFT_NAME + '_DEPTH',
            tf=self.CAM_LEFT_TF,
            parent=self,
        )

        self.cam_right_depth = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_DEPTH,
            name=self.CAM_RIGHT_NAME + '_DEPTH',
            tf=self.CAM_RIGHT_TF,
            parent=self,
        )

        self.cam_back_depth = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_DEPTH,
            name=self.CAM_BACK_NAME + '_DEPTH',
            tf=self.CAM_BACK_TF,
            parent=self,
        )

        self.lidar = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_LIDAR_RAY_CAST_SEMANTIC,
            name=self.LIDAR_NAME,
            tf=self.LIDAR_TF,
            parent=self,
            rotation_frequency=self._context.fps,
            points_per_second=1000000,
            channels=64,
            range=100,
            upper_fov=2,
            lower_fov=-24.8,
        )