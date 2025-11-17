import threading
from typing import Dict


class IdGenerator:
    """
    多例模式且线程安全的递增数标签生成器
    每个不同的 header 对应一个独立的实例和计数器
    """

    DEFAULT_HEADER = ''
    DEFAULT_LENGTH = 3

    _instances: Dict[str, 'IdGenerator'] = {}  # 多例模式实例字典
    _instances_lock = threading.Lock()  # 保护实例字典的锁
    
    def __new__(cls, *args, **kwargs):
        # 从 kwargs 中获取 header，如果没有则使用默认值
        header = kwargs.get('header', cls.DEFAULT_HEADER)
        
        # 使用双重检查锁定确保线程安全
        if header not in cls._instances:
            with cls._instances_lock:
                if header not in cls._instances:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instances[header] = instance
        
        return cls._instances[header]
    
    def __init__(
            self,
            *,
            header: str = None,
            length: int = None,
    ) -> None:
        """
        :param header: 标签前缀，相同的 header 会返回同一个实例
        :param length: 向左补 0 后的总长度
        :raises AttributeError: 在非首次初始化时设置 length
        """
        # 多例模式下，每个 header 对应的实例只初始化一次
        if not self._initialized:
            self._counter = 0
            self._counter_lock = threading.Lock()
            # header 和 length 的设置只在第一次实例化时生效
            self._header = header if header is not None else IdGenerator.DEFAULT_HEADER
            self._length = length if length is not None else IdGenerator.DEFAULT_LENGTH
            self._initialized = True
        else:
            if length is not None:
                raise AttributeError("Length can only be set on the first initialization.")
    
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