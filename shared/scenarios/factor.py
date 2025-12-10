import carla
from logging import Logger
from typing import Callable, final
from typing_extensions import Self
from enum import Enum, auto

from shared.simulator import CarlaContext, CarlaActor, CarlaVehicle
from shared.utils import Logging, PostInitMeta

class Factor(metaclass=PostInitMeta):
    """
    Factor 基类, 用于定义因子的接口
    """

    # 因子名称
    NMAE = 'F_Abstract'

    # 因子优先级, 数值越小优先级越高
    PRIORITY: int = 0

    class FactorStage(Enum):
        """因子生命周期的阶段枚举类"""
        BRINGUP = auto()
        WAIT_FOR_TRIGGER = auto()
        TRIGGERED = auto()
        COMPLETED = auto()
        TEARDOWN = auto()

    def __init__(self, context: CarlaContext, vehicle_ego: CarlaVehicle):
        self._context = context
        self._vehicle_ego = vehicle_ego
        self._stage = self.FactorStage.BRINGUP
        self._logger = Logging().get_logger(self.NAME)
        self._factor_actors: dict[str, CarlaActor] = {}

        self._count_update_frames: int = 0

        self._hook_bringup: list[Callable[[Self], None]] = []
        self._hook_update: list[Callable[[Self], None]] = []
        self._hook_teardown: list[Callable[[Self], None]] = []

    def __post_init__(self) -> Self:
        """在此处绑定钩子"""
        return self

    @property
    def logger(self) -> Logger:
        return self._logger
    
    @property
    def stage(self) -> FactorStage:
        """因子当前阶段, 只读"""
        return self._stage

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

        # 销毁因子 Actor
        self.destroy_factor_actors()

        for hook in self._hook_teardown:
            hook()

    def destroy_factor_actors(self) -> None:
        for actor in self._factor_actors.values():
            actor.destroy()
        self._factor_actors.clear()

    @property
    def hook_bringup(self) -> list[Callable[[Self], None]]:
        return self._hook_bringup

    @property
    def hook_update(self) -> list[Callable[[Self], None]]:
        return self._hook_update

    @property
    def hook_teardown(self) -> list[Callable[[Self], None]]:
        return self._hook_teardown