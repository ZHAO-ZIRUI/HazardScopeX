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
        self._registry: set[SharedMemory] = set()

    @property
    def logger(self) -> Logger:
        return self._logger

    def wait_for_shm(self, domain: str, topic: str, timeout: float = 0.0) -> SharedMemory:
        """
        等待共享内存创建, 如果共享内存不存在, 则等待直到共享内存创建或超时
        """
        full_topic = f'{domain}_{topic}'
        start_time = time.perf_counter()
        while True:
            try:
                shm = SharedMemory(full_topic)
                Logging.cancel_interval('wait_for_shm')
                self.logger.info(f'Shared memory "{full_topic}" found')
                self._registry.add(shm)
                return shm
            except FileNotFoundError:
                msg = f'Waiting for shared memory "{full_topic}" to be created ...'
                Logging.interval(2, self.logger.info, msg, 'wait_for_shm')
                if timeout == 0.0:
                    continue
                if time.perf_counter() - start_time > timeout:
                    raise TimeoutError(f"Shared memory '{full_topic}' not found after {timeout} seconds")
                continue

    def try_get_shm(self, domain: str, topic: str) -> SharedMemory | None:
        """
        尝试获取共享内存, 如果共享内存不存在, 则返回 None
        """
        try:
            full_topic = f'{domain}_{topic}'
            shm = SharedMemory(full_topic)
            self._registry.add(shm)
            return shm
        except FileNotFoundError:
            return None

    def is_shm_exists(self, domain: str, topic: str) -> bool:
        """
        检查共享内存是否存在
        """
        full_topic = f'{domain}_{topic}'
        try:
            SharedMemory(full_topic)
            return True
        except FileNotFoundError:
            return False

    def close(self, shm: SharedMemory | None = None):
        """
        关闭共享内存, 如果未指定共享内存, 则关闭所有共享内存
        """
        if shm is None:
            for shm in list(self._registry):
                self._close(shm)
            self._registry.clear()
        else:
            self._close(shm)

    def _close(self, shm: SharedMemory):
        shm.close()
        try:
            resource_tracker.unregister(shm._name, 'shared_memory')  
        except KeyError:
            # 如果共享内存已经被其他进程关闭, 则忽略
            pass
        self._registry.remove(shm)