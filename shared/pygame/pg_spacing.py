from pydantic import BaseModel, Field, ConfigDict, model_validator


class PgSpacing(BaseModel):
    """PgApp 的间距定义"""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    value: int | None = Field(default=None, ge=0)
    x: int | None = Field(default=None, ge=0)
    y: int | None = Field(default=None, ge=0)
    top: int | None = Field(default=None, ge=0)
    bottom: int | None = Field(default=None, ge=0)
    left: int | None = Field(default=None, ge=0)
    right: int | None = Field(default=None, ge=0)

    def __call__(self) -> tuple[int, int, int, int]:
        return self.top, self.bottom, self.left, self.right

    def __iter__(self):
        yield self.top
        yield self.bottom
        yield self.left
        yield self.right

    @model_validator(mode='after')
    def _resolve_spacing(self):
        """
        解析间距值, 优先级: top/bottom/left/right > x/y > value > 0
        """
        # 先处理 x/y（优先级高于 value）
        if self.x is not None:
            if self.left is None:
                self.left = self.x
            if self.right is None:
                self.right = self.x

        if self.y is not None:
            if self.top is None:
                self.top = self.y
            if self.bottom is None:
                self.bottom = self.y

        # 然后处理 value（应用到所有未设置的方向）
        if self.value is not None:
            if self.top is None:
                self.top = self.value
            if self.bottom is None:
                self.bottom = self.value
            if self.left is None:
                self.left = self.value
            if self.right is None:
                self.right = self.value

        # 最后确保所有值都有默认值（0）
        if self.top is None:
            self.top = 0
        if self.bottom is None:
            self.bottom = 0
        if self.left is None:
            self.left = 0
        if self.right is None:
            self.right = 0

        return self
