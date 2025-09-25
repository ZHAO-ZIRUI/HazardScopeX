import colorsys
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from typing import Tuple, Iterator


class PgColor(BaseModel):
    """
    PgApp 的颜色定义类
    """
    model_config = ConfigDict(
        validate_assignment=True,
    )

    class ColorMode(Enum):
        """颜色模式枚举"""
        RGBA = "RGBA"
        HSVA = "HSVA"

    mode: "PgColor.ColorMode" = Field(default="PgColor.ColorMode.RGBA", description="Color mode")

    channel_1: int = Field(ge=0, le=255, description="Red or Hue channel")
    channel_2: int = Field(ge=0, le=255, description="Green or Saturation channel")
    channel_3: int = Field(ge=0, le=255, description="Blue or Value channel")
    channel_a: int = Field(ge=0, le=255, default=255, description="Alpha channel")

    def __init__(self, r: int, g: int, b: int, a: int = 255, mode: "PgColor.ColorMode" = None) -> None:
        if mode is None:
            mode = self.ColorMode.RGBA
        super().__init__(
            mode=mode,
            channel_1=r,
            channel_2=g,
            channel_3=b,
            channel_a=a,
        )

    def __call__(self, *args, **kwargs) -> Tuple[int, int, int, int]:
        return self.RGBA

    def __iter__(self) -> Iterator[int]:
        """
        使用序列协议提供直接访问
        """
        r, g, b, a = self.RGBA
        yield r
        yield g
        yield b
        yield a

    def __len__(self) -> int:
        return 4

    def __getitem__(self, index: int) -> int:
        return self.RGBA[index]

    @property
    def RGBA(self) -> Tuple[int, int, int, int]:
        if self.mode == self.ColorMode.RGBA:
            return self.channel_1, self.channel_2, self.channel_3, self.channel_a
        elif self.mode == self.ColorMode.HSVA:
            r, g, b = colorsys.hsv_to_rgb(self.channel_1 / 255.0, self.channel_2 / 255.0, self.channel_3 / 255.0)
            return int(r * 255), int(g * 255), int(b * 255), self.channel_a

    @property
    def RGB(self) -> Tuple[int, int, int]:
        r, g, b, _ = self.RGBA
        return r, g, b

    @property
    def HSVA(self) -> Tuple[int, int, int, int]:
        if self.mode == self.ColorMode.HSVA:
            return self.channel_1, self.channel_2, self.channel_3, self.channel_a
        elif self.mode == self.ColorMode.RGBA:
            h, s, v = colorsys.rgb_to_hsv(self.channel_1 / 255.0, self.channel_2 / 255.0, self.channel_3 / 255.0)
            return int(h * 255), int(s * 255), int(v * 255), self.channel_a

    @property
    def HSV(self) -> Tuple[int, int, int]:
        h, s, v, _ = self.HSVA
        return h, s, v