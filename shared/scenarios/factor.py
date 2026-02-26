import carla
import random
from logging import Logger
from typing import Any, Callable, final, TypeVar
from typing_extensions import Self
from enum import Enum, auto

from shared.simulator import CarlaContext, CarlaActor, CarlaVehicle, CarlaBlueprints
from shared.utils import Logging, PostInitMeta
from shared.define import FactorLevel

class Factor(metaclass=PostInitMeta):
    """
    Factor 基类, 用于定义可以注入的因子
    """

    T_LOCATION = TypeVar('T_LOCATION', bound=carla.Location | carla.Transform | int | list[int] | list[carla.Transform] | list[carla.Location])

    # 键定义, 用于索引
    K_VEHICLE_EGO = 'VEHICLE_EGO'
    K_VEHICLE_ACT = 'VEHICLE_ACT'
    K_VEHICLE_NPC = 'VEHICLE_NPC'
    K_VEHICLE_STOP = 'VEHICLE_STOP'
    K_OBSTACLE = 'OBSTACLE'
    K_PEDESTRIAN = 'PEDESTRIAN'

    # 因子名称
    NAME = 'F_Abstract'

    # 因子优先级, 数值越小优先级越高
    PRIORITY: int = 0

    # 影射关系
    M_WORLD_LOCATION: dict[str, dict[str, T_LOCATION]] = {}
    M_LEVEL_VALUE: dict[FactorLevel, Any] = {}

    class FactorStage(Enum):
        """因子生命周期的阶段枚举类"""
        BRINGUP = auto()             # 准备阶段, 用于生成因子所需的 Actor 等操作, 对应 hook_bringup 钩子, 只会执行一次
        WAIT_FOR_TRIGGER = auto()    # 等待触发阶段, 因子开始 update() 后首先进入该阶段, 会在每次 tick() 时执行 hook_update 钩子
        TRIGGERED = auto()           # 触发阶段, 处于 update() 阶段, 需要手动设置 self.stage 进入该阶段
        COMPLETED = auto()           # 完成阶段, 处于 update() 阶段, 用于标记因子完成所有操作或达成特定条件, 需要手动设置 self.stage 进入该阶段
        TEARDOWN = auto()            # 销毁阶段, 用于销毁因子所需的 Actor 等操作, 对应 hook_teardown 钩子, 只会执行一次

    def __init__(
        self,
        context: CarlaContext,
        ego_vehicle: CarlaVehicle,
        level: FactorLevel = FactorLevel.HIGH,
        *,
        ignore_factor_ego_control: bool = False,
        keepalive_after_trigger: float = 5.0,
    ):
        self._context = context
        self._vehicle_ego = ego_vehicle
        self._level = level
        self._stage = self.FactorStage.BRINGUP
        self._logger = Logging().get_logger(self.NAME)
        self._factor_actors: dict[str, CarlaActor] = {}

        self._count_update_frames: int = 0
        self._keepalive_begin_frames = 0
        self._keepalive_after_triggered_frames = keepalive_after_trigger * self._context.fps

        self._flag_ignore_factor_ego_control = ignore_factor_ego_control

        self._hook_bringup: list[Callable[[Self], None]] = []
        self._hook_update: list[Callable[[Self], None]] = []
        self._hook_teardown: list[Callable[[Self], None]] = []

    def __post_init__(self) -> Self:
        """在此处绑定钩子"""
        return self

    @property
    def ego(self) -> CarlaVehicle:
        return self._vehicle_ego

    @property
    def logger(self) -> Logger:
        return self._logger
    
    @property
    def stage(self) -> FactorStage:
        """因子当前阶段, 只读"""
        return self._stage

    @property
    def level(self) -> FactorLevel:
        return self._level

    @stage.setter
    def stage(self, value: FactorStage):
        before = self._stage
        self._stage = value
        if before != value:
            self.logger.debug(f'Stage changed: {before.name} -> {value.name}')
        return self

    @final
    def bringup(self) -> None:
        for hook in self._hook_bringup:
            hook()

        # 状态转移 BRINGUP -> WAIT_FOR_TRIGGER
        self.stage = self.FactorStage.WAIT_FOR_TRIGGER

    @final
    def update(self) -> None:
        self._count_update_frames += 1
        for hook in self._hook_update:
            hook()

    @final
    def teardown(self) -> None:
        # 状态转移 Any -> TEARDOWN
        self.stage = self.FactorStage.TEARDOWN

        self.hook_bringup.clear()
        self.hook_update.clear()

        # 销毁因子 Actor
        self.destroy_factor_actors()

        for hook in self._hook_teardown:
            hook()

    def destroy_factor_actors(self) -> None:
        for actor in self._factor_actors.values():
            actor.destroy()
        self._factor_actors.clear()

    def move_ego_vehicle_to_init_tf(self) -> None:
        if self._flag_ignore_factor_ego_control:
            return

        spawn_point_mapping = self.M_WORLD_LOCATION[self._context.map_name]
        tf_ego = self._context.spawn_points[spawn_point_mapping[self.K_EGO]]
        self._vehicle_ego.actor.set_transform(tf_ego)
        return self

    def create_npc_vehicles(self) -> None:
        spawn_point_mapping = self.M_WORLD_LOCATION[self._context.map_name]
        bps = CarlaBlueprints.vehicles('car')
        for npc_sp_idx in spawn_point_mapping[self.K_NPC_VEHICLE]:
            npc_tf = self._context.spawn_points[npc_sp_idx]
            npc = self._context.actors.create_vehicle(
                bp=random.choice(bps),
                tf=npc_tf,
                name=f'{self.K_NPC_VEHICLE}_{npc_sp_idx}',
            )
            self._factor_actors[f'{self.K_NPC_VEHICLE}_{npc_sp_idx}'] = npc

    def create_stop_vehicles(self) -> None:
        spawn_point_mapping = self.M_WORLD_LOCATION[self._context.map_name]
        bps = CarlaBlueprints.vehicles('car')
        for stop_sp_idx in spawn_point_mapping[self.K_STOP_VEHICLE]:
            stop_tf = self._context.spawn_points[stop_sp_idx]
            stop = self._context.actors.create_vehicle(
                bp=random.choice(bps),
                tf=stop_tf,
                name=f'{self.K_STOP_VEHICLE}_{stop_sp_idx}',
            )
            self._factor_actors[f'{self.K_STOP_VEHICLE}_{stop_sp_idx}'] = stop

    def apply_npc_vehicles_carla_autopilot(self) -> None:
        for actor in self._factor_actors.values():
            if isinstance(actor, CarlaVehicle):
                actor.set_carla_autopilot(enable=True)
                self._context.traffic.auto_lane_change(actor.actor, False)

    def keepalive_after_triggered(self) -> None:
        if self.stage != self.FactorStage.TRIGGERED:
            return
        if self._keepalive_begin_frames == 0:
            self.logger.info(f'Keepalive after triggered begin at frame {self._count_update_frames}, will keep alive for {self._keepalive_after_triggered_frames} frames')
            self._keepalive_begin_frames = self._count_update_frames
        if self._count_update_frames - self._keepalive_begin_frames >= self._keepalive_after_triggered_frames:
            self.stage = self.FactorStage.COMPLETED
        return self

    def spawn_all_factor_actors(self) -> None:
        self._context.actors.spawn_all(*self._factor_actors.values())
        self._context.actors.wait_stable()
        return self

    def update_npc_vehicles_auto_lights(self) -> None:
        for name, actor in self._factor_actors.items():
            if isinstance(actor, CarlaVehicle) and name.startswith(self.K_VEHICLE_NPC) and actor.is_alive:
                self._context.traffic.update_vehicle_lights(actor.actor, True)
        return self

    @property
    def hook_bringup(self) -> list[Callable[[Self], None]]:
        return self._hook_bringup

    @property
    def hook_update(self) -> list[Callable[[Self], None]]:
        return self._hook_update

    @property
    def hook_teardown(self) -> list[Callable[[Self], None]]:
        return self._hook_teardown