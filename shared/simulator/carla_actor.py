import carla
from logging import Logger
from typing import TYPE_CHECKING, Any
from typing_extensions import Self, Unpack

from shared.simulator import CarlaBlueprints, CarlaTransform
from shared.utils import IdGenerator, Logging, PostInitMeta

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


class CarlaActor(metaclass=PostInitMeta):
    """
    carla.Actor 实例的容器, 用于在 CarlaContext 中管理 Actor 的生命周期和行为
    """

    ID_GENERATOR_HEADER = "Actor_"

    def __init__(
        self,
        context: 'CarlaContext',
        bp: carla.ActorBlueprint | CarlaBlueprints | str,
        tf: carla.Transform | CarlaTransform,
        *,
        parent: Self | None = None,
        name: str | None = None,
        ignore_attribute_failure: bool = False,
        ignore_spawn_failure: bool = False,
        is_managed_actor: bool = True,
        **attributes: Unpack[dict[str, Any]],
    ):
        """创建 CarlaActor 实例

        Args:
            context (CarlaContext): CarlaContext 实例
            bp (carla.ActorBlueprint | CarlaBlueprints | str): 蓝图
            tf (carla.Transform | CarlaTransform): 初始变换
            parent (CarlaActor | None): 父级对象
            name (str | None): 别名
            ignore_attribute_failure (bool): 是否忽略属性失败
            ignore_spawn_failure (bool): 是否忽略生成失败
            is_managed_actor (bool): 是否被管理
        """
        self._id_local = next(IdGenerator(header=self.ID_GENERATOR_HEADER))
        self._context = context
        self._name = self._resolve_name(name)
        self._logger = Logging().get_logger(self._name)

        self._is_managed_actor = is_managed_actor
        self._flag_ignore_attribute_failure = ignore_attribute_failure
        self._flag_ignore_spawn_failure = ignore_spawn_failure
        self._parent = parent
        self._cache_attributes: dict[str, str] = {}

        self._bp = self._resolve_blueprint(bp)
        self._bp = self._resolve_attributes(**attributes)
        self._tf = self._resolve_transform(tf)

        self._actor_ref: list[carla.Actor | None] = [None]  # 长度为 1 的列表, 用于存储 carla.Actor 实例的引用

    def __post_init__(self):
        # 注册到 ActorManager
        self._context.actors.add(self)

    def __str__(self) -> str:
        return f"CarlaActor(name='{self.name}', id_local='{self.id_local}', is_alive='{self.is_alive}', is_managed='{self.is_managed_actor}')"

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def name(self) -> str:
        """别名, 只读"""
        return self._name

    @property
    def logger(self) -> Logger:
        """日志记录器, 只读"""
        return self._logger

    @property
    def bp(self) -> carla.ActorBlueprint:
        """蓝图, 只读"""
        return self._bp

    @property
    def id_local(self) -> str:
        """本地唯一 ID, 只读"""
        return self._id_local

    @property
    def id_carla(self) -> int:
        """CARLA ID, 只读"""
        return self.actor.id if self.is_alive else -1

    @property
    def tf_now(self) -> carla.Transform:
        """当前变换, 只读"""
        if not self.is_alive:
            msg = f"Tried to get transform of actor '{self.name}' but it is not alive"
            self.logger.error(msg)
            raise RuntimeError(msg)
        return self.actor.get_transform()

    @property
    def tf_init(self) -> carla.Transform | None:
        """初始变换, 只读"""
        return self._tf

    @property
    def actor(self) -> carla.Actor:
        """carla.Actor 实例, 只读"""
        if not self.is_alive:
            msg = f"Tried to get actor instance of actor '{self.name}' but it is not alive."
            self.logger.error(msg)
            raise RuntimeError(msg)
        assert self._actor_ref[0] is not None
        return self._actor_ref[0]

    @property
    def parent(self) -> Self | None:
        """父级 Actor 实例, 只读"""
        return self._parent

    @property
    def is_alive(self) -> bool:
        """Actor 是否存活"""
        return self._actor_ref[0] is not None and self._actor_ref[0].is_alive

    @property
    def is_managed_actor(self) -> bool:
        """Actor 是否被 CarlaContext 管理"""
        return self._is_managed_actor

    @is_managed_actor.setter
    def is_managed_actor(self, value: bool):
        self._is_managed_actor = value
        if value:
            self.logger.info(f"Actor '{self.name}' is now managed by CarlaContext")
        else:
            self.logger.warning(f"Actor '{self.name}' is no longer managed by CarlaContext")

    def spawn(self) -> Self:
        """在仿真中生成 Actor 实例"""
        # 获取父级 Actor 实例
        if self.parent is not None:
            if not self.parent.is_alive:
                raise ValueError(f"Parent actor: '{self.parent}' not spawned yet or not alive")
            attach_to = self.parent.actor
        else:
            attach_to = None

        # 尝试生成 Actor
        try:
            self.logger.debug(f"Spawning actor '{self.name}' with blueprint '{self._bp.id}' at {Logging.short_tf(self.tf_init)}")
            actor = self._context.world.spawn_actor(self._bp, self._tf, attach_to=attach_to)

            # 强制 Tick 一次, 让 Actor 实例有机会生成
            self._context.tick(force=True)

            # 更新 Actor 实例引用
            self._actor_ref[0] = actor
            self.logger.info(f"Actor is spawned and available now with id: {self.id_local}, carla id: {self.id_carla}")
        except RuntimeError as e:
            if self._flag_ignore_spawn_failure:
                self.logger.warning(f"Failed to spawn actor but ignored: {e}")
                return self
            else:
                self.logger.error(f"Failed to spawn actor: {e}")
                raise e

        return self

    def destroy(self) -> Self:
        """销毁 Actor 实例"""
        if self._actor_ref[0] is None:
            return self
        cache_carla_id = self.id_carla
        result = self._actor_ref[0].destroy()
        self._actor_ref[0] = None
        if result:
            self.logger.info(f"Destroyed actor (CARLA ID: {cache_carla_id})")
        else:
            self.logger.warning(f"Failed to destroy actor (CARLA ID: {cache_carla_id}), but ignored")
        return self

    def serialize(self) -> str:
        """序列化为 YAML 字符串“”“

        Returns:
            str: YAML 字符串
        """
        dump_data = {
            '_id_local': self._id_local,
            '_name': self._name,
            '_bp': self._bp.id,
            '_tf_init': CarlaTransform.from_carla(self.tf_init).serialize(),
            '_parent_name': self._parent.name if self._parent is not None else None,
            '_attributes': self._cache_attributes,
        }
        return dump_data

    def _resolve_blueprint(self, bp: carla.ActorBlueprint | CarlaBlueprints | str) -> carla.ActorBlueprint:
        """将多种可能的蓝图输入统一为 carla.ActorBlueprint

        Args:
            bp (carla.ActorBlueprint | CarlaBlueprints | str): 蓝图输入

        Returns:
            carla.ActorBlueprint: 确定的 carla.ActorBlueprint 对象
        """
        if isinstance(bp, carla.ActorBlueprint):
            return bp
        if isinstance(bp, CarlaBlueprints):
            bp = bp.value
        if isinstance(bp, str):
            blueprint_library = self._context.world.get_blueprint_library()
            try:
                return blueprint_library.find(bp)
            except IndexError as e:
                raise ValueError(f"Blueprint '{bp}' not found in blueprint library") from e
        else:
            raise ValueError(f"Invalid blueprint input: {bp}")

    def _resolve_transform(self, tf: carla.Transform | CarlaTransform) -> carla.Transform:
        """将多种可能的变换输入统一为 carla.Transform

        Args:
            tf (carla.Transform | CarlaTransform): 变换输入

        Returns:
            carla.Transform: 确定的 carla.Transform 对象
        """
        if isinstance(tf, carla.Transform):
            return tf
        elif isinstance(tf, CarlaTransform):
            return tf.to_carla()
        else:
            raise ValueError(f"Invalid transform input: {tf}")

    def _resolve_name(self, name: str | None) -> str:
        """确定最终的别名

        Args:
            name (str | None): 名称输入

        Returns:
            str: 确定的名称
        """
        if name is None:
            return self._id_local
        else:
            return name

    def _resolve_attributes(self, **attributes: Unpack[dict[str, Any]]) -> carla.ActorBlueprint:
        """将属性写入到 carla.ActorBlueprint 中

        Args:
            attributes (Unpack[dict[str, Any]]): 属性输入

        Returns:
            carla.ActorBlueprint: 确定的 carla.ActorBlueprint 对象
        """
        for key, value in attributes.items():
            try:
                self._bp.set_attribute(key, str(value))
                self.logger.debug(f"Attribute '{key}' set to '{str(value)}'")
                self._cache_attributes[key] = str(value)
            except IndexError as e:
                msg = f"Attribute '{key}' not found in blueprint '{self._bp.id}'"
                if not self._flag_ignore_attribute_failure:
                    self.logger.error(msg)
                    raise e
                else:
                    self.logger.warning(msg + ', but ignored')

        # 处理默认别名
        if self._bp.has_attribute('role_name'):
            self._bp.set_attribute('role_name', self._name)
            self.logger.debug(f"Attribute 'role_name' set to '{self._name}'")
            self._cache_attributes['role_name'] = self._name
        return self._bp

    @classmethod
    def from_carla(cls, context: 'CarlaContext', actor: carla.Actor) -> Self:
        """从 carla.Actor 实例创建 CarlaActor 实例"""
        instance = cls(
            context=context,
            bp=actor.type_id,
            tf=actor.get_transform(),
            parent=None,
            name=actor.attributes.get('role_name', None),
            ignore_attribute_failure=False,
            ignore_spawn_failure=False,
            is_managed_actor=False,
        )
        instance._actor_ref[0] = actor
        return instance