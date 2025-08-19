import carla
from logging import getLogger
from typing_extensions import Self

from core.simulator import CarlaContext, CarlaUtils
from core.utils import UniqueTagProvider


class CarlaActor(object):
    """
    对 ``carla.Actor`` 的二次封装, 提供便利工具
    """

    def __init__(
            self,
            world: carla.World | CarlaContext,
            blueprint: carla.ActorBlueprint | str,
            *,
            name: str | None = None,
            log_level: int | None = None,
    ) -> None:
        """
        :param world: Actor 所在的仿真世界或上下文
        :param blueprint: 蓝图
        :param name: 名称, 为 ``None`` 时自动指定
        :param log_level: 日志等级, 对日志的对象级控制
        """
        # 名称优先于日志被确定, 防止日志初始化失败
        self._name = self._resolve_name(name)

        # 日志及其等级设置
        self.logger = getLogger(self._name)
        if log_level is not None:
            self.logger.setLevel(log_level)

        self._world = self._resolve_world(world)
        self._blueprint = self._resolve_blueprint(blueprint)
        self._actor: carla.Actor | None = None
        self._tf_spawn: carla.Transform | None = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 确保程序退出时, Actor 被销毁
        if self.is_alive:
            self.destroy()

    def __str__(self):
        return f"{self.name}#{self.id}"

    @property
    def id(self) -> int:
        """
        :return: Actor 在 CARLA Server 中的 id, 未激活状态返回 ``0``
        """
        if self.is_alive:
            return self._actor.id
        else:
            return 0

    @property
    def name(self) -> str:
        """
        :return: Actor 对象的名称, 和蓝图中的 ``role_name`` 保持一致, 只读属性
        """
        return self._name

    @property
    def blueprint(self) -> carla.ActorBlueprint:
        """
        :return: Actor 使用的蓝图, 只读属性
        """
        return self._blueprint

    @property
    def is_alive(self) -> bool:
        """
        :return: 检查对象是否在仿真上下文中存活
        """
        if isinstance(self._actor, carla.Actor):
            return self._actor.is_active
        return False

    def get_transform(self) -> carla.Transform | None:
        """
        获取当前 Actor 的 Transform, Actor 未存活时返回 ``None``
        :return: Actor 当前帧的 Transform
        """
        if self.is_alive:
            return self._actor.get_transform()
        return None

    def get_transform_spawn(self) -> carla.Transform | None:
        """
        获取当前 Actor 最后一次 Spawn 瞬间的 Transform, 未执行第一次 ``spawn()`` 时返回 ``None``
        :return: Actor 最后一次 Spawn 时的 Transform
        """
        return self._tf_spawn

    def set_transform(
            self,
            transform: carla.Transform | None = None,
            *,
            x: float = None,
            y: float = None,
            z: float = None,
            yaw: float = None,
            pitch: float = None,
            roll: float = None,
    ) -> Self:
        """
        设置 Actor 的 Transform.

        特别注意, 当 ``spawn()`` 时指定了 ``attach`` 时, 该值始终为相对值.

        :param transform: 设置的 ``carla.Transform`` 为 ``None`` 时默认构建全 ``0`` 的对象
        :param x: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param y: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param z: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param yaw: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param pitch: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param roll: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :return: ``self`` 该方法支持链式调用
        """
        # 解析 Transform 覆写
        transform = self._resolve_transform_override(transform, x, y, z, yaw, pitch, roll)

        # 执行
        if self.is_alive:
            self._actor.set_transform(transform)
            self.logger.debug(f"Set transform to {CarlaUtils.short_tf(transform)}")


    def set_attribute(self, key: str, value: str | float | int) -> Self:
        """
        设置 Actor 的 Blueprint Attribute.

        允许在 Actor 已经 Spawn 的状态下设置 Attribute, 但由于 CARLA Actor 生命周期的限制, 这种设置将不会立刻应用
        在这种情况下, 必须重新 Spawn Actor

        :param key: Attribute 的键
        :param value: Attribute 的值
        :return: ``self`` 该方法支持链式调用
        """
        if self.is_alive:
            self.logger.warning('Attempted to set attribute while actor is already alive, '
                                'requires respawn for changes to take effect')

        self._blueprint.set_attribute(key, str(value))  # 此处的强制转换是 CARLA API 的要求
        self.logger.debug(f'Setting attribute {key} to {value}')
        return self

    def get_attribute(self, key: str) -> float | int | str | bool | carla.Color | None:
        """
        读取 Actor 的 Blueprint Attribute. 封装了复杂的 CARLA 类型转换. 无法找到 Attribute 的时候返回 ``None``
        :param key: Attribute 的键
        :return: Attribute 的值, 类型自动转换
        """
        try:
            attribute = self._blueprint.get_attribute(key)
            if not isinstance(attribute, carla.ActorAttribute):
                return None
        except KeyError:
            return None

        if attribute.type == carla.ActorAttributeType.Int:
            return attribute.as_int()
        if attribute.type == carla.ActorAttributeType.Float:
            return attribute.as_float()
        if attribute.type == carla.ActorAttributeType.String:
            return attribute.as_string()
        if attribute.type == carla.ActorAttributeType.Bool:
            return attribute.as_bool()
        if attribute.type == carla.ActorAttributeType.Color:
            return attribute.as_color()
        return None

    def spawn(
            self,
            transform: carla.Transform | None = None,
            *,
            x: float = None,
            y: float = None,
            z: float = None,
            yaw: float = None,
            pitch: float = None,
            roll: float = None,
            attach: carla.Actor | Self = None,
    ) -> Self:
        """
        在 World 中生成 Actor
        :param transform: ``carla.Transform`` 为 ``None`` 时默认构建全 ``0`` 的对象
        :param x: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param y: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param z: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param yaw: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param pitch: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param roll: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param attach: 生成该 Actor 时绑定的对象, 可以为 ``carla.Actor`` 或者封装的 ``CarlaActor`` 实例
        :return: ``self`` 该方法支持链式调用
        :raises RuntimeError: CARLA 服务器无法正常 Spawn Actor 时引发该异常
        """
        # 解析 Transform 覆写
        transform = self._resolve_transform_override(transform, x, y, z, yaw, pitch, roll)

        # 如果发生了覆写, 打印一个日志
        overrides = (x, y, z, yaw, pitch, roll)
        if any(i is not None for i in overrides):
            self.logger.debug(f'Transform overrides happened when spawning actor')

        # 处理蓝图
        self._blueprint.set_attribute('role_name', self.name)

        # 处理 Attach To
        attach_target = None
        if isinstance(attach, carla.Actor):
            attach_target = attach
        if isinstance(attach, CarlaActor):
            attach_target = attach._actor

        # 执行 Spawn
        self._actor = self._world.try_spawn_actor(self._blueprint, self._tf_spawn, attach_to=attach_target)
        if self._actor is None:
            raise RuntimeError(f'Spawn failed')
        else:
            self.logger.debug(f'Spawn succeeded at {CarlaUtils.short_tf(self._actor.role_name)}')

        # 记录 Spawn 时的 Transform
        self._tf_spawn = transform

        return self

    def destroy(self) -> None:
        """
        从 CARLA Server 中销毁当前 Actor
        :return:
        """
        if isinstance(self._actor, carla.Actor):
            self._actor.destroy()
            self._actor = None
            self._tf_spawn = None
            self.logger.debug(f'Destroyed by user')

    def _resolve_blueprint(self, bp: carla.ActorBlueprint | str) -> carla.ActorBlueprint:
        """
        对蓝图进行解析, 得到确定的 ``carla.ActorBlueprint``
        :param bp: 可能得到 ``carla.ActorBlueprint`` 的多种输入类型
        :return: ``carla.ActorBlueprint`` 实例
        """
        if isinstance(bp, carla.ActorBlueprint):
            return bp
        elif isinstance(bp, str):
            result = self._world.get_blueprint_library().find(bp)
            if not result:
                msg = f"Can not found blueprint '{bp}' in current world's blueprint library"
                self.logger.warning(msg)
                raise ValueError(msg)
            return result

    def _resolve_name(self, name: str | None) -> str:
        """
        解析名称, 如果 ``name`` 有非空输入则返回 ``name``, 否则使用 ``UniqueTagProvider`` 构造默认名称
        :param name: 可能的名称输入
        :return: 对象的名称
        """
        if name:
            return name
        result = self.__class__.__name__
        result += UniqueTagProvider()
        return result

    @staticmethod
    def _resolve_world(opt: carla.World | CarlaContext) -> carla.World:
        """
        对 World 进行解析, 得到 ``carla.World``
        :param opt: 可能得到 ``carla.World`` 的多种输入
        :return: ``carla.World`` 实例
        """
        if isinstance(opt, carla.World):
            return opt
        elif isinstance(opt, CarlaContext):
            return opt.world

    @staticmethod
    def _resolve_transform_override(
            transform: carla.Transform | None,
            x: float | None,
            y: float | None,
            z: float | None,
            yaw: float | None,
            pitch: float | None,
            roll: float | None,
    ) -> carla.Transform:
        """
        解析带覆写功能的 Transform
        :param transform: 设置的 ``carla.Transform`` 为 ``None`` 时默认构建全 ``0`` 的对象
        :param x: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param y: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param z: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param yaw: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param pitch: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :param roll: 对 ``transform`` 的覆写值, 默认 ``None`` 时不进行覆写
        :return: 最终给的 ``carla.Transform`` 结果
        """
        transform = transform or carla.Transform()

        # 覆写
        if x is not None:
            transform.location.x = x
        if y is not None:
            transform.location.y = y
        if z is not None:
            transform.location.z = z
        if yaw is not None:
            transform.rotation.yaw = yaw
        if pitch is not None:
            transform.rotation.pitch = pitch
        if roll is not None:
            transform.rotation.roll = roll

        return transform