import carla
import numpy as np
from functools import wraps
from typing import Callable, List
from typing_extensions import Self

from shared.simulator import CarlaActor, CarlaBlueprints
from shared.data import *


class CarlaSensor(CarlaActor):
    """
    carla.Sensor 的外部封装, 用于提供高级功能或适配可重启的服务端
    """

    ID_GENERATOR_HEADER = "SENSOR_"

    def __init__(
        self,
        bp: carla.ActorBlueprint,
        name: str = '',
        actor: carla.Actor | None = None,
    ):
        super().__init__(bp=bp, name=name, actor=actor)
        self._data: SimulatorOutput | None = None
        self._is_sensor_data_received = False

        self.img_color_converter = carla.ColorConverter.Raw    # ONLY FOR CAMERA SENSOR

        # 传感器事件钩子
        self._hook_sensor_data_recv: List[Callable[[SimulatorOutput], None]] = []
        self._hook_sensor_data_ready: List[Callable[[SimulatorOutput], None]] = []

    @staticmethod
    def camera_only(func):
        """检查传感器类型是否为相机的装饰器"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self._bp.id.lower().startswith('sensor.camera.'):
                self.logger.critical(f"Program Logic Error: Method '{func.__name__}' only works on camera sensor, but current sensor is '{self._bp.id}'")
                raise SystemExit(319)
            return func(self, *args, **kwargs)
        return wrapper

    @staticmethod
    def lidar_only(func):
        """检查传感器类型是否为激光雷达的装饰器"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self._bp.id.lower().startswith('sensor.lidar.'):
                self.logger.critical(f"Program Logic Error: Method '{func.__name__}' only works on lidar sensor, but current sensor is '{self._bp.id}'")
                raise SystemExit(319)
            return func(self, *args, **kwargs)
        return wrapper

    @property
    def actor(self) -> carla.Sensor:
        return super().actor

    @actor.setter
    def actor(self, value: carla.Sensor):
        CarlaActor.actor.fset(self, value)

    @property
    def data(self) -> SimulatorOutput | None:
        return self._data

    def spawn(self, world: carla.World, ignore_spawn_failure: bool = False) -> Self:
        super().spawn(world, ignore_spawn_failure)
        self.start_listen()
        return self

    def destroy(self) -> Self:
        # 清理钩子
        self._hook_sensor_data_recv.clear()
        self._hook_sensor_data_ready.clear()

        # 停止监听
        if self.actor is not None and self.actor.is_alive:
            self.actor.stop()

        # 销毁 Actor
        super().destroy()
        return self

    def start_listen(self) -> Self:
        self.actor.listen(lambda data: self._listen_callback(data))
        return self

    @camera_only
    def get_camera_intrinsics_matrix(self) -> np.ndarray:
        """获取相机内参矩阵

        从蓝图属性中读取图像尺寸和视场角(FOV), 计算并返回3x3的相机内参矩阵K。
        内参矩阵格式为:
            K = [[fx,  0, cx],
                 [ 0, fy, cy],
                 [ 0,  0,  1]]
        其中:
            - fx = fy = focal_length (焦距, 像素单位)
            - cx = image_width / 2.0 (主点x坐标)
            - cy = image_height / 2.0 (主点y坐标)

        Returns:
            np.ndarray: 3x3的相机内参矩阵, shape 为 (3, 3), dtype 为 float64
        """
        # 从蓝图属性获取相机参数
        image_width = self._bp.get_attribute('image_size_x').as_int()
        image_height = self._bp.get_attribute('image_size_y').as_int()
        fov = self._bp.get_attribute('fov').as_float()
        
        # 计算焦距: focal = width / (2 * tan(fov / 2))
        focal_length = image_width / (2.0 * np.tan(fov * np.pi / 360.0))
        
        # 构建内参矩阵
        K = np.identity(3, dtype=np.float64)
        K[0, 0] = K[1, 1] = focal_length
        K[0, 2] = image_width / 2.0
        K[1, 2] = image_height / 2.0
        
        return K

    def _listen_callback(self, data: carla.SensorData):
        self._data = self._reformat_sensor_data(data)

        # 当第一次获取数据时打印一个日志
        if not self._is_sensor_data_received:
            self.logger.info(f"Sensor data received: type={type(data)}, reformatted={type(self._data)}")
            self._is_sensor_data_received = True

        # 执行数据接收后的钩子, 用于传感器后处理或注入
        for hook in self._hook_sensor_data_recv:
            hook_return = hook(self._data)
            if hook_return is not None:
                self._data = hook_return

        # 执行数据准备后的钩子, 用于传感器的数据发送或转储
        for hook in self._hook_sensor_data_ready:
            hook_return = hook(self._data)
            if hook_return is not None:
                self._data = hook_return


    def _reformat_sensor_data(self, data: carla.SensorData) -> SimulatorOutput:
        """将 carla.SensorData 转换为 SimulatorOutput 格式的数据

        Args:
            data (carla.SensorData): CARLA 传感器数据

        Returns:
            SimulatorOutput: 框架中的统一仿真器输出数据
        """
        if isinstance(data, carla.Image):
            data.convert(self.img_color_converter)
            return Image.from_carla(data)
        if isinstance(data, carla.LidarMeasurement | carla.SemanticLidarMeasurement):
            return PointCloud.from_carla(data)
        if isinstance(data, carla.CollisionEvent):
            return Collision.from_carla(data)
        raise ValueError(f"Unsupported sensor data type: {type(data)}")
    
    @property
    def hook_sensor_data_recv(self) -> List[Callable[[SimulatorOutput], None]]:
        return self._hook_sensor_data_recv

    @property
    def hook_sensor_data_ready(self) -> List[Callable[[SimulatorOutput], None]]:
        return self._hook_sensor_data_ready