import time
from typing import Any, Callable


class LogUtils:
    _last_times: dict[Any, float] = {}

    @staticmethod
    def interval(
        interval_seconds: float,
        *,
        token: Any,
        log_call: Callable[..., None], 
        content: str
    ) -> None:
        now = time.time()
        last = LogUtils._last_times.get(token, 0.0)
        if (now - last) >= interval_seconds:
            LogUtils._last_times[token] = now
            log_call(content)


