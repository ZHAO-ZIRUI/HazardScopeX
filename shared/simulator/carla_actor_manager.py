import carla
import time
import yaml
from logging import Logger
from typing import TYPE_CHECKING, Any, Dict
from typing_extensions import Unpack, Self

from shared.simulator import CarlaActor, CarlaBlueprints, CarlaTransform, CarlaVehicle, CarlaSensor
from shared.utils import Logging

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


class CarlaActorManager:
    """
    CARLA Actor 管理器, 用于管理 CARLA Actor 的生命周期和创建
    """

    def __init__(
        self,
        context: 'CarlaContext',
    ):
        self._context = context
        self._known_actors: set[CarlaActor] = set()
        self._logger = Logging().get_logger('ActorManager')

    def __len__(self) -> int:
        return len(self._known_actors)

    @property
    def logger(self) -> Logger:
        """日志记录器, 只读"""
        return self._logger

    def add(self, actor: CarlaActor) -> Self:
        """添加 Actor 到注册表
        
        Args:
            actor (CarlaActor): 要添加的 Actor

        Returns:
            Self: 链式调用支持
        """
        before_count = len(self._known_actors)
        self._known_actors.add(actor)
        after_count = len(self._known_actors)
        if after_count - before_count == 1:
            self.logger.debug(f"Added actor '{actor.name}' to registry")
        elif after_count - before_count == 0:
            self.logger.debug(f"Added actor '{actor.name}' to registry but it was already in registry")
        return self

    def remove(self, actor: CarlaActor) -> Self:
        """从注册表中移除 Actor
        
        Args:
            actor (CarlaActor): 要移除的 Actor

        Returns:
            Self: 链式调用支持
        """
        before_count = len(self._known_actors)
        self._known_actors.remove(actor)
        after_count = len(self._known_actors)
        if after_count - before_count == -1:
            self.logger.debug(f"Removed actor '{actor.name}' from registry")
        elif after_count - before_count == 0:
            self.logger.debug(f"Removed actor '{actor.name}' from registry but it was not in registry")
        return self

    def create_actor(
        self,
        bp: carla.ActorBlueprint | CarlaBlueprints | str,
        tf: carla.Transform | CarlaTransform,
        *,
        parent: carla.Actor | CarlaActor | None = None,
        name: str | None = None,
        ignore_attribute_failure: bool = False,
        ignore_spawn_failure: bool = False,
        is_managed_actor: bool = True,
        **attributes: Unpack[dict[str, Any]],
    ) -> CarlaActor:
        """创建 CarlaActor 实例, 返回 CarlaActor 实例

        Args:
            bp (carla.ActorBlueprint | CarlaBlueprints | str): 蓝图
            tf (carla.Transform | CarlaTransform): 初始变换
            parent (carla.Actor | CarlaActor | None): 父级对象
            name (str | None): 别名
            ignore_attribute_failure (bool): 是否忽略属性失败
            ignore_spawn_failure (bool): 是否忽略生成失败
            is_managed_actor (bool): 是否被管理
            attributes (Unpack[dict[str, Any]]): 蓝图属性

        Returns:
            CarlaActor: 创建的 CarlaActor 实例
        """
        actor = CarlaActor(
            context=self._context,
            bp=bp,
            tf=tf,
            parent=parent,
            name=name,
            ignore_attribute_failure=ignore_attribute_failure,
            ignore_spawn_failure=ignore_spawn_failure,
            is_managed_actor=is_managed_actor,
            **attributes,
        )
        return actor

    def create_vehicle(
        self,
        bp: carla.ActorBlueprint | CarlaBlueprints | str,
        tf: carla.Transform | CarlaTransform,
        *,
        name: str | None = None,
        ignore_attribute_failure: bool = False,
        ignore_spawn_failure: bool = False,
        is_managed_actor: bool = True,
        **attributes: Unpack[dict[str, Any]],
    ) -> CarlaVehicle:
        """创建 CarlaVehicle 实例, 返回 CarlaVehicle 实例

        Args:
            bp (carla.ActorBlueprint | CarlaBlueprints | str): 蓝图
            tf (carla.Transform | CarlaTransform): 初始变换
            name (str | None): 别名
            ignore_attribute_failure (bool): 是否忽略属性失败
            ignore_spawn_failure (bool): 是否忽略生成失败
            is_managed_actor (bool): 是否被管理
            attributes (Unpack[dict[str, Any]]): 蓝图属性

        Returns:
            CarlaVehicle: 创建的 CarlaVehicle 实例
        """
        actor = CarlaVehicle(
            context=self._context,
            bp=bp,
            tf=tf,
            name=name,
            ignore_attribute_failure=ignore_attribute_failure,
            ignore_spawn_failure=ignore_spawn_failure,
            is_managed_actor=is_managed_actor,
            **attributes,
        )
        return actor

    def create_sensor(
        self,
        bp: carla.ActorBlueprint | CarlaBlueprints | str,
        tf: carla.Transform | CarlaTransform,
        *,
        parent: carla.Actor | CarlaActor | None = None,
        name: str | None = None,
        ignore_attribute_failure: bool = False,
        ignore_spawn_failure: bool = False,
        is_managed_actor: bool = True,
        image_color_converter: carla.ColorConverter | None = None,
        **attributes: Unpack[dict[str, Any]],
    ) -> CarlaSensor:
        """创建 CarlaSensor 实例, 返回 CarlaSensor 实例

        Args:
            bp (carla.ActorBlueprint | CarlaBlueprints | str): 蓝图
            tf (carla.Transform | CarlaTransform): 初始变换
            parent (carla.Actor | CarlaActor | None): 父级对象
            name (str | None): 别名
            ignore_attribute_failure (bool): 是否忽略属性失败
            ignore_spawn_failure (bool): 是否忽略生成失败
            is_managed_actor (bool): 是否被管理
            image_color_converter (carla.ColorConverter | None): 图像颜色转换器
            attributes (Unpack[dict[str, Any]]): 蓝图属性

        Returns:
            CarlaSensor: 创建的 CarlaSensor 实例
        """
        actor = CarlaSensor(
            context=self._context,
            bp=bp,
            tf=tf,
            parent=parent,
            name=name,
            ignore_attribute_failure=ignore_attribute_failure,
            ignore_spawn_failure=ignore_spawn_failure,
            is_managed_actor=is_managed_actor,
            image_color_converter=image_color_converter,
            **attributes,
        )
        return actor

    def spawn_all(self) -> Self:
        """生成所有注册表中的 Actor"""

        # 按照父级关系排序
        sorted_actors = self._topological_sort_by_parent()
        self.logger.debug(f"Sorted actors: {[actor.name for actor in sorted_actors]}")
        
        for actor in sorted_actors:
            if actor.is_alive:
                self._logger.warning(f"Actor '{actor.name}' is already alive, skipping spawn")
                continue
            actor.spawn()
        return self

    def destroy_all(
        self,
        *,
        remove_from_registry: bool = True,
        remove_unmanaged_actors: bool = False,
    ) -> Self:
        """销毁所有注册表中的 Actor"""
        if remove_unmanaged_actors:
            actors_to_remove = [actor for actor in self._known_actors if not actor.is_managed_actor]
        else:
            actors_to_remove = list(self._known_actors)
        for actor in actors_to_remove:
            actor.destroy()
            if remove_from_registry:
                self.remove(actor)
        self._context.tick(force=True)
        return self

    def wait_stable(self, *actors: CarlaActor):
        """等待指定 Actor 稳定
        
        Args:
            *actors (CarlaActor): 指定的 Actor, 如果为空, 则使用注册表中的所有 actors
        """
        # 当 actors 为空时，使用注册表中的所有 actors
        if not actors:
            actors = self._known_actors
        
        # 记录每个 actor 的上次变换和稳定状态
        last_transforms: Dict[str, carla.Transform] = {}
        stable_flags: Dict[str, bool] = {}
        for actor in actors:
            last_transforms[actor.id_local] = actor.tf_now
            stable_flags[actor.id_local] = False
        
        # 开始计时
        timer = time.perf_counter()
        
        # 第一次必须进行 tick, 让 actors 有机会移动
        self._context.tick(force=True)
        time.sleep(1/self._context.fps)
        
        while True:
            # 检查所有 actors 是否都稳定
            all_stable = True
            for actor in actors:
                # 跳过已经稳定的 actor
                if stable_flags[actor.id_local]:
                    continue
                
                tf_current = actor.tf_now
                tf_last = last_transforms[actor.id_local]
                
                # 检查位置变化是否小于阈值
                threshold = self._context.configs.actor_manager.spawn_wait_stable_threshold
                if (
                    abs(tf_current.location.x - tf_last.location.x) < threshold and
                    abs(tf_current.location.y - tf_last.location.y) < threshold and
                    abs(tf_current.location.z - tf_last.location.z) < threshold
                ):
                    stable_flags[actor.id_local] = True
                    actor.logger.debug(f"Actor is stable at {Logging.short_tf(tf_current)}")
                else:
                    all_stable = False
                    last_transforms[actor.id_local] = tf_current
            
            # 如果所有 actors 都稳定，退出循环
            if all_stable:
                self.logger.info(f'All {len(actors)} actors are stable: {[actor.name for actor in actors]}')
                break
            
            # 检查是否超时
            timeout = self._context.configs.actor_manager.spawn_wait_stable_timeout
            if time.perf_counter() - timer > timeout:
                self.logger.warning(f'Actors stable wait timeout after {timeout} seconds')
                break
            
            # 进行 tick 操作
            self._context.tick(force=True)
            try:
                time.sleep(1/self._context.fps)
            except KeyboardInterrupt:
                self.logger.warning('Wait stable interrupted by user')
                raise SystemExit(102)

    def find_by_local_id(self, id: str) -> CarlaActor | CarlaVehicle | CarlaSensor | None:
        """根据本地 ID 查找 Actor
        
        Args:
            id (str): 本地 ID

        Returns:
            CarlaActor | None: 找到的 Actor, 如果未找到, 则返回 None
        """
        for actor in self._known_actors:
            if actor.id_local == id:
                return actor
        return None

    def find_by_carla_id(self, id: int) -> CarlaActor | CarlaVehicle | CarlaSensor | None:
        """根据 CARLA ID 查找 Actor
        
        Args:
            id (int):  CARLA 服务端的 Actor ID

        Returns:
            CarlaActor | None: 找到的 Actor, 如果未找到, 则返回 None
        """
        # 查找已有注册表
        for actor in self._known_actors:
            if actor.id_carla == id:
                return actor

        # 查找 CARLA 世界
        actor = self._context.world.get_actor(id)
        if actor is None:
            return None
        if isinstance(actor, carla.Vehicle):
            return CarlaVehicle.from_carla(self._context, actor)
        elif isinstance(actor, carla.Sensor):
            return CarlaSensor.from_carla(self._context, actor)
        else:
            return CarlaActor.from_carla(self._context, actor)

    def find_by_name(self, name: str) -> CarlaActor | CarlaVehicle | CarlaSensor | None:
        """根据名称查找 Actor"""
        # 查找已有注册表
        for actor in self._known_actors:
            if actor.name == name:
                return actor

        # 查找 CARLA 世界中的 Actor role_name
        all_actors = self._context.world.get_actors()
        for actor in all_actors:
            if actor.attributes.get('role_name', None) != name:
                continue
            if isinstance(actor, carla.Vehicle):
                return CarlaVehicle.from_carla(self._context, actor)
            elif isinstance(actor, carla.Sensor):
                return CarlaSensor.from_carla(self._context, actor)
            else:
                return CarlaActor.from_carla(self._context, actor)
        return None

    def serialize_all(self) -> list[dict[str, Any]]:
        return [actor.serialize() for actor in self._known_actors]
        
    def _topological_sort_by_parent(self) -> list[CarlaActor]:
        """根据父级依赖关系对 Actor 进行拓扑排序
        
        Returns:
            list[CarlaActor]: 排序后的 Actor 列表，父级 Actor 在子级之前
        """
        # 构建依赖图：记录每个 actor 的子级列表
        children_map: Dict[CarlaActor, list[CarlaActor]] = {}
        # 记录所有 actors
        all_actors = list(self._known_actors)
        
        # 初始化 children_map
        for actor in all_actors:
            children_map[actor] = []
        
        # 构建依赖关系：如果 actor 有 parent，则 parent 依赖于 actor（parent 必须先生成）
        # 实际上我们需要的是：parent -> children 的映射
        for actor in all_actors:
            parent = actor.parent
            if parent is not None and parent in self._known_actors:
                children_map[parent].append(actor)
        
        # Kahn's algorithm: 拓扑排序
        # 计算每个 actor 的入度（有多少个 actor 依赖于它）
        in_degree: Dict[CarlaActor, int] = {}
        for actor in all_actors:
            in_degree[actor] = 0
        
        # 计算入度：如果 actor 有 parent，则 actor 的入度为 1
        for actor in all_actors:
            if actor.parent is not None and actor.parent in self._known_actors:
                in_degree[actor] = 1
        
        # 找到所有入度为 0 的节点（没有 parent 的 actors）
        queue: list[CarlaActor] = [actor for actor in all_actors if in_degree[actor] == 0]
        result: list[CarlaActor] = []
        
        # 拓扑排序
        while queue:
            # 取出一个入度为 0 的节点
            current = queue.pop(0)
            result.append(current)
            
            # 处理当前节点的所有子节点
            for child in children_map[current]:
                in_degree[child] -= 1
                # 如果子节点的入度变为 0，加入队列
                if in_degree[child] == 0:
                    queue.append(child)
        
        # 检查是否有循环依赖（理论上不应该发生，但作为安全检查）
        if len(result) != len(all_actors):
            self._logger.warning(
                f"Topological sort incomplete: {len(result)}/{len(all_actors)} actors sorted. "
                "Possible circular dependency detected."
            )
            # 将未排序的 actors 添加到结果末尾
            remaining = [actor for actor in all_actors if actor not in result]
            result.extend(remaining)
        
        return result