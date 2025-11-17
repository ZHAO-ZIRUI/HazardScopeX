import logging
import time
import carla
from typing import Callable, Dict
from rich.logging import RichHandler
from typing_extensions import Self

from shared.utils import Config


class Logging:
    """
    日志记录类（单例模式）
    """
    _instance = None  # 单例模式实例
    _initialized = False  # 标记单例是否已初始化
    _interval_timer_cache: Dict[str, float] = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        level: int = logging.INFO,
    ):
        # 单例模式下，确保只初始化一次
        if not Logging._initialized:
            self.level = level
            self._post_init()
            Logging._initialized = True

    def _post_init(self):
        self._init_basic_config()
        self.get_logger('Logging').info('Initialized')

    def _init_basic_config(self):
        logging.basicConfig(
            level=self.level,
            format="[%(name)s] %(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, show_time=True, markup=True)]
        )

    def get_logger(self, name: str) -> logging.Logger:
        return logging.getLogger(name)

    @classmethod
    def from_config(cls, config: Config) -> Self:
        level: str = config.get("logging/level")
        
        # 将 level 转换为 logging 的级别
        level = getattr(logging, level.upper())

        return cls(
            level=level,
        )

    @staticmethod
    def interval(
        seconds: float,
        log_call: Callable,
        message: str,
        token: str,
    ):
        """每间隔一段时间执行一次日志记录, 用于在某些情况下避免日志记录过于频繁

        该方法可以被频繁调用, 只有在间隔时间到达时才会实际执行一次日志记录

        Args:
            seconds (float): 间隔时间
            log_call (Callable): 日志记录函数, 如 logger.info
            message (str): 日志消息
            token (str): 凭据
        """
        now = time.perf_counter()
        last = Logging._interval_timer_cache.get(token, 0)
        if now - last < seconds:
            return
        Logging._interval_timer_cache[token] = now
        log_call(message)

    @staticmethod
    def cancel_interval(token: str):
        """取消间隔日志记录, 用于在某些情况下停止间隔日志记录

        Args:
            token (str): 凭据
        """
        Logging._interval_timer_cache.pop(token, None)

    @staticmethod
    def short_tf(tf: carla.Transform) -> str:
        """将 carla.Transform 转换为短字符串

        Args:
            tf (carla.Transform): 变换

        Returns:
            str: 日志用短字符串
        """
        return f"TF(X={tf.location.x:.2f}, Y={tf.location.y:.2f}, Z={tf.location.z:.2f}, Yaw={tf.rotation.yaw:.2f}, Pitch={tf.rotation.pitch:.2f}, Roll={tf.rotation.roll:.2f})"