from abc import ABC, abstractmethod
from logging import Logger
from typing_extensions import Self

from shared.simulator import CarlaContext
from shared.utils import Logging
from shared.simulator import CarlaActor


class Evaluator(ABC):
    """
    评估器, 用于评估因子的执行结果
    """

    def __init__(self, context: CarlaContext):
        self._logger = Logging().get_logger('Evaluator')
        self._context = context
        self._result: float | None = None
        self._evaluate_actors: dict[str, CarlaActor] = {}

    @property
    def logger(self) -> Logger:
        return self._logger

    @property
    def result(self) -> float | None:
        return self._result

    def bind_evaluate_actor(self, name: str, actor: CarlaActor) -> Self:
        self._evaluate_actors[name] = actor
        return self

    @abstractmethod
    def evaluate(self) -> float:
        raise NotImplementedError