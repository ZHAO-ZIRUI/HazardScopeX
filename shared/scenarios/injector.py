import carla
from typing_extensions import Self, Unpack
from logging import Logger

from shared.simulator import CarlaContext, CarlaTickBlocker
from shared.utils import Logging, PostInitMeta
from . import Factor, Evaluator

class Injector(metaclass=PostInitMeta):
    """
    注入器, 用于在仿真中注入特定的因子
    """

    def __init__(self, context: CarlaContext, *factors: Factor):
        self._context = context
        self._logger = Logging().get_logger('Injector')
        self._factors: list[Factor] = list(factors)

        self._tick_blocker = CarlaTickBlocker(name='Injector')

    def __post_init__(self) -> Self:
        # 清理 factors 中为 None 的因子
        self._factors = [factor for factor in self._factors if factor is not None]

        # 按优先级排序因子
        self._factors.sort(key=lambda x: x.PRIORITY)

        # 绑定 TickBlocker
        self._context.tick_blockers.append(self._tick_blocker)

        # 打印日志
        self.logger.info(f'Initialized with {len(self._factors)} factors')
        self.logger.debug(f'Factors: {", ".join([factor.NAME for factor in self._factors])}')
        return self

    def __enter__(self) -> Self:
        self.bringup()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return

    @property
    def logger(self) -> Logger:
        return self._logger

    def bringup(self) -> None:
        self.logger.info(f'Bringing up {len(self._factors)} factors ...')

        for factor in self._factors:
            self.logger.info(f'Bringing up factor: {factor.NAME}')
            factor.bringup()

        # 进行一次 Tick, 防止 bringup 阶段遗漏
        self._context.wait_ticks(1, no_log=True)

        # 绑定 TICK 钩子
        self._context.hook_on_tick.append(self.tick)

        self.logger.info(f'All {len(self._factors)} factors brought up')

    def tick(self, _: carla.WorldSnapshot) -> None:
        print("Injector tick...")
        self._tick_blocker.set()

        for factor in self._factors:
            factor.update()

        self._tick_blocker.clear()
        return

    def teardown(self) -> None:
        self.logger.info(f'Tearing down {len(self._factors)} factors ...')
        self._context.tick_blockers.remove(self._tick_blocker)
        self._context.hook_on_tick.remove(self.tick)

        for factor in self._factors:
            factor.teardown()

        # 进行一次 Tick, 防止 teardown 阶段遗漏
        self._context.wait_ticks(1, no_log=True)

        self.logger.info(f'All {len(self._factors)} factors torn down')
        return

    def spin_until_finished(self, *factors: Unpack[Factor]) -> None:
        """持续运行仿真直到指定因子完成

        Args:
            *factors: 指定因子, 如果为空, 则运行直到所有因子完成

        Raises:
            SystemExit: 用户中断
        """
        if len(factors) == 0:
            factors = self._factors
        
        while any(factor.stage != Factor.FactorStage.COMPLETED for factor in factors):
            try:
                self._context.wait_ticks(1, no_log=True, raise_interrupted=True)
            except KeyboardInterrupt:
                self.logger.warning(f'Spin until finished interrupted by user')
                raise SystemExit(441)
        
        self.logger.info(f'All {len(factors)} factors finished')

    def spin_until_evaluator_threshold(self, evaluator: Evaluator, threshold: float) -> None:
        """持续运行仿真直到评估器结果达到指定阈值

        Args:
            evaluator (Evaluator): 评估器
            threshold (float): 阈值

        Raises:
            SystemExit: 用户中断
        """
        assert isinstance(threshold, float) and 0.0 <= threshold <= 1.0
        while evaluator.result is None or evaluator.result < threshold:
            try:
                self._context.wait_ticks(1, no_log=True, raise_interrupted=True)
            except KeyboardInterrupt:
                self.logger.warning(f'Spin until evaluator threshold interrupted by user')
                raise SystemExit(441)
        
        self.logger.info(f'Evaluator {evaluator.NAME} threshold reached')
        return
