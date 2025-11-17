import threading
from typing import TYPE_CHECKING, List
from typing_extensions import Self

from shared.utils import Logging
from shared.scenarios import Factor

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


class Injector:
    """
    注入器, 用于在仿真中注入特定的场景因子
    """

    TICK_BLOCKER_TOKEN = 'injector'

    def __init__(self, context: 'CarlaContext', *factors: Factor):
        self.logger = Logging().get_logger('Injector')
        self._context = context
        self._factors: List[Factor] = list(factors)

        self._tick_blocker = threading.Event()

        self._post_init()

    def _post_init(self) -> Self:
        self._context.bind_tick_blocker(self.TICK_BLOCKER_TOKEN, self._tick_blocker)
        self.logger.info(f'Initialized with {len(self._factors)} factors')
        self.logger.debug(f'Factors: {", ".join([factor.NAME for factor in self._factors])}')
        return self

    def __enter__(self) -> Self:
        self.setup()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.teardown()
        return

    def setup(self) -> None:
        for factor in sorted(self._factors, key=lambda x: x.PRIORITY, reverse=True):
            if factor.PRIORITY:
                self._context.flag_ignore_dead_detector = True
            factor.setup()
            self._context.tick()
            self._context.flag_ignore_dead_detector = False

        self._context.hook_before_tick.append(self.tick)
        self.logger.info(f'All factors setup completed')

    def tick(self) -> None:
        self._tick_blocker.set()
        
        for factor in self._factors:
            factor.tick()
        
        self._tick_blocker.clear()

    def teardown(self) -> None:
        for factor in self._factors:
            factor.teardown()
        self.logger.info(f'All factors teardown completed')
        return self