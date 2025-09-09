import time
import carla
import math
from typing import List, Callable
from typing_extensions import Self

from core.simulator import *
from core.data import VehicleDirectControl


class CarlaVehicle(CarlaActor):
    """
    对 ``carla.Vehicle`` 的高级行为进行二次封装
    """

    DEFAULT_VEHICLE_MASS = 1500.0   # KG

    def __init__(
            self,
            context: CarlaContext,
            blueprint: carla.ActorBlueprint | str | CarlaBlueprints,
            *,
            tf: carla.Transform | None = None,
            name: str | None = None,
            log_level: int | None = None,
    ) -> None:
        """
        :param context: Actor 所在的仿真上下文
        :param blueprint: 蓝图
        :param name: 名称, 为 ``None`` 时自动指定
        :param log_level: 日志等级, 对日志的对象级控制
        :param tf: Actor 生成时的默认坐标, 为 ``None`` 时需要在 ``spawn()`` 时指定
        """
        if not isinstance(context, CarlaContext):
            raise TypeError('world attribute must be an CarlaContext for using TrafficManager')

        super().__init__(context, blueprint, name=name, log_level=log_level, tf=tf)
        self._traffic_manager = context.traffic_manager
        self._sensors: list[CarlaSensor] = list()
        self._hook_after_collision: list[Callable] = list()
        self._lazy_mass_kg: float | None = None
        self._performance: CarlaVehiclePerformance = CarlaVehiclePerformance()
        self._added_force: carla.Vector3D | None = None

    @property
    def actor(self) -> carla.Vehicle:
        """
        :return: 当前封装类所对应的 ``carla.Vehicle`` 实例, Actor 未 Spawn 或者已经被销毁时返回 ``None``
        """
        return self._actor

    @property
    @CarlaActor.require_actor_alive
    def mass(self) -> float:
        """
        :return: 车辆的质量, 单位 KG
        """
        if self._lazy_mass_kg is not None:
            return self._lazy_mass_kg
        if self.is_alive:
            self._lazy_mass_kg = self._actor.get_physics_control().mass
            self.logger.debug(f"Vehicle mass is {self._lazy_mass_kg} kg, defined by CARLA")
            return self._lazy_mass_kg
        return self.DEFAULT_VEHICLE_MASS

    @property
    @CarlaActor.require_actor_alive
    def speed(self) -> float:
        """
        :return: 车辆的表显速度, 单位 KM/H
        """
        speed_m_s = math.sqrt(
            self.actor.get_velocity().x ** 2 +
            self.actor.get_velocity().y ** 2 +
            self.actor.get_velocity().z ** 2
        )
        speed_km_h = speed_m_s * 3.6
        return speed_km_h

    @property
    def performance(self) -> CarlaVehiclePerformance:
        return self._performance

    @performance.setter
    def performance(self, value: CarlaVehiclePerformance) -> None:
        self._performance = value
        self.logger.debug(f"Vehicle performance update: {value}")

    def add_sensor(self, sensor: CarlaSensor | List[CarlaSensor], *sensors: CarlaSensor) -> Self:
        """
        向车辆增加传感, 该方法允许在任何情况下使用

        可以使用下列任意方式调用:

        - v.add_sensor(s1)
        - v.add_sensor([s1, s2])
        - v.add_sensor(s1, s2)

        :param sensor: ``CarlaSensor`` 实例及其派生, 或者输入一个 ``CarlaSensor`` 的列表
        :param sensors: 不定长度的 ``CarlaSensor`` 实例
        :return: ``self`` 该方法支持链式调用
        """
        # 整流输入
        sensor_list: List[CarlaSensor] = list()
        if isinstance(sensor, CarlaSensor):
            sensor_list.append(sensor)
        if isinstance(sensor, list):
            sensor_list.extend(sensor)
        if sensors:
            sensor_list.extend(sensors)

        # 如果当前车辆已经可用, 则先对 sensor 执行 spawn 操作
        if self.is_alive:
            for s in sensor_list:
                s.spawn(attach=self._actor)

        # 加入车辆管理的传感器列表
        self._sensors.extend(sensor_list)

        return self

    def get_sensors(self) -> list[CarlaSensor]:
        """
        :return: 车辆全部传感器的列表
        """
        return self._sensors

    def get_sensor_by_name(self, name: str) -> CarlaSensor | None:
        """
        通过传感器的名称检索得到一个特定的传感器
        :param name: 检索名
        :return: ``CarlaSensor`` 实例, 找不到时返回 ``None``
        """
        for s in self._sensors:
            if s.name == name:
                return s
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
        # 阻止车辆被添加到其他对象
        if attach is not None:
            msg = f"Not allowed to attach vehicle to some actor. Attach option is ignored."
            self.logger.warning(msg)

        # 调用父类方法执行 spawn
        super().spawn(
            transform=transform,
            x=x,
            y=y,
            z=z,
            yaw=yaw,
            pitch=pitch,
            roll=roll,
            attach=None
        )

        # 生成传感器并检查是否有碰撞传感器
        collision_sensor = None
        for s in self._sensors:
            if s.blueprint.id == CarlaBlueprints.SENSOR_OTHER_COLLISION.value:
                collision_sensor = s
            s.spawn(attach=self._actor)

        # 如果没有碰撞传感器则建立一个
        if collision_sensor is None:
            collision_sensor = CarlaSensor(
                self._context,
                blueprint=CarlaBlueprints.SENSOR_OTHER_COLLISION,
                name=f"{self.name}CollisionSensor",
            )
            collision_sensor.spawn()
            self._sensors.append(collision_sensor)

        # 绑定碰撞事件
        collision_sensor.hook_after_senser_data_recv.extend(self._hook_after_collision)

        return self

    def destroy(self) -> None:
        """
        从 CARLA Server 中销毁当前 Vehicle, 在销毁前优先处理传感器的销毁
        """
        for sensor in self._sensors:
            sensor.destroy()
        super().destroy()

    @CarlaActor.require_actor_alive
    def tick(self):
        """每次 Tick 车辆执行的操作, CARLA 处于同步模式时直接调用, 处于异步模式时使用 ``world.on_tick()`` 或者在单独线程中调用"""
        # 处理使用外部力刹车时的静止操作
        if isinstance(self._added_force, carla.Vector3D) and self.speed < 1:
            self.apply_full_stop()

    @CarlaActor.require_actor_alive
    @CarlaActor.require_sync_mode
    def wait_all_sensor_data_ready(self) -> Self:
        """
        阻塞等待全部的传感器处理完成, 该方法仅限在同步模式下使用
        :return: ``self`` 以支持链式调用
        """
        current_frame = self._world.get_snapshot().frame

        # 确定监听的传感器, 排除事件触发型的传感器
        sensors: List[CarlaSensor] = list()
        for sensor in self._sensors:
            if str(sensor.blueprint.id) in CarlaBlueprints.get_event_sensor_blueprints_set():
                continue
            sensors.append(sensor)

        while True:
            # 确保所有的数据 frame id 与最新的 frame id 一致
            time.sleep(0.001)
            flag = all(sensor.get_data().frame_id == current_frame for sensor in sensors)
            if flag:
                break
        return self

    @CarlaActor.require_actor_alive
    def apply_carla_direct_control(
            self,
            control: VehicleDirectControl | carla.VehicleControl = None,
            *,
            throttle: float | None = None,
            steering: float | None = None,
            brake: float | None = None,
            silence: bool = False
    ) -> Self:
        """
        对车辆应用最基础的控制
        :param control: ``VehicleDirectControl`` 实例, 默认为 ``None``, 该实例可能被具名传参覆写
        :param throttle: 覆写 ``control`` 的加速踏板开度, 范围 ``[0,1]``, 默认 ``None`` 为不进行覆写
        :param steering: 覆写 ``control`` 的转向角, 范围 ``[-1,1]``, 正向向右, 默认 ``None`` 为不进行覆写
        :param brake: 覆写 ``control`` 的刹车踏板开度, 范围 ``[0,1]``, 默认 ``None`` 为不进行覆写
        :param silence: 静默模式, 为 ``True`` 时不再打印日志
        :return: ``self`` 以支持链式调用
        """
        # 整流输入
        if control is None:
            control = VehicleDirectControl()
        if isinstance(control, VehicleDirectControl):
            pass
        if isinstance(control, carla.VehicleControl):
            control = VehicleDirectControl.from_carla(control)

        # 处理覆写
        override_control = VehicleDirectControl(
            throttle=throttle if throttle else control.throttle,
            steering=steering if steering else control.steering,
            brake=brake if brake else control.brake,
            reverse=control.reverse,
        )

        carla_control = override_control.to_carla(disturbance=True)
        if not silence:
            self.logger.debug(f'Apply CARLA direct control: {CarlaUtils.short_direct_control(carla_control)}')
        self._actor.apply_control(carla_control)

    @CarlaActor.require_actor_alive
    def _apply_performance_calc_brake(
            self,
            brake: float,
            gain: float,
            steering: float = 0.0,
    ) -> Self:
        """
        对车辆应用经过外部性能计算的刹车
        :param brake: 刹车踏板开度, 取值范围 ``[0,1]``
        :param gain: 刹车增益, 与里面状态有关, 取值范围 ``[-1,1]``
        :return: ``self`` 以支持链式调用
        """
        vector = self.performance.calc_break_force_vector(
            velocity=self.actor.get_velocity(),
            mass=self.mass,
            brake=brake,
            gain=gain
        )

        # 清空可能影响刹车的行为
        self.actor.disable_constant_velocity()
        self.actor.set_autopilot(False)

        # 执行刹车
        self.actor.add_force(vector)
        self.logger.debug(f"Apply CARLA performance calculated brake, brake={brake}, gain={gain}")

        # CARLA 仍然响应转向
        self.apply_carla_direct_control(
            throttle=0,
            steering=steering,
            brake=0,
            silence=False
        )

        # 记录施加的力用于后续抵消解除
        self._added_force = vector

        return self

    @CarlaActor.require_actor_alive
    def apply_full_stop(self) -> Self:
        """
        对车辆执行全停指令
        :return: ``self`` 以支持链式调用
        """
        # 清空可能影响刹车的行为
        self.actor.disable_constant_velocity()
        self.actor.set_autopilot(False)

        # 执行 CARLA 的全力刹车
        self.apply_carla_direct_control(throttle=0.0, steer=0.0, brake=1.0, silence=True)

        # 清除车辆可能施加的力
        counteract_force_vector = carla.Vector3D(
            -1.0 * self._added_force.x,
            -1.0 * self._added_force.y,
            -1.0 * self._added_force.z
        )
        if isinstance(self._added_force, carla.Vector3D):
            self.actor.add_force(counteract_force_vector)
            self._added_force = None

        self.logger.debug('Apply full stop')
        return self

    @CarlaActor.require_actor_alive
    def apply_direct_control(
            self,
            control: VehicleDirectControl | carla.VehicleControl = None,
            *,
            throttle: float = 0.0,
            steering: float = 0.0,
            brake: float = 0.0,
            brake_gain: float = 0.0,
            silence: bool = True,
    ) -> Self:
        """
        经过 ``CarlaVehiclePerformance`` 修正的直接控制操作
        :param control: ``VehicleDirectControl`` 实例, 默认为 ``None``, 该实例可能被具名传参覆写
        :param throttle: 覆写 ``control`` 的加速踏板开度, 范围 ``[0,1]``, 默认 ``None`` 为不进行覆写
        :param steering: 覆写 ``control`` 的转向角, 范围 ``[-1,1]``, 正向向右, 默认 ``None`` 为不进行覆写
        :param brake: 覆写 ``control`` 的刹车踏板开度, 范围 ``[0,1]``, 默认 ``None`` 为不进行覆写
        :param brake_gain: 刹车增益系数 ``[-1,1]``
        :param silence: 静默模式, 为 ``True`` 时不再打印日志
        :return: ``self`` 以支持链式调用
        """
        # 清空影响控制的其他指令
        self.actor.set_autopilot(False)
        self.actor.disable_constant_velocity()
        if isinstance(self._added_force, carla.Vector3D):
            self.actor.add_force(self._added_force)
            self._added_force = None

        # 整流输入
        if control is None:
            control = VehicleDirectControl()
        if isinstance(control, VehicleDirectControl):
            pass
        if isinstance(control, carla.VehicleControl):
            control = VehicleDirectControl.from_carla(control)

        # 处理覆写
        override_control = VehicleDirectControl(
            throttle=throttle if throttle else control.throttle,
            steering=steering if steering else control.steering,
            brake=brake if brake else control.brake,
            reverse=control.reverse,
        )

        # 当减速时使用经过 CarlaVehiclePerformance 修正的刹车
        if override_control.brake > 0.0:
            self._apply_performance_calc_brake(brake, brake_gain, steering=steering)
            return self

        # 其他情况应用 CARLA 的原生控制
        self.apply_carla_direct_control(
            control,
            throttle=throttle,
            steering=steering,
            brake=0.0,
            silence=silence
        )
        return self

    @CarlaActor.require_actor_alive
    def apply_carla_autopilot(self, ref_speed:float) -> Self:
        """
        使用 CARLA 的 Waypoint 追踪自动驾驶
        :param ref_speed: 参考速度, 单位 KM/H
        :return: ``self`` 以支持链式调用
        """
        self.actor.set_autopilot(True)
        velocity_ms = ref_speed / 3.6
        self.actor.enable_constant_velocity(carla.Vector3D(x=velocity_ms, y=0.0, z=0.0))
        return self

    @CarlaActor.require_actor_alive
    def cancel_carla_autopilot(self) -> Self:
        """
        取消 CARLA 的 Waypoint 追踪自动驾驶. 注意此时车辆脱控
        :return: ``self`` 以支持链式调用
        """
        self.actor.set_autopilot(False)
        self.actor.disable_constant_velocity()
        return self

    @property
    def hook_after_collision(self) -> list[Callable]:
        return self._hook_after_collision