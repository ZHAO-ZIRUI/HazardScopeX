from multiprocessing.shared_memory import SharedMemory
from typing_extensions import Self

from shared.simulator import CarlaSensor
from shared.io import IOAdapter


class SharedMemoryAdapter(IOAdapter):
    """
    共享内存适配器, 用于将仿真器的数据转换为共享内存数据
    """

    def __init__(self, shm: SharedMemory):
        super().__init__()
        self.shm = shm

    def bind_sensor_output(self, sensor: CarlaSensor) -> Self:
        sensor.hook_sensor_data_ready.append(
            lambda data: data.to_shm(self.shm)
        )
        return self