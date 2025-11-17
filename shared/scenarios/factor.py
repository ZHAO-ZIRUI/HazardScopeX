from abc import ABC
from typing import TYPE_CHECKING

from shared.utils import Logging

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


class Factor(ABC):
    """
    场景因子, 用于在仿真中注入特定的场景因子
    """
    NAME = 'Factor'
    PRIORITY = False    # 当设置地图时, 设置PRIORITY为True

    def __init__(self, context: 'CarlaContext'):
        self.logger = Logging().get_logger(self.NAME)
        self._context = context

    def setup(self) -> None:
        """因子要件的初始化逻辑
        """
        self.logger.info(f'Setup completed')
        return self

    def tick(self) -> None:
        """在每个 tick 中执行因子逻辑
        """
        return

    def teardown(self) -> None:
        """因子要件的销毁逻辑
        """
        self.logger.info(f'Teardown completed')
        return self