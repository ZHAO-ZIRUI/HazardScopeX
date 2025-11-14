import carla
import logging
import threading
from functools import wraps
from typing import Any
from typing_extensions import Self

from shared.simulator import CarlaTransform
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
                raise RuntimeError(f'Actor not spawned yet. Call context.actors.spawn() first.')
            if not self._actor.is_alive:
                raise RuntimeError(f'Actor is not alive anymore.')
            return func(self, *args, **kwargs)
        return wrapper

    @staticmethod
    def warn_actor_not_alive(func):
        """警告 Actor 不可用的装饰器"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self._actor is None:
                self.logger.warning(f'Actor not spawned yet. Call context.actors.spawn() first.')
            if not self._actor.is_alive:
                self.logger.warning(f'Actor is not alive anymore.')
            return func(self, *args, **kwargs)
        return wrapper
    
    def __init__(
        self, 
        bp: carla.ActorBlueprint,
        name: str = '',
        actor: carla.Actor | None = None,
    ):
        # 生成本地 ID
        self._id_generator = IdGenerator(header=self.ID_GENERATOR_HEADER)
        self._id_local = next(self._id_generator)

        # 别名
        self._name = name

        # 日志记录器
        self._logger = Logging().get_logger(self.name)

        # 初始值
        self._bp = bp
        self._tf_init: carla.Transform | None = None
        self._parent: Self | None = None

        # carla.Actor 实例
        self._actor = actor

        # TICK 阻塞器
        self._tick_blocker: threading.Event = threading.Event()

        self.logger.info(f"Created with blueprint '{self._bp.id}'")

    def serialize(self) -> str:
        """序列化为 YAML 字符串“”“

        Returns:
            str: YAML 字符串
        """
        dump_data = {
            '_id_local': self._id_local,
            '_name': self._name,
            '_bp': self._bp.id,
            '_tf_init': CarlaTransform.from_carla(self._tf_init).serialize(),
            '_parent_name': self._parent.name if self._parent is not None else None,
            '_attributes': self._actor.attributes,
        }
        return dump_data

    @property
    def bp(self) -> carla.ActorBlueprint:
        """蓝图, 包含创建 Actor 所需的属性信息"""
        return self._bp

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def name(self) -> str:
        if self._name == '':
            return self._id_local
        else:
            return self._name

    @property
    def id_local(self) -> str:
        """本地容器的 ID, 用于在注册表中唯一标识"""
        return self._id_local

    @property
    def tf_init(self) -> carla.Transform | None:
        """初始变换"""
        return self._tf_init

    @property
    def tick_blocker(self) -> threading.Event:
        """TICK 阻塞器"""
        return self._tick_blocker

    @property
    @require_actor_alive
    def tf_now(self) -> carla.Transform:
        """当前变换"""
        return self._actor.get_transform()

    @tf_init.setter
    def tf_init(self, value: carla.Transform):
        if self._tf_init is not None:
            self.logger.warning(f"Initial transform already set to {Logging.short_tf(self._tf_init)}. Overwriting with {Logging.short_tf(value)}")
        if self._actor is not None:
            self.logger.warning(f"Actor already spawned. Setting initial transform will have no effect.")
            return
        self.logger.debug(f"Setting initial transform to {Logging.short_tf(value)}")
        self._tf_init = value
        return

    @property
    def parent(self) -> Self | None:
        """父 Actor"""
        return self._parent

    @parent.setter
    def parent(self, value: Self | None):
        if self._parent is not None:
            self.logger.warning(f"Parent already set to {self._parent.name}. Overwriting with {value.name}")
        if self._actor is not None:
            self.logger.warning(f"Actor already spawned. Setting parent will have no effect.")
            return
        if value is None:
            return
        self.logger.info(f"Setting parent to {value.id_local}")
        self._parent = value
        return

    @property
    @require_actor_alive
    def actor(self) -> carla.Actor:
        """carla.Actor 实例"""
        return self._actor

    @actor.setter
    def actor(self, value: carla.Actor):
        if self._actor is not None:
            self.logger.warning(f"Actor already set. Overwriting with {value.id}")
            return
        self.logger.debug(f"Bind actor instance (CARLA ID: {value.id})")
        self._actor = value
        return

    def spawn(self, world: carla.World, ignore_spawn_failure: bool = False) -> Self:
        """在仿真中生成 Actor 实例

        Args:
            world (carla.World): 仿真世界
            ignore_spawn_failure (bool): 是否忽略生成失败, 如果为 True, 则不会抛出异常

        Raises:
            RuntimeError: 生成失败, 且 ignore_spawn_failure 为 False

        Returns:
            Self: 链式调用支持
        """
        try:
            self.actor = world.spawn_actor(self._bp, self._tf_init, attach_to=self._parent.actor if self._parent is not None else None)
            self.logger.info(f"Spawned actor (CARLA ID: {self.actor.id})")
        except RuntimeError as e:
            if ignore_spawn_failure:
                self.logger.warning(f"Failed to spawn actor but ignored: {e}")
                return self
            else:
                self.logger.error(f"Failed to spawn actor: {e}")
                raise e
        return self

    @warn_actor_not_alive
    def destroy(self) -> Self:
        """销毁 Actor 实例"""
        if self._actor is None:
            return self
        
        try:
            actor_id = self._actor.id   # 暂存 CARLA ID, 防止销毁后无法获取
            self._actor.destroy()
            self._actor = None
            self.logger.info(f"Destroyed actor (CARLA ID: {actor_id})")
        except RuntimeError as e:
            self.logger.error(f"Failed to destroy actor: {e}")
        return self
