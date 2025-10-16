import carla
import logging
from functools import wraps
from typing_extensions import Self

from shared.utils import IdGenerator, Logging

class CarlaActor:
    """
    carla.Actor 的外部封装, 用于提供高级功能或适配可重启的服务端
    """

    ID_GENERATOR_HEADER = "ACTOR_"

    @staticmethod
    def require_actor_alive(func):
        """强制要求 Actor 是否可用的装饰器"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self._actor is None:
                raise RuntimeError(f'Actor "{self.name}" not spawned yet. Call context.factory.spawn() first.')
            if not self._actor.is_alive:
                raise RuntimeError(f'Actor "{self.name}" is not alive anymore.')
            return func(self, *args, **kwargs)
        return wrapper

    @staticmethod
    def warn_actor_not_alive(func):
        """警告 Actor 不可用的装饰器"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self._actor is None:
                self.logger.warning(f'Actor "{self.name}" not spawned yet. Call context.factory.spawn() first.')
            if not self._actor.is_alive:
                self.logger.warning(f'Actor "{self.name}" is not alive anymore.')
            return func(self, *args, **kwargs)
        return wrapper
    
    def __init__(
        self, 
        bp: carla.ActorBlueprint,
        actor: carla.Actor | None = None,
    ):
        # 生成本地 ID
        self._id_generator = IdGenerator(header=self.ID_GENERATOR_HEADER)
        self._id_local = next(self._id_generator)

        # 日志记录器
        self._logger = Logging().get_logger(self._id_local)

        # 初始值
        self._bp = bp
        self._tf_init: carla.Transform | None = None
        self._attach_target: Self | None = None

        # carla.Actor 实例
        self._actor = actor

        self.logger.info(f"Created with blueprint '{self._bp.id}'")
        
    @property
    def bp(self) -> carla.ActorBlueprint:
        """蓝图, 包含创建 Actor 所需的属性信息"""
        return self._bp

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def id_local(self) -> str:
        """本地容器的 ID, 用于在注册表中唯一标识"""
        return self._id_local

    @property
    def tf_init(self) -> carla.Transform | None:
        """初始变换"""
        return self._tf_init

    @tf_init.setter
    def tf_init(self, value: carla.Transform):
        if self._tf_init is not None:
            self.logger.warning(f"Initial transform already set to {Logging.short_tf(self._tf_init)}. Overwriting with {Logging.short_tf(value)}")
        if self._actor is not None:
            self.logger.warning(f"Actor already spawned. Setting initial transform will have no effect.")
            return
        self.logger.info(f"Setting initial transform to {Logging.short_tf(value)}")
        self._tf_init = value
        return

    @property
    def attach_target(self) -> Self | None:
        """附着到的目标 Actor"""
        return self._attach_target

    @attach_target.setter
    def attach_target(self, value: Self | None):
        if self._attach_target is not None:
            self.logger.warning(f"Attach target already set to {self._attach_target.name}. Overwriting with {value.name}")
        if self._actor is not None:
            self.logger.warning(f"Actor already spawned. Setting attach target will have no effect.")
            return
        if value is None:
            return
        self.logger.info(f"Setting attach target to {value.id_local}")
        self._attach_target = value
        return