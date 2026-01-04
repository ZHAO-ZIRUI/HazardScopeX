from abc import ABC, abstractmethod
from logging import Logger
from typing_extensions import Self

from shared.simulator import CarlaContext
from shared.utils import Logging
from shared.simulator import CarlaActor

import carla
from .eval import EvalManager, CarlaEvaluatorAdapter

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
    
class ConstantRiskEvaluator(Evaluator):
    def __init__(self, context: CarlaContext):
        super().__init__(context)
        self._eval_manager = None

    @property
    def frame(self):
        return self._context.world.get_snapshot().frame

    def bind_evaluate_actor(self, name: str, actor: CarlaActor) -> Self:
        return super().bind_evaluate_actor(name, actor)

    def evaluate(self) -> float:
        return 0.0

    
class SimpleRiskEvaluator(Evaluator):
    """简单的风险评估器，需要在 context 绑定前完成绑定
    """

    def __init__(self, context: CarlaContext):
        super().__init__(context)
        self._eval_manager = None

    @property
    def frame(self):
        return self._context.world.get_snapshot().frame

    def bind_evaluate_actor(self, name: str, actor: CarlaActor) -> Self:
        assert isinstance(actor.actor, carla.Vehicle), "Actor binding must be a vehicle!"
        self._eval_manager = EvalManager(CarlaEvaluatorAdapter(self._context), actor.actor)
        
        # 注册风险计算器
        fixed_delta_time = self._context.fixed_delta_seconds
        self._eval_manager.register_risk_computer('ttc', fixed_delta_time=fixed_delta_time)
        self._eval_manager.register_risk_computer('dst', fixed_delta_time=fixed_delta_time)
        self._eval_manager.register_risk_computer('rla', fixed_delta_time=fixed_delta_time)
        self._eval_manager.register_risk_computer('cri', fixed_delta_time=fixed_delta_time)
        self._eval_manager.register_risk_computer('dce', fixed_delta_time=fixed_delta_time)
        return super().bind_evaluate_actor(name, actor)

    def evaluate(self) -> float:
        if self._eval_manager is None:
            raise RuntimeError("You should bind a vehicle before evaluation!")
        self._eval_manager.run_evaluation_in_frame(self.frame)
        self._result = self._eval_manager.normalized_risk_value
        for k, v in self._eval_manager.risk_value.items():
            self._logger.info(f"指标 {k}: {v}")
        self._logger.info(f"执行评估在 {self.frame} 帧，评估结果为 {self._result}.")
        return self._eval_manager.normalized_risk_value