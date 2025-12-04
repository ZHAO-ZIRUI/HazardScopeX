from threading import Event


class CarlaTickBlocker(Event):
    """
    TICK 阻塞器的实现, 继承自 threading.Event, 用于阻塞 TICK 过程
    """

    def __init__(
        self, 
        name: str,
        *,
        auto_set_after_tick: bool = False
    ):
        super().__init__()
        self._name = name
        self._auto_set_after_tick = auto_set_after_tick
    
    def __str__(self) -> str:
        return f'CarlaTickBlocker(status={self.is_set()}, name={self._name}, auto_set_after_tick={self._auto_set_after_tick})'

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def name(self) -> str:
        return self._name

    @property
    def auto_set_after_tick(self) -> bool:
        return self._auto_set_after_tick
