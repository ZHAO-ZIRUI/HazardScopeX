import carla
from typing import TYPE_CHECKING

from shared.simulator import CarlaTransform, CarlaSensor, CarlaVehicle, CarlaBlueprints

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


class KittiVehiclePrefab:
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
    CAM_FRONT_TF = CarlaTransform(x=0.06, y=0.0, z=1.75)

    CAM_LEFT_NAME = 'CAM_LEFT'
    CAM_LEFT_TF = CarlaTransform(x=0.06, y=-0.27, z=1.75)

    CAM_RIGHT_NAME = 'CAM_RIGHT'
    CAM_RIGHT_TF = CarlaTransform(x=0.06, y=0.27, z=1.75)

    CAM_BACK_NAME = 'CAM_BACK'
    CAM_BACK_TF = CarlaTransform(x=-0.06, y=0.0, z=1.75)

    LIDAR_NAME = 'LIDAR_MAIN'
    LIDAR_TF = CarlaTransform(x=0.0, y=0.0, z=1.83)

    def __init__(self, context: 'CarlaContext', tf: CarlaTransform | carla.Transform):
        self._context = context

        self._tf: CarlaTransform | carla.Transform = tf
        self.vehicle: CarlaVehicle | None = None

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

        if isinstance(self._tf, carla.Transform):
            vehicle_tf = self._tf
        else:
            vehicle_tf = self._tf.to_carla()

        self.vehicle = self._context.actors.create_vehicle(
            bp=CarlaBlueprints.VEHICLE_TESLA_MODEL3,
            tf=vehicle_tf,
        )

        self.cam_front_rgb = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_FRONT_NAME + '_RGB',
            tf=self.CAM_FRONT_TF,
            parent=self.vehicle,
        )

        self.cam_left_rgb = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_LEFT_NAME + '_RGB',
            tf=self.CAM_LEFT_TF,
            parent=self.vehicle,
        )

        self.cam_right_rgb = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_RIGHT_NAME + '_RGB',
            tf=self.CAM_RIGHT_TF,
            parent=self.vehicle,
        )

        self.cam_back_rgb = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.CAM_BACK_NAME + '_RGB',
            tf=self.CAM_BACK_TF,
            parent=self.vehicle,
        )

        self.cam_front_depth = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_DEPTH,
            name=self.CAM_FRONT_NAME + '_DEPTH',
            tf=self.CAM_FRONT_TF,
            parent=self.vehicle,
        )

        self.cam_left_depth = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_DEPTH,
            name=self.CAM_LEFT_NAME + '_DEPTH',
            tf=self.CAM_LEFT_TF,
            parent=self.vehicle,
        )

        self.cam_right_depth = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_DEPTH,
            name=self.CAM_RIGHT_NAME + '_DEPTH',
            tf=self.CAM_RIGHT_TF,
            parent=self.vehicle,
        )

        self.cam_back_depth = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_DEPTH,
            name=self.CAM_BACK_NAME + '_DEPTH',
            tf=self.CAM_BACK_TF,
            parent=self.vehicle,
        )

        self.lidar = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_LIDAR_RAY_CAST_SEMANTIC,
            name=self.LIDAR_NAME,
            tf=self.LIDAR_TF,
            parent=self.vehicle,
            rotation_frequency = self._context.fps,
            points_per_second=1000000,
            channels=64,
            range=100,
            upper_fov=2,
            lower_fov=-24.8,
        )