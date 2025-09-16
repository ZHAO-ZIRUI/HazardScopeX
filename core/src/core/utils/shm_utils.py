from multiprocessing.shared_memory import SharedMemory
from multiprocessing import resource_tracker


class SharedMemoryUtils:
    """
    SharedMemory 的操作工具, 主要用于处理在 Linux 环境下生产者和消费者之间的不同行为
    """
    
    @staticmethod
    def consumer_close(*shms: SharedMemory):
        for shm in shms:
            resource_tracker.unregister(shm._name, 'shared_memory')  # ONLY for Linux
            shm.close()

    @staticmethod
    def producer_close(*shms: SharedMemory):
        for shm in shms:
            shm.close()
            shm.unlink()
