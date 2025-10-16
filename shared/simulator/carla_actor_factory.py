import carla
from typing import Dict, Any
from typing_extensions import Self, Unpack

from shared.simulator import CarlaActor, CarlaVehicle, CarlaSensor, CarlaBlueprints, CarlaTransform, CarlaActorRegistry
from shared.utils import Logging

class CarlaActorFactory:
    """
    CARLA 工厂, 用于创建 CARLA Actor
    """

    def __init__(
        self,
        world: carla.World,
        registry: CarlaActorRegistry,
    ):
        self.logger = Logging().get_logger('ActorFactory')
        self._world = world
        self._blueprint_library = self._world.get_blueprint_library()
        self._registry = registry

    def create_actor(
        self,
        bp: str | carla.ActorBlueprint | CarlaBlueprints,
        name: str = '',
        tf: carla.Transform | CarlaTransform | None = None,
        attach_to: carla.Actor | CarlaActor | None = None,
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
            attach_to (carla.Actor | CarlaActor | None): 附着到的目标 Actor
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
        bp = self._resolve_blueprint(bp)
        
        # 创建一个目标 CarlaActor 或其子类实例, 仅用作容器
        actor = target(bp, name=name)

        # 解析属性与变换
        self._resolve_attributes(actor, attributes, ignore_failure=ignore_attribute_failure)
        self._resolve_transform(actor, tf)

        # 附着目标
        actor.attach_target = attach_to

        # 注册到注册表
        self._registry.add(actor)

        return actor

    def create_vehicle(
        self,
        bp: str | carla.ActorBlueprint | CarlaBlueprints,
        tf: carla.Transform,
        attach_to: carla.Actor | CarlaActor | None = None,
        *,
        ignore_attribute_failure: bool = False,
        **attributes: Unpack[Dict[str, Any]],
    ) -> CarlaVehicle:
        """创建 CarlaVehicle 实例

        Args:
            bp (str | carla.ActorBlueprint | CarlaBlueprints): 蓝图输入
            tf (carla.Transform): 初始变换
            attach_to (carla.Actor | CarlaActor | None): 附着到的目标 Actor
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
        bp = self._resolve_blueprint(bp)
        if not bp.id.lower().startswith('vehicle.'):
            raise ValueError(f"Blueprint '{bp.id}' is not a vehicle blueprint")
        
        return self.create_actor(bp, tf, attach_to, ignore_attribute_failure=ignore_attribute_failure, target=CarlaVehicle, **attributes)
    
    def create_sensor(
        self,
        bp: str | carla.ActorBlueprint | CarlaBlueprints,
        tf: carla.Transform,
        attach_to: carla.Actor | CarlaActor | None = None,
        *,
        ignore_attribute_failure: bool = False,
        **attributes: Unpack[Dict[str, Any]],
    ) -> CarlaSensor:
        """创建 CarlaSensor 实例

        Args:
            bp (str | carla.ActorBlueprint | CarlaBlueprints): 蓝图输入
            tf (carla.Transform): 初始变换
            attach_to (carla.Actor | CarlaActor | None): 附着到的目标 Actor
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
        bp = self._resolve_blueprint(bp)
        if not bp.id.lower().startswith('sensor.'):
            raise ValueError(f"Blueprint '{bp.id}' is not a sensor blueprint")
        
        return self.create_actor(bp, tf, attach_to, ignore_attribute_failure=ignore_attribute_failure, target=CarlaSensor, **attributes)

    def _resolve_blueprint(
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

    def _resolve_attributes(
        self,
        actor: CarlaActor,
        attributes: Dict[str, Any],
        *,
        ignore_failure: bool = False,
    ) -> Self:
        """将属性写入到 carla.ActorBlueprint 中

        Args:
            bp (carla.ActorBlueprint): 蓝图
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

    def _resolve_transform(
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