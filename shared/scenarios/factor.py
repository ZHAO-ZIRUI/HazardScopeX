from abc import ABC, abstractmethod
from logging import Logger
from enum import Enum, auto

from shared.utils import Logging
from shared.simulator import CarlaContext, CarlaActor


class Factor(ABC):
    """
    场景因子, 用于在仿真中注入特定的场景因子

    因子定义包含以下内容:
    - strength: 归一化表示的因子强度, 在 __init__ 阶段中赋值, 范围为 0.0 到 1.0, 默认为 1.0
    - PRIORITY: 因子优先级, 用于在多个因子联合注入时, 控制因子的执行顺序, 范围为整型区间, 越小越先执行
    - result:   归一化表示的因子执行评估结果, 范围为 0.0 到 1.0, 在因子未处于 FINISHED 状态时为 -1.0

    因子的生命周期如下:
    - HANGUP         # 挂起, 因子尚未开始执行
    - bringup()      # 初始化, 用于生成场景实例
    - warmup() x N   # 预热, 用于启动车辆或车流等, 会执行多帧, 直到因子处于 UPDATE 状态
    - update() x N   # 帧更新, 用于更新实例状态或进行触发, 会执行多帧
    - teardown() x N # 销毁, 用于销毁场景实例, 会执行多帧, 直到因子处于 FINISHED 状态
    - FINISHED       # 完成, 用于标记因子生命周期结束

    因子的命名请修改类属性 NAME, 遵循以下命名规则:
    - 以 F_ 开始, 使用 PascalCase(大驼峰) 命名
    - 第二个单词表示因子的类型
        - Env: 环境因素, 包括天气, 时间, 光照等
        - Traffic: 车流因素, 与主要事件关系不大的车流因素
        - Sensor: 传感器因素, 包括对相机, 激光雷达, 毫米波雷达等传感器的数据处理
        - Case: 交互因素, 具体的交互场景
    - 第三个至以后的单词表示因子的具体说明
    - 示例:
        - F_EnvHeavyRain
        - F_TrafficLargeVehilces
        - F_SensorCamLoss
        - F_CaseForceCutin
    """

    NAME = 'F_BaseFactor'
    PRIORITY = 0

    class FactorStatus(Enum):
        HANGUP = auto()
        BRINGUP = auto()
        WARMUP = auto()
        UPDATE = auto()
        TEARDOWN = auto()
        FINISHED = auto()

    def __init__(self, context: CarlaContext, strength: float = 1.0):
        self._logger = Logging().get_logger(self.NAME)
        self._context = context
        self._status = self.FactorStatus.HANGUP
        self._strength = strength
        self._result: float = -1.0
        self._actors: dict[str, CarlaActor] = {}
        
        self._is_warmup_completed = False
        self._is_teardown_completed = False
        self._is_update_ended = False

    @property
    def logger(self) -> Logger:
        return self._logger

    @property
    def status(self) -> FactorStatus:
        return self._status

    @property
    def is_update_ended(self) -> bool:
        """因子更新是否结束, 用于标记因子更新周期的结束, 只读"""
        return self._is_update_ended

    @property
    def is_warmup_completed(self) -> bool:
        """因子预热是否完成, 只读"""
        return self._is_warmup_completed

    @property
    def is_teardown_completed(self) -> bool:
        """因子销毁是否完成, 只读"""
        return self._is_teardown_completed

    @property
    def strength(self) -> float:
        """因子强度, 用于控制因子的强度, 范围为 0.0 到 1.0, 默认为 1.0, 只读"""
        return self._strength

    @status.setter
    def status(self, value: FactorStatus):
        before = self._status
        self._status = value
        self.logger.debug(f'Status changed: {before.name} -> {value.name}')
        return self

    @property
    def result(self) -> float:
        """因子执行评估结果, 范围为 0.0 到 1.0, 在因子未处于 FINISHED 状态时, 结果为 -1.0, 只读"""
        return self._result

    def bringup(self) -> None:
        """因子要件的初始化逻辑, 用于生成场景实例, 只会执行一次"""
        self.status = self.FactorStatus.BRINGUP
        return self

    @abstractmethod
    def warmup(self) -> None:
        """因子要件的预热逻辑, 用于启动车辆或车流等, 会执行多帧
        
        该方法必须被子类实现, 并手动设置 self._is_warmup_completed 为 True 以标记预热完成
        """
        raise NotImplementedError
        if self._is_warmup_completed:
            return
        self.status = self.FactorStatus.WARMUP
        return self

    @abstractmethod
    def update(self) -> None:
        """因子要件的更新逻辑, 用于更新实例状态或进行触发, 会执行多帧
        
        该方法必须被子类实现, 并手动设置 self._is_update_ended 为 True 以标记更新结束
        """
        if self._is_update_ended:
            return
        self.status = self.FactorStatus.UPDATE
        self._result = self._evaluate()
        return self

    def teardown(self) -> None:
        """因子要件的销毁逻辑, 用于销毁场景实例, 只会执行一次"""

        self.status = self.FactorStatus.TEARDOWN

        # 销毁所有场景 Actor 实例
        for actor in self._actors.values():
            actor.destroy()
        self._actors.clear()

        self._is_teardown_completed = True
        self.status = self.FactorStatus.FINISHED
        return self

    def _evaluate(self) -> float:
        """因子执行评估逻辑, 用于评估因子的执行结果"""
        return self._result