import carla
import numpy as np
import threading
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, List
from typing_extensions import Self, Unpack

from shared.simulator import CarlaActor, CarlaBlueprints, CarlaTickBlocker, CarlaTransform
from shared.data import *

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


class CarlaSensor(CarlaActor):
    """
    carla.Sensor 的外部封装, 用于提供高级功能或适配可重启的服务端
    """

    ID_GENERATOR_HEADER = "Sensor_"

    def __init__(
        self,
        context: 'CarlaContext',
        bp: carla.ActorBlueprint | CarlaBlueprints | str,
        tf: carla.Transform | CarlaTransform,
        *,
        parent: carla.Actor | Self | None = None,
        name: str | None = None,
        ignore_attribute_failure: bool = False,
        ignore_spawn_failure: bool = False,
        is_managed_actor: bool = True,
        image_color_converter: carla.ColorConverter | None = None,  # ONLY FOR CAMERA SENSOR
        **attributes: Unpack[dict[str, Any]],
    ):
        super().__init__(
            context=context,
            bp=bp,
            tf=tf,
            parent=parent,
            name=name,
            ignore_attribute_failure=ignore_attribute_failure,
            ignore_spawn_failure=ignore_spawn_failure,
            is_managed_actor=is_managed_actor,
            **attributes,
        )
        self._data: SimulatorOutput | None = None
        self._is_sensor_data_received = False

        self._img_color_converter = self._resolve_image_color_converter(image_color_converter)  # ONLY FOR CAMERA SENSOR

        # TICK 阻塞器
        if self.id_local == self.name:
            tick_blocker_name = self.id_local
        else:
            tick_blocker_name = f"{self.name}_{self.id_local}"
        self._tick_blocker: CarlaTickBlocker = CarlaTickBlocker(name=tick_blocker_name, auto_set_after_tick=True)

        # 传感器事件钩子
        self._hook_sensor_data_recv: List[Callable[[SimulatorOutput], None]] = []
        self._hook_sensor_data_ready: List[Callable[[SimulatorOutput], None]] = []

    @staticmethod
    def camera_only(func):
        """检查传感器类型是否为相机的装饰器"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self.bp.id.lower().startswith('sensor.camera.'):
                self.logger.critical(f"Program Logic Error: Method '{func.__name__}' only works on camera sensor, but current sensor is '{self.bp.id}'")
                raise SystemExit(319)
            return func(self, *args, **kwargs)
        return wrapper

    @staticmethod
    def lidar_only(func):
        """检查传感器类型是否为激光雷达的装饰器"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self.bp.id.lower().startswith('sensor.lidar.'):
                self.logger.critical(f"Program Logic Error: Method '{func.__name__}' only works on lidar sensor, but current sensor is '{self.bp.id}'")
                raise SystemExit(319)
            return func(self, *args, **kwargs)
        return wrapper

    @property
    def actor(self) -> carla.Sensor:
        """carla.Sensor 实例, 只读"""
        return super().actor

    @property
    def tick_blocker(self) -> threading.Event:
        """TICK 阻塞器"""
        return self._tick_blocker

    @property
    def data(self) -> SimulatorOutput | None:
        """传感器数据, 只读"""
        return self._data

    @property
    def is_camera(self) -> bool:
        """是否为相机传感器"""
        return self.bp.id.lower().startswith('sensor.camera.')

    @property
    def is_lidar(self) -> bool:
        """是否为激光雷达传感器"""
        return self.bp.id.lower().startswith('sensor.lidar.')

    def spawn(self) -> Self:
        """在仿真中生成 Sensor 实例并开始监听"""
        super().spawn()

        # 注册 Tick Blocker
        self._context.tick_blockers.append(self._tick_blocker)

        # 开始监听
        self.start_listen()
        return self

    def destroy(self) -> Self:
        """销毁 Sensor 实例"""
        # 移除 Tick Blocker
        self._context.tick_blockers.remove(self._tick_blocker)
        
        # 清理钩子
        self._hook_sensor_data_recv.clear()
        self._hook_sensor_data_ready.clear()

        # 停止监听
        if self.is_alive:
            try:
                self.actor.stop()
            except RuntimeError as e:
                self.logger.warning(f"Failed to stop sensor before destroy: {e}")

        # 销毁 Actor
        return super().destroy()

    def start_listen(self) -> Self:
        """开始监听传感器数据"""
        if not self.is_alive:
            msg = f"Cannot start listening for sensor '{self.name}' because it is not alive"
            self.logger.error(msg)
            raise RuntimeError(msg)
        
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
        image_width = self.bp.get_attribute('image_size_x').as_int()
        image_height = self.bp.get_attribute('image_size_y').as_int()
        fov = self.bp.get_attribute('fov').as_float()
        
        # 计算焦距: focal = width / (2 * tan(fov / 2))
        focal_length = image_width / (2.0 * np.tan(fov * np.pi / 360.0))
        
        # 构建内参矩阵
        K = np.identity(3, dtype=np.float64)
        K[0, 0] = K[1, 1] = focal_length
        K[0, 2] = image_width / 2.0
        K[1, 2] = image_height / 2.0
        
        return K

    def _listen_callback(self, data: carla.SensorData):
        # 设置 TICK 阻塞器
        self.tick_blocker.set()

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
        
        # 清除 TICK 阻塞器
        self.tick_blocker.clear()

    def _reformat_sensor_data(self, data: carla.SensorData) -> SimulatorOutput:
        """将 carla.SensorData 转换为 SimulatorOutput 格式的数据

        Args:
            data (carla.SensorData): CARLA 传感器数据

        Returns:
            SimulatorOutput: 框架中的统一仿真器输出数据
        """
        if isinstance(data, carla.Image):
            data.convert(self._img_color_converter)
            return Image.from_carla(data)
        if isinstance(data, carla.LidarMeasurement | carla.SemanticLidarMeasurement):
            return PointCloud.from_carla(data)
        if isinstance(data, carla.CollisionEvent):
            return Collision.from_carla(data)
        raise ValueError(f"Unsupported sensor data type: {type(data)}")
    
    def _resolve_image_color_converter(self, value: carla.ColorConverter | None) -> carla.ColorConverter:
        """根据传感器类型解析图像颜色转换器"""
        if value is not None:
            return value

        mapping = {
            'Raw': carla.ColorConverter.Raw,
            'LogarithmicDepth': carla.ColorConverter.LogarithmicDepth,
            'Depth': carla.ColorConverter.Depth,
            'CityScapesPalette': carla.ColorConverter.CityScapesPalette,
        }
        
        # 默认情况
        if self.bp.id.lower().endswith('rgb'):
            return carla.ColorConverter.Raw
        elif self.bp.id.lower().endswith('depth'):
            return mapping[self._context.configs.actor_manager.image_cc_depth]
        elif self.bp.id.lower().endswith('instance_segmentation'):
            return mapping[self._context.configs.actor_manager.image_cc_instance_segmentation]
        elif self.bp.id.lower().endswith('semantic_segmentation'):
            return mapping[self._context.configs.actor_manager.image_cc_semantic_segmentation]
        else:
            raise ValueError(f"Unsupported sensor type: {self.bp.id}")

    @property
    def hook_sensor_data_recv(self) -> List[Callable[[SimulatorOutput], None]]:
        return self._hook_sensor_data_recv

    @property
    def hook_sensor_data_ready(self) -> List[Callable[[SimulatorOutput], None]]:
        return self._hook_sensor_data_ready