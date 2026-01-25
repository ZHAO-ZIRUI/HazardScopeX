from multiprocessing.shared_memory import SharedMemory
from typing_extensions import Self
from typing import TYPE_CHECKING

from shared.io import AbstractIOAdapter

if TYPE_CHECKING:
    from shared.simulator import CarlaSensor
    from shared.simulator import CarlaContext


class SharedMemoryAdapter(AbstractIOAdapter):
    """
    共享内存适配器, 用于将仿真器的数据转换为共享内存数据
    """

    def __init__(self, context: 'CarlaContext', shm: SharedMemory, topic: str):
        super().__init__(context)
        self._shared_memory_instance = shm
        self._topic = topic

    @property
    def shared_memory_instance(self) -> SharedMemory:
        """共享内存实例"""
        return self._shared_memory_instance
    
    @property
    def topic(self) -> str:
        """共享内存的名称, 与对象创建时的 topic 参数一致"""
        return self._topic

    def bind_sensor(self, sensor: 'CarlaSensor') -> Self:
        sensor.hook_sensor_data_ready.append(
            lambda data: data.to_shm(self.shared_memory_instance)
        )
        return self

    def bind_clock(self) -> Self:
        self._context.hook_on_tick.append(
            lambda snapshot: self._context.clock.to_shm(self.shared_memory_instance)
        )
        return self