import carla
import time
from typing import Dict, Any, TYPE_CHECKING
from typing_extensions import Self, Unpack

from shared.simulator import CarlaActor, CarlaVehicle, CarlaSensor, CarlaBlueprints, CarlaTransform
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
        self._actors: Dict[str, CarlaActor] = {}
        self._blueprint_library = self._context.world.get_blueprint_library()
        self._sync_mode_fps = context.fps
        self._actors_stable_threshold = context._actors_spawn_stable_threshold
        self._actors_stable_timeout = context._actors_spawn_stable_timeout
        self.logger = Logging().get_logger('ActorManager')

    @property
    def registry(self) -> Dict[str, CarlaActor]:
        return self._actors

    def __getitem__(self, key: str) -> CarlaActor:
        return self._actors[key]

    def __len__(self) -> int:
        return len(self._actors)

    def serialize(self) -> list[dict[str, Any]]:
        return [actor.serialize() for actor in self._actors.values()]

    def values(self) -> list[CarlaActor]:
        return list[CarlaActor](self._actors.values())

    def add(self, actor: CarlaActor):
        self._actors[actor.id_local] = actor
        self.logger.info(f"Registered actor container '{actor.id_local}' -> '{actor.name}'")
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
            if actor.parent is not None:
                if actor.parent.id_local not in self._actors:
                    raise RuntimeError(f"Actor '{actor.id_local}' depends on '{actor.parent.id_local}' which is not in registry")
                dependents[actor.parent.id_local].append(actor)
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
            actor.spawn(self._context.world, ignore_spawn_failure=ignore_spawn_failure)
        
        # 防止 attch 到空目标或者销毁错误
        self._context.tick()
        return self

    def destroy_all(self) -> Self:
        """销毁所有注册表中的 Actor"""
        for actor in self._actors.values():
            actor.destroy()
        try:
            self._context.tick()
        except RuntimeError as e:
            self.logger.error(f'Failed to tick world after destroying actors: {e}')
        return self

    def create_actor(
        self,
        bp: str | carla.ActorBlueprint | CarlaBlueprints,
        name: str = '',
        tf: carla.Transform | CarlaTransform | None = None,
        parent: carla.Actor | CarlaActor | None = None,
        *,
        ignore_attribute_failure: bool = False,
        target: type[CarlaActor] = CarlaActor,
        **attributes: Unpack[Dict[str, Any]],
    ) -> CarlaActor:
        """创建 CarlaActor 实例

        Args:
            bp (str | carla.ActorBlueprint | CarlaBlueprints): 蓝图输入
            name (str): 别名
            tf (carla.Transform): 初始变换
            parent (carla.Actor | CarlaActor | None): 附着到的目标 Actor
            ignore_attribute_failure (bool): 是否忽略属性失败
            target (type[CarlaActor]): 目标 CarlaActor 子类类型, 默认为 CarlaActor
            attributes (Unpack[Dict[str, Any]]): 蓝图属性

        Raises:
            ValueError: 蓝图输入不合规
            IndexError: 属性未找到, 且 ignore_attribute_failure 为 False
            ValueError: 属性设置失败, 且 ignore_attribute_failure 为 False

        Returns:
            CarlaActor: 创建的 CarlaActor 实例
        """
        # 解析蓝图
        bp = self.resolve_blueprint(bp)
        
        # 创建一个目标 CarlaActor 或其子类实例, 仅用作容器
        actor = target(bp, name=name)

        # 解析属性与变换
        self.resolve_attributes(actor, attributes, ignore_failure=ignore_attribute_failure)
        self.resolve_transform(actor, tf)

        # 附着目标
        actor.parent = parent

        # 注册到注册表
        self.add(actor)

        # 注册 Tick Blocker
        if target == CarlaSensor:
            auto_set = True
        else:
            auto_set = False
        self._context.bind_tick_blocker(actor.id_local + '_' + actor.name, actor.tick_blocker, auto_set=auto_set)

        return actor

    def create_vehicle(
        self,
        bp: str | carla.ActorBlueprint | CarlaBlueprints,
        tf: carla.Transform,
        parent: carla.Actor | CarlaActor | None = None,
        *,
        name: str = '',
        ignore_attribute_failure: bool = False,
        **attributes: Unpack[Dict[str, Any]],
    ) -> CarlaVehicle:
        """创建 CarlaVehicle 实例

        Args:
            bp (str | carla.ActorBlueprint | CarlaBlueprints): 蓝图输入
            name (str): 别名
            tf (carla.Transform): 初始变换
            parent (carla.Actor | CarlaActor | None): 附着到的目标 Actor
            ignore_attribute_failure (bool): 是否忽略属性失败
            attributes (Unpack[Dict[str, Any]]): 蓝图属性

        Raises:
            ValueError: 蓝图输入不合规
            IndexError: 属性未找到, 且 ignore_attribute_failure 为 False
            ValueError: 属性设置失败, 且 ignore_attribute_failure 为 False

        Returns:
            CarlaVehicle: 创建的 CarlaVehicle 实例
        """
        # 检查 BP 是否合规
        bp = self.resolve_blueprint(bp)
        if not bp.id.lower().startswith('vehicle.'):
            raise ValueError(f"Blueprint '{bp.id}' is not a vehicle blueprint")
        
        return self.create_actor(bp, name=name, tf=tf, parent=parent, ignore_attribute_failure=ignore_attribute_failure, target=CarlaVehicle, **attributes)
    
    def create_sensor(
        self,
        bp: str | carla.ActorBlueprint | CarlaBlueprints,
        tf: carla.Transform,
        parent: carla.Actor | CarlaActor | None = None,
        *,
        name: str = '',
        ignore_attribute_failure: bool = False,
        **attributes: Unpack[Dict[str, Any]],
    ) -> CarlaSensor:
        """创建 CarlaSensor 实例

        Args:
            bp (str | carla.ActorBlueprint | CarlaBlueprints): 蓝图输入
            tf (carla.Transform): 初始变换
            parent (carla.Actor | CarlaActor | None): 附着到的目标 Actor
            name (str): 别名
            ignore_attribute_failure (bool): 是否忽略属性失败
            attributes (Unpack[Dict[str, Any]]): 蓝图属性

        Raises:
            ValueError: 蓝图输入不合规
            IndexError: 属性未找到, 且 ignore_attribute_failure 为 False
            ValueError: 属性设置失败, 且 ignore_attribute_failure 为 False

        Returns:
            CarlaSensor: 创建的 CarlaSensor 实例
        """
        # 检查 BP 是否合规
        bp = self.resolve_blueprint(bp)
        if not bp.id.lower().startswith('sensor.'):
            raise ValueError(f"Blueprint '{bp.id}' is not a sensor blueprint")
        
        actor = self.create_actor(bp, name=name, tf=tf, parent=parent, ignore_attribute_failure=ignore_attribute_failure, target=CarlaSensor, **attributes)
        
        # 设置传感器颜色转换器
        if bp.id == CarlaBlueprints.SENSOR_CAMERA_INSTANCE_SEGMENTATION.value:
            actor.img_color_converter = self.resolve_img_color_converter(
                self._context.config.get("context/actors/img_cc_instance_segmentation", 
                default="CityScapesPalette")
            )
        elif bp.id == CarlaBlueprints.SENSOR_CAMERA_SEMANTIC_SEGMENTATION.value:
            actor.img_color_converter = self.resolve_img_color_converter(
                self._context.config.get("context/actors/img_cc_semantic_segmentation", 
                default="CityScapesPalette")
            )
        elif bp.id == CarlaBlueprints.SENSOR_CAMERA_DEPTH.value:
            actor.img_color_converter = self.resolve_img_color_converter(
                self._context.config.get("context/actors/img_cc_depth", 
                default="Depth")
            )

        return actor

    def find_by_local_id(self, id: str) -> CarlaActor | CarlaVehicle | CarlaSensor | None:
        """根据 ID 查找 Actor
        
        Args:
            id (str):  本地 ID
        """
        for actor in self._actors.values():
            if actor.id_local == id:
                return actor
        self.logger.warning(f"Actor with local ID '{id}' not found")
        return None

    def find_by_carla_id(self, id: int) -> CarlaActor | CarlaVehicle | CarlaSensor | None:
        """根据 CARLA ID 查找 Actor
        
        Args:
            type (type[CarlaActor]):  Actor 类型
            id (int):  CARLA ID
        """
        # 查找已有注册表
        for actor in self._actors.values():
            if actor.actor.id == id:
                return actor
        
        # 查找 CARLA 世界
        actor = self._context.world.get_actor(id)
        if actor is not None:
            bp = self.resolve_blueprint(actor.type_id)

            try:
                name = actor.attributes['role_name']
            except KeyError:
                name = ''

            # 组装本地容器
            if isinstance(actor, carla.Vehicle):
                local_actor = CarlaVehicle(bp, name=name, actor=actor)
                self.add(local_actor)
                return local_actor
            elif isinstance(actor, carla.Sensor):
                local_actor = CarlaSensor(bp, name=name, actor=actor)
                self.add(local_actor)
                return local_actor
            else:
                local_actor = CarlaActor(bp, name=name, actor=actor)
                self.add(local_actor)
                return local_actor
        return None

    def find_by_name(self, name: str) -> CarlaActor | CarlaVehicle | CarlaSensor | None:
        """根据名称查找 Actor
        
        Args:
            type (type[CarlaActor]):  Actor 类型
            name (str):  Actor 名称
        """
        # 查找已有注册表
        for actor in self._actors.values():
            if actor.name == name:
                return actor

        # 查找 CARLA 世界
        all_actors = self._context.world.get_actors()
        for actor in all_actors:
            try:
                role_name = actor.attributes['role_name']
            except KeyError:
                continue

            if role_name != name:
                continue

            bp = self.resolve_blueprint(actor.type_id)
            if isinstance(actor, carla.Vehicle):
                local_actor = CarlaVehicle(bp, name=name, actor=actor)
                self.add(local_actor)
                return local_actor
            elif isinstance(actor, carla.Sensor):
                local_actor = CarlaSensor(bp, name=name, actor=actor)
                self.add(local_actor)
                return local_actor
            else:
                local_actor = CarlaActor(bp, name=name, actor=actor)
                self.add(local_actor)
                return local_actor

        self.logger.warning(f"Actor with name '{name}' not found")
        return None

    def resolve_blueprint(
        self,
        blueprint: str | carla.ActorBlueprint | CarlaBlueprints,
    ) -> carla.ActorBlueprint:
        """将多种可能的蓝图输入统一为 carla.ActorBlueprint

        Args:
            blueprint (str | carla.ActorBlueprint | CarlaBlueprints): 蓝图输入

        Raises:
            KeyError: 蓝图未找到

        Returns:
            carla.ActorBlueprint: 确定的 carla.ActorBlueprint 对象
        """
        if isinstance(blueprint, CarlaBlueprints):
            blueprint = blueprint.value

        if isinstance(blueprint, str):
            try:
                blueprint = self._blueprint_library.find(blueprint)
            except IndexError as e:
                self.logger.error(f"Blueprint '{blueprint}' not found")
                raise e
        
        if isinstance(blueprint, carla.ActorBlueprint):
            self.logger.debug(f"Blueprint '{blueprint}' found")
            return blueprint

    def resolve_attributes(
        self,
        actor: CarlaActor,
        attributes: Dict[str, Any],
        *,
        ignore_failure: bool = False,
    ) -> Self:
        """将属性写入到 carla.ActorBlueprint 中

        Args:
            actor (CarlaActor): 目标 CarlaActor
            attributes (Dict[str, Any]): 蓝图属性
            ignore_failure (bool): 是否忽略失败, 如果为 True, 则不会抛出异常

        Raises:
            IndexError: 属性未找到
            ValueError: 属性设置失败

        Returns:
            Self: 链式调用支持
        """
        # 先处理默认别名
        if actor.bp.has_attribute('role_name'):
            actor.bp.set_attribute('role_name', actor.name)

        for key, value in attributes.items():
            try:
                actor.bp.set_attribute(key, str(value))
                actor.logger.debug(f"Attribute '{key}' set to '{str(value)}'")
            except IndexError as e:
                actor.logger.error(f"Attribute '{key}' not found in blueprint '{actor.bp.id}'")
                if not ignore_failure:
                    raise e
            except ValueError as e:
                actor.logger.error(f"Attribute '{key}' not set in blueprint '{actor.bp.id}': {e}")
                if not ignore_failure:
                    raise e
        return self

    def resolve_transform(
        self,
        actor: CarlaActor,
        tf: carla.Transform | CarlaTransform | None = None,
    ) -> Self:
        """将变换写入到 carla.Actor 中

        Args:
            actor (CarlaActor): 目标 carla.Actor
            tf (carla.Transform | CarlaTransform): 变换输入
        """
        if tf is None:
            actor.logger.warning(f"No initial transform provided. Using default transform.")
            tf = carla.Transform()
        if isinstance(tf, CarlaTransform):
            tf = tf.to_carla()
        actor.tf_init = tf
        return self

    def resolve_img_color_converter(self, name: str) -> carla.ColorConverter:
        """根据名称解析图像颜色转换器
        
        Args:
            name (str): 名称
        """
        if name.upper() == "RAW":
            return carla.ColorConverter.Raw
        elif name.upper() == "LOGARITHMICDEPTH":
            return carla.ColorConverter.LogarithmicDepth
        elif name.upper() == "DEPTH":
            return carla.ColorConverter.Depth
        elif name.upper() == "CITYSCAPESPALETTE":
            return carla.ColorConverter.CityScapesPalette
        else:
            raise ValueError(f"Invalid image color converter name: {name}")

    def wait_stable(self, *actors: CarlaActor):
        """等待指定 Actor 稳定
        
        Args:
            *actors (CarlaActor): 指定的 Actor, 如果为空, 则使用注册表中的所有 actors
        """
        # 当 actors 为空时，使用注册表中的所有 actors
        if not actors:
            actors = tuple(self._actors.values())

        # 过滤掉没有绑定实际 actor 的 actors
        actors = [actor for actor in actors if actor.actor is not None]
        
        # 记录每个 actor 的上次变换和稳定状态
        last_transforms: Dict[str, carla.Transform] = {}
        stable_flags: Dict[str, bool] = {}
        for actor in actors:
            last_transforms[actor.id_local] = actor.tf_now
            stable_flags[actor.id_local] = False
        
        # 开始计时
        timer = time.perf_counter()
        
        # 第一次必须进行 tick, 让 actors 有机会移动
        self._context.tick()
        time.sleep(1/self._sync_mode_fps)
        
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
                if (
                    abs(tf_current.location.x - tf_last.location.x) < self._actors_stable_threshold and
                    abs(tf_current.location.y - tf_last.location.y) < self._actors_stable_threshold and
                    abs(tf_current.location.z - tf_last.location.z) < self._actors_stable_threshold
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
            if time.perf_counter() - timer > self._actors_stable_timeout:
                self.logger.warning(f'Actors stable wait timeout after {self._actors_stable_timeout} seconds')
                break
            
            # 进行 tick 操作
            self._context.tick()
            time.sleep(1/self._sync_mode_fps)