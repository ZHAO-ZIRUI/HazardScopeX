import logging
from rich.logging import RichHandler
from typing_extensions import Self

from shared.utils import Config


class Logging:
    """
    日志记录类（单例模式）
    """
    _instance = None  # 单例模式实例
    _initialized = False  # 标记单例是否已初始化

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
        self.get_logger('Logging').info('Logging initialized')

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