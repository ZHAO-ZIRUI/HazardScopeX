import time
from logging import Logger
from multiprocessing.shared_memory import SharedMemory
from multiprocessing import resource_tracker

from shared.utils import Logging


class ExternalSharedMemoryManager:
    """
    外部共享内存管理器, 用于在外部程序中使用 SharedMemory 的简化操作
    """

    def __init__(self):
        self._logger = Logging().get_logger('ExtShmManager')
        self._registry: list[SharedMemory] = []

    @property
    def logger(self) -> Logger:
        return self._logger

    def wait_for_shm(self, domain: str, topic: str, timeout: float = 0.0) -> SharedMemory:
        """
        等待共享内存创建, 如果共享内存不存在, 则等待直到共享内存创建或超时
        """
        start_time = time.perf_counter()
        while True:
            try:
                shm = SharedMemory(f'{domain}_{topic}')
                Logging.cancel_interval('wait_for_shm')
                self.logger.info(f'Shared memory "{topic}" found')
                self._registry.append(shm)
                return shm
            except FileNotFoundError:
                msg = f'Waiting for shared memory "{topic}" to be created ...'
                Logging.interval(2, self.logger.info, msg, 'wait_for_shm')
                if timeout == 0.0:
                    continue
                if time.perf_counter() - start_time > timeout:
                    raise TimeoutError(f"Shared memory '{topic}' not found after {timeout} seconds")
                continue

    def close(self, shm: SharedMemory | None = None):
        """
        关闭共享内存, 如果未指定共享内存, 则关闭所有共享内存
        """
        if shm is None:
            for shm in self._registry:
                shm.close()
                # 在 Linux 下防止 resource_tracker 清理共享内存, 客户端侧不关心共享内存的销毁
                # 这里访问了 _name 属性, 由于 SharedMemory 的 _name 和 name 并不一致, 而底层 resource_tracker 需要使用 _name 属性
                resource_tracker.unregister(shm._name, 'shared_memory')  
            self._registry.clear()
        else:
            shm.close()
            resource_tracker.unregister(shm._name, 'shared_memory')  
            self._registry.remove(shm)