import carla
from typing import Callable, List
from typing_extensions import Self

from shared.simulator import CarlaActor
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

        # 传感器事件钩子
        self._hook_sensor_data_recv: List[Callable[[SimulatorOutput], None]] = []
        self._hook_sensor_data_ready: List[Callable[[SimulatorOutput], None]] = []

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
            if self.bp.id == CarlaBlueprints.SENSOR_CAMERA_INSTANCE_SEGMENTATION.value or self.bp.id == CarlaBlueprints.SENSOR_CAMERA_SEMANTIC_SEGMENTATION.value:
                data.convert(carla.ColorConverter.CityScapesPalette)
            elif self.bp.id == CarlaBlueprints.SENSOR_CAMERA_DEPTH.value:
                data.convert(carla.ColorConverter.Depth)
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