import carla
from typing import TYPE_CHECKING, Dict, Any
from typing_extensions import Unpack
import numpy as np
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

    CAM_FRONT_NAME = 'CAM_FRONT'
    CAM_FRONT_TF = CarlaTransform(x=1.50, y=0.00, z=2.00, yaw=0.0)

    CAM_FRONT_LEFT_NAME = 'CAM_FRONT_LEFT'
    # CAM_FRONT_LEFT_TF = CarlaTransform(x=1.50, y=-0.70, z=2.00, yaw=55.0)
    CAM_FRONT_LEFT_TF = CarlaTransform(x=1.50, y=-0.70, z=2.00, yaw=-55.0)

    CAM_FRONT_RIGHT_NAME = 'CAM_FRONT_RIGHT'
    # CAM_FRONT_RIGHT_TF = CarlaTransform(x=1.50, y=0.70, z=2.00, yaw=-55.0)
    CAM_FRONT_RIGHT_TF = CarlaTransform(x=1.50, y=0.70, z=2.00, yaw=55.0)

    CAM_BACK_NAME = 'CAM_BACK'
    CAM_BACK_TF = CarlaTransform(x=-1.50, y=0.00, z=2.00, yaw=180.0)

    CAM_BACK_LEFT_NAME = 'CAM_BACK_LEFT'
    # CAM_BACK_LEFT_TF = CarlaTransform(x=-0.70, y=-0.70, z=2.00, yaw=110.0)
    CAM_BACK_LEFT_TF = CarlaTransform(x=-0.70, y=-0.70, z=2.00, yaw=-110.0)

    CAM_BACK_RIGHT_NAME = 'CAM_BACK_RIGHT'
    # CAM_BACK_RIGHT_TF = CarlaTransform(x=-0.70, y=0.70, z=2.00, yaw=-110.0)
    CAM_BACK_RIGHT_TF = CarlaTransform(x=-0.70, y=0.70, z=2.00, yaw=110.0)

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
        # 左手坐标系 -> 右手坐标系  
        self.CARLA_NUSCENES_TF = np.array([
            [1.0,  0.0, 0.0, 0.0],
            [0.0, -1.0, 0.0, 0.0],
            [0.0,  0.0, 1.0, 0.0],
            [0.0,  0.0, 0.0, 1.0],
        ], dtype=float)
        # carla 左手坐标系下的lidar(x向前 y向右 z向上) -> nuscenes 右手坐标系下的雷达(y向前 x向右 z向上)
        self.CARLA_LIDAR_NUSCENES_LIDAR = np.array(
            [
                [0, 1, 0, 0], # x_N = y_C
                [1, 0, 0, 0], # y_N = x_C
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ],dtype=float)
        # carla 左手坐标系下的camera(x向前 y向右 z向上) -> nuscenes 右手坐标系下的雷达(z向前 x向右 y向)
        self.CARLA_CAM_NUSCENES_CAM = np.array(
            [
                [0,  1,  0, 0],  # x_N = y_C (右)
                [0,  0, -1, 0],  # y_N = -z_C (下)
                [1,  0,  0, 0],  # z_N = x_C (前)
                [0,  0,  0, 1],
            ], dtype=float)
        self._context = context
        resolved_bp = self._context.actors.resolve_blueprint(bp)
        super().__init__(bp=resolved_bp, name=name)
        
        self._context.actors.resolve_transform(self, tf)
        self._context.actors.resolve_attributes(self, attributes)
        self._context.actors.add(self)

        self.vehicle_transform = tf
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

    def carla_lidar_to_nuscenes_lidar_extrinsic(self,lidar_vehicle_rear_carla: np.ndarray) -> np.ndarray:
        """
        将 CARLA 左手系下的 4x4 外参矩阵 (ego_carla <- lidar_carla)
        转换为 nuScenes 右手系下的 4x4 外参矩阵 (ego_nusc <- lidar_nusc)
        其中 lidar_nusc 满足: x右, y前, z上。
        """
        assert lidar_vehicle_rear_carla.shape == (4, 4)
        lidar_vehicle_rear_nusc = self.CARLA_NUSCENES_TF @ lidar_vehicle_rear_carla @ self.CARLA_LIDAR_NUSCENES_LIDAR  
        return lidar_vehicle_rear_nusc  

    def carla_cam_to_nuscenes_cam_extrinsic(self,cam_vehicle_rear_center_tf_carla:np.array) -> np.array:
        """
        将 CARLA 左手系下的 4x4 外参矩阵 (ego_carla <- cam_carla)
        转换为 nuScenes 右手系下的 4x4 外参矩阵 (ego_nusc <- cam_nusc)
        其中 cam_nusc 满足: x右, y下, z前。
        """
        assert cam_vehicle_rear_center_tf_carla.shape == (4, 4)
        cam_vehicle_rear_nusc = self.CARLA_NUSCENES_TF @ cam_vehicle_rear_center_tf_carla @ self.CARLA_CAM_NUSCENES_CAM.T
        return cam_vehicle_rear_nusc

    def carla_ego_to_nuscenes_ego_extrinsic(self,ego_tf_carla):
        '''
        carla左手坐标系下（x向前，y向右，z向上）ego_pose转换为nuscenes车体右手坐标系下（x向前，y向左，z向上）
        '''
        assert ego_tf_carla.shape == (4, 4)
        ego_tf_nus = self.CARLA_NUSCENES_TF @ ego_tf_carla @ self.CARLA_NUSCENES_TF
        return ego_tf_nus

    def get_sensor_vehicle_rear_wheels_center_tf(self) -> dict[str, np.array]:
        '''
        获取传感器到车辆后轮中心的转换矩阵，符合nuscenes数据集 ,nuscenes车体右手坐标系下
        '''
        sensor_vehicle_rear_wheels_center_tf = {}
        vehicle_to_vehicle_rear_tf = self.get_vehicle_center_to_rear_transform_matrix()
        cam_front_to_vehicle_tf = np.array(self.CAM_FRONT_TF.to_carla().get_matrix())
        cam_front_left_to_vehicle_tf = np.array(self.CAM_FRONT_LEFT_TF.to_carla().get_matrix())
        cam_front_right_to_vehicle_tf = np.array(self.CAM_FRONT_RIGHT_TF.to_carla().get_matrix())
        cam_back_to_vehicle_tf = np.array(self.CAM_BACK_TF.to_carla().get_matrix())
        cam_back_left_to_vehicle_tf = np.array(self.CAM_BACK_LEFT_TF.to_carla().get_matrix())
        cam_back_right_to_vehicle_tf = np.array(self.CAM_BACK_RIGHT_TF.to_carla().get_matrix())
        lidar_to_vehicle_tf = np.array(self.LIDAR_TF.to_carla().get_matrix())
        
        # 正相机到车辆后轮中心的转换矩阵  carla左手坐标系下
        cam_front_vehicle_rear_center_tf_carla = vehicle_to_vehicle_rear_tf @ cam_front_to_vehicle_tf
        # 转换为nuscenes车体右手坐标系下 camera(x右, y下, z前)到车体后轮中心（x向前，y向左，z向上）的外参
        cam_front_vehicle_rear_center_tf_nus = self.carla_cam_to_nuscenes_cam_extrinsic(cam_front_vehicle_rear_center_tf_carla)
        # 存入的为nuscenes右手坐标系
        sensor_vehicle_rear_wheels_center_tf[self.CAM_FRONT_NAME] = cam_front_vehicle_rear_center_tf_nus

        # 左前相机到车辆后轮中心的转换矩阵  carla左手坐标系下
        cam_front_left_vehicle_rear_center_tf_carla = vehicle_to_vehicle_rear_tf @ cam_front_left_to_vehicle_tf
        # 转换为nuscenes车体右手坐标系下 camera(x右, y下, z前)到车体后轮中心（x向前，y向左，z向上）的外参
        cam_front_left_vehicle_rear_center_tf_nus = self.carla_cam_to_nuscenes_cam_extrinsic(cam_front_left_vehicle_rear_center_tf_carla)
        sensor_vehicle_rear_wheels_center_tf[self.CAM_FRONT_LEFT_NAME] = cam_front_left_vehicle_rear_center_tf_nus

        # 右前相机到车辆后轮中心的转换矩阵  carla左手坐标系下
        cam_front_right_vehicle_rear_center_tf_carla = vehicle_to_vehicle_rear_tf @ cam_front_right_to_vehicle_tf
        # 转换为nuscenes车体右手坐标系下 camera(x右, y下, z前)到车体后轮中心（x向前，y向左，z向上）的外参
        cam_front_right_vehicle_rear_center_tf_nus = self.carla_cam_to_nuscenes_cam_extrinsic(cam_front_right_vehicle_rear_center_tf_carla)
        sensor_vehicle_rear_wheels_center_tf[self.CAM_FRONT_RIGHT_NAME] = cam_front_right_vehicle_rear_center_tf_nus

        # 正后相机到车辆后轮中心的转换矩阵 carla左手坐标系下
        cam_back_vehicle_rear_center_tf_carla = vehicle_to_vehicle_rear_tf @ cam_back_to_vehicle_tf
        # 转换为nuscenes车体右手坐标系下 camera(x右, y下, z前)到车体后轮中心（x向前，y向左，z向上）的外参
        cam_back_vehicle_rear_center_tf_nus = self.carla_cam_to_nuscenes_cam_extrinsic(cam_back_vehicle_rear_center_tf_carla)
        sensor_vehicle_rear_wheels_center_tf[self.CAM_BACK_NAME] = cam_back_vehicle_rear_center_tf_nus
        
        # 左后相机到车辆后轮中心的转换矩阵  carla左手坐标系下
        cam_back_left_vehicle_rear_center_tf_carla = vehicle_to_vehicle_rear_tf @ cam_back_left_to_vehicle_tf
        # 转换为nuscenes车体右手坐标系下 camera(x右, y下, z前)到车体后轮中心（x向前，y向左，z向上）的外参
        cam_back_left_vehicle_rear_center_tf_nus = self.carla_cam_to_nuscenes_cam_extrinsic(cam_back_left_vehicle_rear_center_tf_carla)
        sensor_vehicle_rear_wheels_center_tf[self.CAM_BACK_LEFT_NAME] = cam_back_left_vehicle_rear_center_tf_nus

        # 右后相机到车辆后轮中心的转换矩阵  carla左手坐标系下
        cam_back_right_vehicle_rear_center_tf_carla = vehicle_to_vehicle_rear_tf @ cam_back_right_to_vehicle_tf
        # 转换为nuscenes车体右手坐标系下 camera(x右, y下, z前)到车体后轮中心（x向前，y向左，z向上）的外参
        cam_back_right_vehicle_rear_center_tf_nus = self.carla_cam_to_nuscenes_cam_extrinsic(cam_back_right_vehicle_rear_center_tf_carla)
        sensor_vehicle_rear_wheels_center_tf[self.CAM_BACK_RIGHT_NAME] = cam_back_right_vehicle_rear_center_tf_nus

        # lidar到车辆后轮中心的转换矩阵 carla左手坐标系下
        lidar_vehicle_rear_center_tf_carla = vehicle_to_vehicle_rear_tf @ lidar_to_vehicle_tf
        # 转换为nuscenes车体右手坐标系下 lidar(x向右 y向前 z向上) 到车体后轮中心（x向前，y向左，z向上）的外参
        lidar_vehicle_rear_center_tf_nus = self.carla_lidar_to_nuscenes_lidar_extrinsic(lidar_vehicle_rear_center_tf_carla)
        sensor_vehicle_rear_wheels_center_tf[self.LIDAR_NAME] = lidar_vehicle_rear_center_tf_nus
        
        # 车体中心 → 后轮中心 左/右手系无关
        sensor_vehicle_rear_wheels_center_tf["vehicle_to_vehicle_rear"] = vehicle_to_vehicle_rear_tf
        return sensor_vehicle_rear_wheels_center_tf
    def _post_init(self):
        # self就是vehicle，不需要再创建
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

        # self.lidar = self._context.actors.create_sensor(
        #     bp=CarlaBlueprints.SENSOR_LIDAR_RAY_CAST_SEMANTIC,
        #     name=self.LIDAR_NAME,
        #     tf=self.LIDAR_TF,
        #     parent=self,
        #     rotation_frequency=self._context.fps,
        #     points_per_second=280000,
        #     channels=128,
        #     range=80,
        #     upper_fov=10,
        #     lower_fov=-40,
        # )
        self.lidar = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_LIDAR_RAY_CAST_SEMANTIC,
            name=self.LIDAR_NAME,
            tf=self.LIDAR_TF,
            parent=self,
            rotation_frequency=self._context.fps,
            points_per_second=120_000 * self._context.fps,
            channels=64,
            range=120,
            upper_fov=2,
            lower_fov=-24.5,
        )
        # self._lidar = self._context.actors.create_sensor(
        #     bp=CarlaBlueprints.SENSOR_LIDAR_RAY_CAST_SEMANTIC,
        #     name=self.name + '_' + self.LIDAR_NAME,
        #     tf=self.LIDAR_TF,
        #     parent=self,
        #     rotation_frequency=self._context.fps,
        #     points_per_second=120_000 * self._context.fps,
        #     channels=64,
        #     range=120,
        #     upper_fov=2,
        #     lower_fov=-24.5,
        # )

