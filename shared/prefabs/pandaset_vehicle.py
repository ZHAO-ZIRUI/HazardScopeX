import carla
from typing import TYPE_CHECKING, Dict, Any
from typing_extensions import Unpack
import numpy as np

from shared.simulator import CarlaTransform, CarlaSensor, CarlaVehicle, CarlaBlueprints

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


class PandaSetVehicle(CarlaVehicle):
    """
    与 PandaSet 数据集一致的仿真车辆

    相机:

    
    激光雷达:
        - lidar (LIDAR_TOP)

    注意: nuScenes 的相机命名约定是从车辆前方看，左侧是 FRONT_LEFT，右侧是 FRONT_RIGHT
    """

    FRONT_CAMERA_NAME = "front_camera"
    FRONT_LEFT_CAMERA_NAME = "front_left_camera"
    FRONT_RIGHT_CAMERA_NAME = "front_right_camera"
    BACK_CAMERA_NAME = "back_camera"
    LEFT_CAMERA_NAME = "left_camera"
    RIGHT_CAMERA_NAME = "right_camera"
    LIDAR_NAME = "lidar"

    VEHICLE_SENSORS = [
        FRONT_CAMERA_NAME,
        FRONT_LEFT_CAMERA_NAME,
        FRONT_RIGHT_CAMERA_NAME,
        BACK_CAMERA_NAME,
        LEFT_CAMERA_NAME,
        RIGHT_CAMERA_NAME,
        LIDAR_NAME,
    ]
   
    # =========================
    # CARLA 中的安装位姿（相对车辆中心坐标系）
    # CARLA: x前 y右 z上（左手系）
    # =========================
    FRONT_CAMERA_TF = CarlaTransform(x=1.50, y=0.00, z=2.00, yaw=0.0)
    FRONT_LEFT_CAMERA_TF = CarlaTransform(x=1.50, y=-0.70, z=2.00, yaw=-55.0)
    FRONT_RIGHT_CAMERA_TF = CarlaTransform(x=1.50, y=0.70, z=2.00, yaw=55.0)
    BACK_CAMERA_TF = CarlaTransform(x=-1.50, y=0.00, z=2.00, yaw=180.0)
    # 侧向相机（合理默认值；后续可根据传感器配置图精调）
    LEFT_CAMERA_TF = CarlaTransform(x=0.00, y=-0.90, z=2.00, yaw=-90.0)
    RIGHT_CAMERA_TF = CarlaTransform(x=0.00, y=0.90, z=2.00, yaw=90.0)
    LIDAR_TF = CarlaTransform(x=0.00, y=0.00, z=2.00)

    # CAM_GAME_NAME = 'game_camera'
    # CAM_GAME_TF = CarlaTransform(x=-5.5, y=0.0, z=2.5, pitch=-15.0)

    POINT_FORMAT = np.dtype([
        ('x', '<f4'), 
        ('y', '<f4'), 
        ('z', '<f4'),
        ('cos_inc_angle', '<f4'),
        ('object_id', '<u4'), 
        ('object_semantic_tag', '<u4'),
        ('channel', '<u4')
    ])



    def __init__(
        self,
        context: 'CarlaContext',
        tf: CarlaTransform | carla.Transform,
        bp: carla.ActorBlueprint | str | CarlaBlueprints = CarlaBlueprints.VEHICLE_TESLA_MODEL3,
        name: str = 'PandaSetVehicle',
        **attributes: Unpack[Dict[str, Any]],
    ):
        # carla 左手坐标系(x向前 y向右 z向上) -> Pandaset ego坐标系 右手坐标系(x向前 y向左 z向上)
        self.CARLA_TO_PANDASET_EGO_BASIS = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, -1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ], dtype=float)

        # # carla 左手坐标系下的lidar(x向前 y向右 z向上) -> pandaset 右手坐标系下的雷达(x向左 y向后  z向上)
        # self.CARLA_LIDAR_TO_PANDASET_LIDAR = np.array(
        #     [
        #         [0.0, -1.0, 0.0, 0.0], 
        #         [-1.0, 0.0, 0.0, 0.0], 
        #         [0.0, 0.0, 1.0, 0.0],
        #         [0.0, 0.0, 0.0, 1.0]
        #     ],dtype=float)

        # CARLA lidar(x前,y右,z上) -> PandaSet lidar(x前,y左,z上)
        self.CARLA_LIDAR_TO_PANDASET_LIDAR = np.array([
            [1.0,  0.0, 0.0, 0.0],
            [0.0, -1.0, 0.0, 0.0],
            [0.0,  0.0, 1.0, 0.0],
            [0.0,  0.0, 0.0, 1.0],
        ], dtype=float)

        
        # carla 左手坐标系下的camera(x向前 y向右 z向上) -> pandaset 右手坐标系下的camera(x向右 y向下 z向前)
        self.CARLA_CAM_TO_PANDASET_CAM = np.array(
            [
                [0.0, 1.0, 0.0, 0.0], 
                [0.0, 0.0, -1.0, 0.0], 
                [1.0, 0.0, 0.0, 0.0],  
                [0.0, 0.0, 0.0, 1.0],
            ], dtype=float)
        
        self._context = context
        super().__init__(
            context=context,
            bp=bp,
            tf=tf,
            name=name,
            **attributes,
        )

        self._front_camera: CarlaSensor | None = None
        self._front_left_camera: CarlaSensor | None = None
        self._front_right_camera: CarlaSensor | None = None
        self._back_camera: CarlaSensor | None = None
        self._left_camera: CarlaSensor | None = None
        self._right_camera: CarlaSensor | None = None
        # self._cam_game: CarlaSensor | None = None
        self._lidar: CarlaSensor | None = None

    # =========================================================
    # 外参转换：CARLA -> PandaSet
    # 输入 T_carla: ego_carla <- sensor_carla
    # 输出 T_pandaset: ego_pandaset <- sensor_pandaset
    #
    # 公式（坐标基变换 + 传感器轴定义变换）：
    #   p_ego_p = B * p_ego_c
    #   p_sensor_p = A * p_sensor_c
    #   p_ego_c = T_c * p_sensor_c
    # => p_ego_p = B * T_c * A^{-1} * p_sensor_p
    # => T_p = B * T_c * A^{-1}
    # =========================================================

    def carla_cam_to_pandaset_cam_extrinsic(self, T_ego_cam_carla: np.ndarray) -> np.ndarray:
        assert T_ego_cam_carla.shape == (4, 4)
        B = self.CARLA_TO_PANDASET_EGO_BASIS
        A = self.CARLA_CAM_TO_PANDASET_CAM
        return B @ T_ego_cam_carla @ A.T  # A^{-1} = A.T（纯旋转）
    
    def carla_lidar_to_pandaset_lidar_extrinsic(self, T_ego_lidar_carla: np.ndarray) -> np.ndarray:
        assert T_ego_lidar_carla.shape == (4, 4)
        B = self.CARLA_TO_PANDASET_EGO_BASIS
        A = self.CARLA_LIDAR_TO_PANDASET_LIDAR
        return B @ T_ego_lidar_carla @ A.T  # A^{-1} = A.T（纯旋转）

    def carla_ego_to_pandaset_ego_extrinsic(self, T_world_ego_carla: np.ndarray) -> np.ndarray:
        """
        CARLA(左手) ego/world pose -> PandaSet ego/world pose
        """
        assert T_world_ego_carla.shape == (4, 4)
        B = self.CARLA_TO_PANDASET_EGO_BASIS
        return B @ T_world_ego_carla @ B

    def get_sensor_vehicle_rear_wheels_center_tf(self) -> dict[str, np.ndarray]:
        """
        返回：各传感器相对“后轴中心(ego frame)”的外参矩阵（ego <- sensor），以及车体中心->后轴的矩阵。

        注意：
        - `*_pandaset` 均为 PandaSet 右手系表达
        - `vehicle_center_to_rear_carla` 为 CARLA 表达，保留是为了你若还要在 carla world 里先算后轴 pose
        """
        out: dict[str, np.ndarray] = {}

        # 车体中心 -> 后轴中心（baselink）: CARLA 坐标系
        vehicle_center_to_rear_carla = self.get_vehicle_center_to_baselink_transform_matrix()
        # self.logger.debug(f"the vehicle_center_to_rear_carla is:\n{vehicle_center_to_rear_carla}")

        # 各传感器：vehicle <- sensor（CARLA）
        T_vehicle_front_c = np.array(self.FRONT_CAMERA_TF.to_carla().get_matrix())
        # self.logger.debug(f"the T_vehicle_front_c carla is:\n{T_vehicle_front_c}")
        T_vehicle_front_left_c = np.array(self.FRONT_LEFT_CAMERA_TF.to_carla().get_matrix())
        # self.logger.debug(f"the T_vehicle_front_left_c carla is:\n{T_vehicle_front_left_c}")
        T_vehicle_front_right_c = np.array(self.FRONT_RIGHT_CAMERA_TF.to_carla().get_matrix())
        # self.logger.debug(f"the T_vehicle_front_right_c carla is:\n{T_vehicle_front_right_c}")
        T_vehicle_back_c = np.array(self.BACK_CAMERA_TF.to_carla().get_matrix())
        # self.logger.debug(f"the T_vehicle_back_c carla is:\n{T_vehicle_back_c}")
        T_vehicle_left_c = np.array(self.LEFT_CAMERA_TF.to_carla().get_matrix())
        # self.logger.debug(f"the T_vehicle_left_c carla is:\n{T_vehicle_left_c}")
        T_vehicle_right_c = np.array(self.RIGHT_CAMERA_TF.to_carla().get_matrix())
        # self.logger.debug(f"the T_vehicle_right_c carla is:\n{T_vehicle_right_c}")
        T_vehicle_lidar_c = np.array(self.LIDAR_TF.to_carla().get_matrix())
        # self.logger.debug(f"the T_vehicle_lidar_c carla is:\n{T_vehicle_lidar_c}")

        # 后轴 <- 车体中心 <- 传感器
        T_rear_front_c = vehicle_center_to_rear_carla @ T_vehicle_front_c
        # self.logger.debug(f"the T_rear_front_c carla is:\n{T_rear_front_c}")
        T_rear_front_left_c = vehicle_center_to_rear_carla @ T_vehicle_front_left_c
        # self.logger.debug(f"the T_rear_front_left_c carla is:\n{T_rear_front_left_c}")
        T_rear_front_right_c = vehicle_center_to_rear_carla @ T_vehicle_front_right_c
        # self.logger.debug(f"the T_rear_front_right_c carla is:\n{T_rear_front_right_c}")
        T_rear_back_c = vehicle_center_to_rear_carla @ T_vehicle_back_c
        # self.logger.debug(f"the T_rear_back_c carla is:\n{T_rear_back_c}")
        T_rear_left_c = vehicle_center_to_rear_carla @ T_vehicle_left_c
        # self.logger.debug(f"the T_rear_left_c carla is:\n{T_rear_left_c}")
        T_rear_right_c = vehicle_center_to_rear_carla @ T_vehicle_right_c
        # self.logger.debug(f"the T_rear_right_c carla is:\n{T_rear_right_c}")
        T_rear_lidar_c = vehicle_center_to_rear_carla @ T_vehicle_lidar_c
        # self.logger.debug(f"the T_rear_lidar_c carla is:\n{T_rear_lidar_c}")

        # 转到 PandaSet 坐标系 + 传感器轴定义
        out[self.FRONT_CAMERA_NAME] = self.carla_cam_to_pandaset_cam_extrinsic(T_rear_front_c)
        # self.logger.debug(f"the front_camera_rear pandaset extrinsic is:\n{out[self.FRONT_CAMERA_NAME]}")
        out[self.FRONT_LEFT_CAMERA_NAME] = self.carla_cam_to_pandaset_cam_extrinsic(T_rear_front_left_c)
        # self.logger.debug(f"the front_left_camera_rear pandaset extrinsic is:\n{out[self.FRONT_LEFT_CAMERA_NAME]}")
        out[self.FRONT_RIGHT_CAMERA_NAME] = self.carla_cam_to_pandaset_cam_extrinsic(T_rear_front_right_c)
        # self.logger.debug(f"the front_right_camera_rear pandaset extrinsic is:\n{out[self.FRONT_RIGHT_CAMERA_NAME]}")
        out[self.BACK_CAMERA_NAME] = self.carla_cam_to_pandaset_cam_extrinsic(T_rear_back_c)
        # self.logger.debug(f"the back_camera_rear pandaset extrinsic is:\n{out[self.BACK_CAMERA_NAME]}")
        out[self.LEFT_CAMERA_NAME] = self.carla_cam_to_pandaset_cam_extrinsic(T_rear_left_c)
        # self.logger.debug(f"the left_camera_rear pandaset extrinsic is:\n{out[self.LEFT_CAMERA_NAME]}")
        out[self.RIGHT_CAMERA_NAME] = self.carla_cam_to_pandaset_cam_extrinsic(T_rear_right_c)
        # self.logger.debug(f"the right_camera_rear pandaset extrinsic is:\n{out[self.RIGHT_CAMERA_NAME]}")   
        out[self.LIDAR_NAME] = self.carla_lidar_to_pandaset_lidar_extrinsic(T_rear_lidar_c)
        # self.logger.debug(f"the lidar_rear pandaset extrinsic is:\n{out[self.LIDAR_NAME]}")

        # 同时给出车体中心->后轴 两套坐标系（避免混用）
        out["vehicle_center_to_rear_carla"] = vehicle_center_to_rear_carla
        # self.logger.debug(f"the vehicle_center_to_rear_carla is:\n{out['vehicle_center_to_rear_carla']}")
        out["vehicle_center_to_rear_pandaset"] = self.carla_ego_to_pandaset_ego_extrinsic(vehicle_center_to_rear_carla)
        # self.logger.debug(f"the vehicle_center_to_rear_pandaset is:\n{out['vehicle_center_to_rear_pandaset']}") 

        return out

    def __post_init__(self):
        super().__post_init__()

        # ===== Cameras =====
        self._front_camera = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.name + "_" + self.FRONT_CAMERA_NAME,
            tf=self.FRONT_CAMERA_TF,
            parent=self,
            image_size_x=1920,
            image_size_y=1080,
            fov=70,
        )

        self._front_left_camera = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.name + "_" + self.FRONT_LEFT_CAMERA_NAME,
            tf=self.FRONT_LEFT_CAMERA_TF,
            parent=self,
            image_size_x=1920,
            image_size_y=1080,
            fov=70,
        )

        self._front_right_camera = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.name + "_" + self.FRONT_RIGHT_CAMERA_NAME,
            tf=self.FRONT_RIGHT_CAMERA_TF,
            parent=self,
            image_size_x=1920,
            image_size_y=1080,
            fov=70,
        )

        self._back_camera = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.name + "_" + self.BACK_CAMERA_NAME,
            tf=self.BACK_CAMERA_TF,
            parent=self,
            image_size_x=1920,
            image_size_y=1080,
            fov=70,
        )


        self._left_camera = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.name + "_" + self.LEFT_CAMERA_NAME,
            tf=self.LEFT_CAMERA_TF,
            parent=self,
            image_size_x=1920,
            image_size_y=1080,
            fov=70,
        )


        self._right_camera = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
            name=self.name + "_" + self.RIGHT_CAMERA_NAME,
            tf=self.RIGHT_CAMERA_TF,
            parent=self,
            image_size_x=1920,
            image_size_y=1080,
            fov=70,
        )

        # self._cam_game = self._context.actors.create_sensor(
        #     bp=CarlaBlueprints.SENSOR_CAMERA_RGB,
        #     name=self.name + '_' + self.CAM_GAME_NAME,
        #     tf=self.CAM_GAME_TF,
        #     parent=self,
        # )

        # ===== LiDAR =====
        self._lidar = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_LIDAR_RAY_CAST_SEMANTIC,
            name=self.name + "_" + self.LIDAR_NAME,
            tf=self.LIDAR_TF,
            parent=self,
            rotation_frequency=self._context.fps,
            points_per_second=120_000 * self._context.fps,
            channels=64,
            range=120,
            upper_fov=2,
            lower_fov=-24.5,
        )

    # =========================
    # Properties（兼容常用调用）
    # =========================
    @property
    def front_camera(self) -> CarlaSensor:
        return self._front_camera

    @property
    def front_left_camera(self) -> CarlaSensor:
        return self._front_left_camera

    @property
    def front_right_camera(self) -> CarlaSensor:
        return self._front_right_camera

    @property
    def back_camera(self) -> CarlaSensor:
        return self._back_camera

    @property
    def left_camera(self) -> CarlaSensor:
        return self._left_camera

    @property
    def right_camera(self) -> CarlaSensor:
        return self._right_camera

    @property
    def lidar(self) -> CarlaSensor:
        return self._lidar

    @property
    def main_camera(self) -> CarlaSensor:
        return self._front_camera

    @property
    def main_lidar(self) -> CarlaSensor:
        return self._lidar

    # 兼容旧命名（如果你别处还在用 cam_front 之类）
    @property
    def cam_front(self) -> CarlaSensor:
        return self._front_camera

    @property
    def cam_front_left(self) -> CarlaSensor:
        return self._front_left_camera

    @property
    def cam_front_right(self) -> CarlaSensor:
        return self._front_right_camera

    @property
    def cam_back(self) -> CarlaSensor:
        return self._back_camera
