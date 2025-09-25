from abc import ABC
from typing import Any, Tuple
from pydantic import Field

from core.pygame import PgWidget


class PgProgressBar(PgWidget, ABC):

    value: float = Field(ge=0, le=1, default=0)
    vertical: bool = False
    reverse: bool = False
    content_color: Tuple[int, int, int, int] = Field(default=(0, 0, 0))

    def model_post_init(self, context: Any, /) -> None:
        self.padding = 2

    def update(self, value: float):
        self.value = value
