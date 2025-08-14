import threading
from typing import Optional


class UniqueTagProvider:
    """
    全局单例且线程安全的递增数标签生成器
    """
    
    _instance: Optional['UniqueTagProvider'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'UniqueTagProvider':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
            self,
            *,
            header: str = None,
            length: int = 2,
    ) -> None:
        """
        :param header: 标签前缀
        :param length: 向左补 0 后的总长度
        """
        if not hasattr(self, '_initialized'):
            self._counter = 0
            self._counter_lock = threading.Lock()
            self._initialized = True
            self._header = header
            self._length = length
    
    def __iter__(self):
        return self
    
    def __next__(self) -> str:
        with self._counter_lock:
            self._counter += 1
            result = self._header if self._header else ''
            result += str(self._counter).zfill(self._length)
            return result
    
    def next(self) -> str:
        """
        以显示调用的方式获得下一个标签
        :return: 标签字符串
        """
        return self.__next__()
