from pydantic import BaseModel, Field, ConfigDict

class PgPos(BaseModel):
    """PgApp 的位置定义"""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    x: int = Field(default=0, ge=0)
    y: int = Field(default=0, ge=0)

    def __iter__(self):
        yield self.x
        yield self.y