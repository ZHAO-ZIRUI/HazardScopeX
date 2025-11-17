from abc import ABC
from shared.data import BaseData



class SimulatorInput(BaseData, ABC):
    """
    仿真器的输入数据
    
    该类仅提供与 SimulatorOutput 的对等抽象
    """
    pass