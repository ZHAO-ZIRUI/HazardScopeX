import time
from typing_extensions import Self
from logging import Logger

from shared.utils import Logging, PostInitMeta
from shared.scenarios import Factor
from shared.simulator import CarlaContext, CarlaTickBlocker


class Injector(metaclass=PostInitMeta):
    """
    注入器, 用于在仿真中注入特定的场景因子
    """

    TICK_BLOCKER_TOKEN = 'Injector'

    def __init__(self, context: CarlaContext, flag_auto_tick: bool = True, *factors: Factor | None):
        self._logger = Logging().get_logger('Injector')
        self._context = context
        self._factors: list[Factor | None] = list(factors)
        self._flag_auto_tick = flag_auto_tick

        self._status = Factor.FactorStatus.HANGUP

        self._tick_blocker = CarlaTickBlocker(name=self.TICK_BLOCKER_TOKEN)

    def __post_init__(self) -> Self:
        # 清理 factors 中为 None 的因子
        self._factors = [factor for factor in self._factors if factor is not None]

        # 绑定 TickBlocker
        self._context.tick_blockers.append(self._tick_blocker)

        # 打印日志
        self.logger.info(f'Initialized with {len(self._factors)} factors')
        self.logger.debug(f'Factors: {", ".join([factor.NAME for factor in self._factors])}')
        return self

    def __enter__(self) -> Self:
        self.setup()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.teardown()
        return

    @property
    def logger(self) -> Logger:
        return self._logger

    def setup(self) -> None:
        for factor in sorted(self._factors, key=lambda x: x.PRIORITY):
            factor.bringup()
            self._context.tick()

        # 绑定 TICK 钩子
        if self._flag_auto_tick:
            self._context.hook_on_tick.append(self.tick)

        self._status = Factor.FactorStatus.BRINGUP
        self.logger.info(f'All factors setup completed')

    def tick(self) -> None:
        self._tick_blocker.set()

        if self._status == Factor.FactorStatus.BRINGUP:
            self._status = Factor.FactorStatus.WARMUP
        
        # WARMUP 阶段
        if self._status == Factor.FactorStatus.WARMUP:
            if all(factor.is_warmup_completed for factor in self._factors):
                self._status = Factor.FactorStatus.UPDATE
                self.logger.info(f'All factors warmup completed, begin to update ...')
                self._tick_blocker.clear()
                return
            else:
                for factor in self._factors:
                    factor.warmup()
        
        # UPDATE 阶段
        if self._status == Factor.FactorStatus.UPDATE:
            if any(factor.is_update_ended for factor in self._factors):
                self._status = Factor.FactorStatus.TEARDOWN
                updated_ended_factor_list = [factor for factor in self._factors if factor.is_update_ended]
                self.logger.info(f'Factors update ended: {", ".join([factor.NAME for factor in updated_ended_factor_list])}')
                self.logger.info(f'Found factors update ended, begin to teardown ...')
                self._tick_blocker.clear()
                return
            else:
                for factor in self._factors:
                    factor.update()
        
        # TEARDOWN 阶段
        if self._status == Factor.FactorStatus.TEARDOWN:
            if all(factor.is_teardown_completed for factor in self._factors):
                self.logger.info(f'All factors teardown completed')
                self._status = Factor.FactorStatus.FINISHED
                self._tick_blocker.clear()
                return
            else:
                for factor in self._factors:
                    factor.teardown()
        
        self._tick_blocker.clear()

    def teardown(self) -> None:
        # 如果调用该方法时, 因子尚未完成, 则跳过当前步骤直接执行 TEARDOWN 阶段
        while self._status != Factor.FactorStatus.FINISHED:
            # 如果处于挂起阶段, 则直接设置为 FINISHED 状态
            if self._status == Factor.FactorStatus.HANGUP:
                self._status = Factor.FactorStatus.FINISHED
                break
            # 否则, 设置为 TEARDOWN 阶段, 并执行 TICK
            self._status = Factor.FactorStatus.TEARDOWN
            self.tick()

        # 移除 TICK 钩子
        if self._flag_auto_tick:
            self._context.hook_on_tick.remove(self.tick)

        return self

    def spin_until_finished(self) -> None:
        while self._status != Factor.FactorStatus.FINISHED:
            self._context.tick()
            try:
                time.sleep(self._context.calc_tick_wait_time())
            except KeyboardInterrupt:
                self.logger.warning('Spin interrupted by user')
                raise SystemExit(401)
        return