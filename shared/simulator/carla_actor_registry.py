import carla
from typing import Dict 
from typing_extensions import Self

from shared.simulator import CarlaActor
from shared.utils import Logging


class CarlaActorRegistry:
    """
    CARLA Actor 注册表, 用于管理 CARLA Actor 的生命周期
    """

    def __init__(self, world: carla.World):
        self._world = world
        self._actors: Dict[str, CarlaActor] = {}
        self.logger = Logging().get_logger('ActorRegistry')

    @property
    def registry(self) -> Dict[str, CarlaActor]:
        return self._actors

    def __getitem__(self, key: str) -> CarlaActor:
        return self._actors[key]

    def __len__(self) -> int:
        return len(self._actors)

    @property
    def world(self) -> carla.World:
        return self._world

    @world.setter
    def world(self, value: carla.World):
        self.logger.warning(f"World is already set. Overwriting with {value.name}")
        self._world = value
        return

    def values(self) -> list[CarlaActor]:
        return list(self._actors.values())

    def add(self, actor: CarlaActor):
        self._actors[actor.id_local] = actor
        self.logger.info(f"Registered actor container '{actor.id_local}'")
        return

    def remove(self, actor: CarlaActor):
        if actor.id_local not in self._actors:
            self.logger.warning(f"Actor container '{actor.id_local}' not found in registry")
            return
        del self._actors[actor.id_local]
        self.logger.info(f"Removed actor container '{actor.id_local}'")
        return

    def spawn_all(self, *, ignore_spawn_failure: bool = False) -> Self:
        """生成所有注册表中的 Actor

        Raises:
            RuntimeError: 检测到循环依赖

        Returns:
            Self: 链式调用支持
        """
        # 构建依赖图：actor_id -> 依赖它的actors列表
        dependents: Dict[str, list[CarlaActor]] = {actor_id: [] for actor_id in self._actors.keys()}
        in_degree: Dict[str, int] = {actor_id: 0 for actor_id in self._actors.keys()}
        
        # 计算入度
        for actor in self._actors.values():
            if actor.attach_target is not None:
                if actor.attach_target.id_local not in self._actors:
                    raise RuntimeError(f"Actor '{actor.id_local}' depends on '{actor.attach_target.id_local}' which is not in registry")
                dependents[actor.attach_target.id_local].append(actor)
                in_degree[actor.id_local] += 1
        
        # Kahn算法进行拓扑排序
        queue: list[CarlaActor] = []
        sorted_actors: list[CarlaActor] = []
        
        # 将所有入度为0的actor加入队列, 即没有依赖的actor
        for actor_id, degree in in_degree.items():
            if degree == 0:
                queue.append(self._actors[actor_id])
        
        while queue:
            current = queue.pop(0)
            sorted_actors.append(current)
            
            # 遍历所有依赖当前actor的actors
            for dependent in dependents[current.id_local]:
                in_degree[dependent.id_local] -= 1
                if in_degree[dependent.id_local] == 0:
                    queue.append(dependent)
        
        # 检查是否存在循环依赖
        if len(sorted_actors) != len(self._actors):
            unsorted = [actor_id for actor_id, degree in in_degree.items() if degree > 0]
            raise RuntimeError(f"Circular dependency detected among actors: {unsorted}")
        
        # 按照依赖顺序spawn所有actors
        self.logger.info(f"Spawning {len(sorted_actors)} actors in dependency order")
        self.logger.debug(f"Sorted actors: {[actor.id_local for actor in sorted_actors]}")
        for actor in sorted_actors:
            actor.spawn(self._world, ignore_spawn_failure=ignore_spawn_failure)
        
        # 防止 attch 到空目标或者销毁错误
        self._world.tick()
        return self

    def destroy_all(self) -> Self:
        """销毁所有注册表中的 Actor"""
        for actor in self._actors.values():
            actor.destroy()
        return self