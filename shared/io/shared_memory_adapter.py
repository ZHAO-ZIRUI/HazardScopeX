from multiprocessing.shared_memory import SharedMemory
from typing_extensions import Self

from shared.simulator import CarlaSensor
from shared.io import AbstractIOAdapter


class SharedMemoryAdapter(AbstractIOAdapter):
    """
    共享内存适配器, 用于将仿真器的数据转换为共享内存数据
    """

    def __init__(self, shm: SharedMemory, topic: str, managed:bool = True):
        super().__init__()
        self._shared_memory_instance = shm
        self._topic = topic
        self._managed = managed

    @property
    def shared_memory_instance(self) -> SharedMemory:
        """共享内存实例"""
        return self._shared_memory_instance
    
    @property
    def topic(self) -> str:
        """共享内存的名称, 与对象创建时的 topic 参数一致"""
        return self._topic
    
    @property
    def managed(self) -> bool:
        """是否由 IOManager 创建"""
        return self._managed

    def bind_sensor_output(self, sensor: CarlaSensor) -> Self:
        sensor.hook_sensor_data_ready.append(
            lambda data: data.to_shm(self.shared_memory_instance)
        )
        return self