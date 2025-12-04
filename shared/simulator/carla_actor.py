import carla
from logging import Logger
from typing import TYPE_CHECKING, Any
from typing_extensions import Self, Unpack

from shared.simulator import CarlaBlueprints, CarlaTransform
from shared.utils import IdGenerator, Logging

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


class CarlaActor():
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
        parent: carla.Actor | Self | None = None,
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
            parent (carla.Actor | 'CarlaActor' | int | None): 父级对象
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

        self._bp = self._resolve_blueprint(bp)
        self._bp = self._resolve_attributes(**attributes)
        self._tf = self._resolve_transform(tf)
        self._parent_ref = self._resolve_parent(parent)

        self._actor_ref: list[carla.Actor | None] = [None]  # 长度为 1 的列表, 用于存储 carla.Actor 实例的引用

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
        attach_to = self._parent_ref[0]
        if attach_to is not None and not attach_to.is_alive:
            raise ValueError(f"Parent actor: '{attach_to.name}' not spawned yet or not alive")

        # 尝试生成 Actor
        try:
            actor = self._context.world.spawn_actor(self._bp, self._tf, attach_to=attach_to)
            self.logger.info(f"Spawned actor (CARLA ID: {actor.id}) at {Logging.short_tf(self._tf)}")
        except RuntimeError as e:
            if self._flag_ignore_spawn_failure:
                self.logger.warning(f"Failed to spawn actor but ignored: {e}")
                return self
            else:
                self.logger.error(f"Failed to spawn actor: {e}")
                raise e
        
        # 更新 Actor 实例引用
        self._actor_ref[0] = actor
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

    def _resolve_blueprint(self, bp: carla.ActorBlueprint | CarlaBlueprints | str) -> carla.ActorBlueprint:
        """将多种可能的蓝图输入统一为 carla.ActorBlueprint

        Args:
            bp (carla.ActorBlueprint | CarlaBlueprints | str): 蓝图输入

        Returns:
            carla.ActorBlueprint: 确定的 carla.ActorBlueprint 对象
        """
        if isinstance(bp, carla.ActorBlueprint):
            return bp
        elif isinstance(bp, CarlaBlueprints):
            return bp.to_carla()
        elif isinstance(bp, str):
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
        return self._bp

    def _resolve_parent(self, parent: carla.Actor | Self | None) -> list[carla.Actor | None]:
        """将多种可能的父级输入统一为 carla.Actor

        Args:
            parent (carla.Actor | Self | int | None): 父级输入

        Returns:
            list[carla.Actor | None]: 长度为 1 的列表, 用于存储 carla.Actor 实例的引用
        """
        if isinstance(parent, carla.Actor):
            return [parent]
        elif isinstance(parent, CarlaActor):
            return parent._actor_ref
        elif isinstance(parent, int):
            actor = self._context.world.get_actor(parent)
            if actor is None:
                raise ValueError(f"Actor with ID '{parent}' not found")
            return [actor]
        else:
            return [None]

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