import carla
from typing import TYPE_CHECKING, Any, Dict
from typing_extensions import Unpack

from shared.simulator import CarlaActor, CarlaBlueprints, CarlaTransform, CarlaVehicle, CarlaSensor

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

    def __len__(self) -> int:
        return len(self._known_actors)

    def add(self, actor: CarlaActor):
        self._known_actors.add(actor)

    def remove(self, actor: CarlaActor):
        self._known_actors.remove(actor)

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
        parent: carla.Actor | CarlaActor | None = None,
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
            parent (carla.Actor | CarlaActor | None): 父级对象
            name (str | None): 别名
            ignore_attribute_failure (bool): 是否忽略属性失败
            ignore_spawn_failure (bool): 是否忽略生成失败
            is_managed_actor (bool): 是否被管理
            attributes (Unpack[dict[str, Any]]): 蓝图属性

        Returns:
            CarlaVehicle: 创建的 CarlaVehicle 实例
        """
        actor = self.create_actor(
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
        actor = self.create_actor(
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