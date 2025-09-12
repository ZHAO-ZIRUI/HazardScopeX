from pydantic import Field

from core.pygame import PgText


class PgTextStatic(PgText):
    """
    显示静态文本的文本框, 继承自 PgText, 并提供了简化的接口.
    """
    width: int = Field(default=1, ge=0)
    overflow_x: PgText.Overflow = Field(default=PgText.Overflow.AUTO)
    padding_x: int = Field(default=2, ge=0)
    margin_y: int = Field(default=2, ge=0)