import textwrap
import pygame
import uuid
from pydantic import PrivateAttr, Field
from typing import Any, Tuple

from core.pygame import *


class VehicleBackgroundWidget(PgWidget):

    line_width: int = Field(default=2)
    line_color: Tuple[int, int, int, int] | None = Field(default=None)

    body_radius: int = Field(default=24)

    wheel_width_ratio: float = Field(default=0.3, ge=0, le=0.5, description="Ratio relative to component width")
    wheel_height_ratio: float = Field(default=0.25, ge=0, le=0.5, description="Ratio relative to component height")
    wheel_radius: int = Field(default=8, ge=0)
    wheel_front_ratio: float = Field(default=0.5, ge=0, le=1)
    wheel_back_ratio: float = Field(default=0.5, ge=0, le=1)

    center_mark: bool = Field(default=True)
    center_radius: int = Field(default=8, ge=0)

    head_mark: bool = Field(default=True)
    head_radius: int = Field(default=8, ge=0)

    _wheel_width: int = PrivateAttr(default=0)
    _wheel_height: int = PrivateAttr(default=0)
    _wheel_front_offset: int = PrivateAttr(default=0)
    _wheel_back_offset: int = PrivateAttr(default=0)

    def model_post_init(self, context: Any, /) -> None:
        # 计算颜色
        if self.line_color is None:
            self.line_color = self.palette.PRIMARY.RGBA

        # 根据比例计算车轮参数
        self._wheel_width = int(self.wheel_width_ratio * self.width)
        self._wheel_height = int(self.wheel_height_ratio * self.height)
        self._wheel_front_offset = int(self.wheel_front_ratio * self.width // 2)
        self._wheel_back_offset = int(self.wheel_back_ratio * self.width // 2)

    def _draw_content(self):
        # 车身
        pygame.draw.rect(
            self.surface,
            self.line_color,
            (self.x, self.y, self.width, self.height),
            self.line_width,
            border_radius=self.body_radius,
        )

        # 车轮
        wheel_position = [
            (   # FL
                self.x,
                self.center_y - self._wheel_front_offset - self._wheel_height
            ),
            (   # RL
                self.x,
                self.center_y + self._wheel_back_offset
            ),
            (   # FR
                self.x + self.width - self._wheel_width,
                self.center_y - self._wheel_front_offset - self._wheel_height
            ),
            (   # RR
                self.x + self.width - self._wheel_width,
                self.center_y + self._wheel_back_offset
            )

        ]
        for wheel_x, wheel_y in wheel_position:
            pygame.draw.rect(
                self.surface,
                self.line_color,
                (wheel_x, wheel_y, self._wheel_width, self._wheel_height),
                self.line_width,
                border_radius=self.wheel_radius
            )

        # 几何中心标志, Center Mark
        if self.center_mark:
            pygame.draw.line(
                self.surface,
                self.line_color,
                (self.center_x - self.center_radius, self.center_y),
                (self.center_x +  self.center_radius, self.center_y),
                self.line_width
            )
            pygame.draw.line(
                self.surface,
                self.line_color,
                (self.center_x, self.center_y -  self.center_radius),
                (self.center_x, self.center_y +  self.center_radius), self.line_width
            )

        # 正方形标志, Head Mark
        if self.head_mark:
            pygame.draw.polygon(
                self.surface,
                self.line_color,
                [
                    (self.center_x, self.center_y - self.height // 2 - 24),
                    (self.center_x - 8, self.center_y - self.height // 2 - 8),
                    (self.center_x + 8, self.center_y - self.height // 2 - 8)
                ]
            )

class HelpModelBox(PgContainer):

    def model_post_init(self, context: Any, /) -> None:
        super().model_post_init(context)

        self.border = 2
        self.margin = 8
        self.margin_bg_color = self.palette.LIGHT_GRAY.RGBA
        self.border_color = self.palette.BLACK.RGBA

        header = PgTextStatic(
            surface=self.surface,
            position=(self.content_rect[0], self.content_rect[1]),
            bold=True,
            width=self.content_rect[2],
            height=24,
            text='[ HELPS ]',
            text_color=self.palette.BLACK.RGBA,
            align_x=PgText.Align.CENTER,
        )
        content_text = f"""
        EXTERNAL KEYBOARD VEHICLE CONTROL
    
        CONTROLS:
         
         - W/↑:    Accelerator Pedal
         - S/↓:    Brake Padel
         - A/←:    Turn Left
         - D/→:    Turn Right
         - +:      Forward Gear
         - -:      Reverse Gear
         - SPACE:  Reset Throttle and Brake
         - H:      Show/Hide Helps
         
         - ESC:    Exit Program
        """
        content = PgTextStatic(
            surface=self.surface,
            position=(self.content_rect[0], self.content_rect[1] + 24),
            bold=True,
            width=self.content_rect[2],
            height=24 * 14,
            text=textwrap.dedent(content_text).strip('\n'),
            text_color=self.palette.BLACK.RGBA,
            align_y=PgText.Align.BEGIN,
        )

        self.add_widget(header)
        self.add_widget(content)


class KeyboardControl(PgApp):

    show_grid_debug: bool = Field(default=False)

    W_GRID: str = uuid.uuid4().hex
    W_VEHICLE_BACKGROUND:str = uuid.uuid4().hex
    W_HEADER_TEXT: str = uuid.uuid4().hex
    W_FOOTER_TEXT: str = uuid.uuid4().hex
    W_THROTTLE_TEXT: str = uuid.uuid4().hex
    W_THROTTLE_BAR: str = uuid.uuid4().hex
    W_THROTTLE_VAL: str = uuid.uuid4().hex
    W_BRAKE_TEXT: str = uuid.uuid4().hex
    W_BRAKE_BAR: str = uuid.uuid4().hex
    W_BRAKE_VAL: str = uuid.uuid4().hex
    W_STEERING_TEXT: str = uuid.uuid4().hex
    W_STEERING_BAR: str = uuid.uuid4().hex
    W_STEERING_VAL: str = uuid.uuid4().hex
    W_CONNECTION_TEXT: str = uuid.uuid4().hex
    W_CONNECTION_VAL: str = uuid.uuid4().hex
    W_GARE_TEXT: str = uuid.uuid4().hex
    W_GARE_VAL: str = uuid.uuid4().hex
    W_MODE_TEXT: str = uuid.uuid4().hex
    W_MODE_VAL: str = uuid.uuid4().hex
    W_KEY_PRESSED_TEXT: str = uuid.uuid4().hex
    W_KEY_PRESSED_VAL: str = uuid.uuid4().hex
    W_HELP_MODEL: str = uuid.uuid4().hex

    def _init_widgets(self):
        grid = PgGrid(
            surface=self._screen,
            position=(0, 0),
            width=self.width,
            height=self.height,
        )
        self.widgets[self.W_GRID] = grid

        # 背景车辆
        w_vehicle_background_width = 100
        w_vehicle_background_height = 200
        self.widgets[self.W_VEHICLE_BACKGROUND] = VehicleBackgroundWidget(
            surface=self._screen,
            position=(
                self.center_x - w_vehicle_background_width // 2,
                self.center_y - w_vehicle_background_height // 2 - grid.row_interval * 2
            ),
            width=w_vehicle_background_width,
            height=w_vehicle_background_height,
        )

        # 顶部文本
        self.widgets[self.W_HEADER_TEXT] = PgText(
            surface=self._screen,
            position=(0, 0),
            width=self.width,
            height=grid.row_interval,
            text="[ KEYBOARD CONTROL ]",
            text_color=self.palette.INFO.RGBA,
            bold=True,
            align_x=PgText.Align.CENTER,
        )

        # 底部文本
        self.widgets[self.W_FOOTER_TEXT] = PgTextStatic(
            surface=self._screen,
            position=(0, self.height - grid.row_interval),
            width=self.width,
            height=grid.row_interval,
            text="Press <H> to show/hide helps.",
            text_color=self.palette.BLACK.RGBA,
            margin_bg_color=self.palette.LIGHT_GRAY.RGBA,
            bold=True,
            padding_x=8,
        )

        # 帮助信息
        self.widgets[self.W_HELP_MODEL] = HelpModelBox(
            surface=self._screen,
            position=grid.get_position(4, 8),
            width=grid.col_interval * 17,
            height=grid.row_interval * 16,
            show=False,
            z_index=100,
        )

        # 油门刹车转向
        self.widgets[self.W_THROTTLE_TEXT] = PgText(
            surface=self._screen,
            position=grid.get_position(19, 12),
            width=grid.col_interval * 4,
            height=grid.row_interval,
            text="THROTTLE:",
            text_color=self.palette.TEXT_PRIMARY.RGBA,
            bold=True,
        )
        self.widgets[self.W_BRAKE_TEXT] = PgText(
            surface=self._screen,
            position=grid.get_position(20, 12),
            width=grid.col_interval * 4,
            height=grid.row_interval,
            text="BRAKE:",
            text_color=self.palette.TEXT_PRIMARY.RGBA,
            bold=True,
        )
        self.widgets[self.W_STEERING_TEXT] = PgText(
            surface=self._screen,
            position=grid.get_position(21, 12),
            width=grid.col_interval * 4,
            height=grid.row_interval,
            text="STEERING:",
            text_color=self.palette.TEXT_PRIMARY.RGBA,
            bold=True,
        )

        self.widgets[self.W_THROTTLE_VAL] = PgText(
            surface=self._screen,
            position=grid.get_position(19, 16),
            width=grid.col_interval * 2,
            height=grid.row_interval,
            text="0.00",
            text_color=self.palette.SUCCESS.RGBA,
            bold=True,
            align_x=PgText.Align.END,
        )
        self.widgets[self.W_BRAKE_VAL] = PgText(
            surface=self._screen,
            position=grid.get_position(20, 16),
            width=grid.col_interval * 2,
            height=grid.row_interval,
            text="0.00",
            text_color=self.palette.SUCCESS.RGBA,
            bold=True,
            align_x=PgText.Align.END,
        )
        self.widgets[self.W_STEERING_VAL] = PgText(
            surface=self._screen,
            position=grid.get_position(21, 16),
            width=grid.col_interval * 2,
            height=grid.row_interval,
            text="0.00",
            text_color=self.palette.SUCCESS.RGBA,
            bold=True,
            align_x=PgText.Align.END,
        )

        self.widgets[self.W_THROTTLE_BAR] = PgProgressBarLinear(
            surface=self._screen,
            position=grid.get_position(19, 19),
            width=grid.col_interval * 13,
            height=grid.row_interval,
            border=2,
            margin_y=2,
            border_color=self.palette.TEXT_PRIMARY.RGBA,
        )
        self.widgets[self.W_BRAKE_BAR] = PgProgressBarLinear(
            surface=self._screen,
            position=grid.get_position(20, 19),
            width=grid.col_interval * 13,
            height=grid.row_interval,
            border=2,
            margin_y=2,
            border_color=self.palette.TEXT_PRIMARY.RGBA,
        )
        self.widgets[self.W_STEERING_BAR] = PgProgressBarBipolar(
            surface=self._screen,
            position=grid.get_position(21, 19),
            width=grid.col_interval * 13,
            height=grid.row_interval,
            border=2,
            margin_y=2,
            border_color=self.palette.TEXT_PRIMARY.RGBA,
        )

        # 档位
        self.widgets[self.W_GARE_TEXT] = PgTextStatic(
            surface=self._screen,
            position=grid.get_position(22, 12),
            width=grid.col_interval * 5,
            height=grid.row_interval,
            text="GEAR:",
            text_color=self.palette.TEXT_PRIMARY.RGBA,
            bold=True,
        )
        self.widgets[self.W_GARE_VAL] = PgTextValue(
            surface=self._screen,
            position=grid.get_position(22, 16),
            width=grid.col_interval * 2,
            height=grid.row_interval,
            text="FWD",
            text_color=self.palette.SUCCESS.RGBA,
            align_x=PgTextValue.Align.END,
            bold=True,
        )

        # 连接状态
        self.widgets[self.W_CONNECTION_TEXT] = PgTextStatic(
            surface=self._screen,
            position=grid.get_position(19, 1),
            height=grid.row_interval,
            text="CONNECTION:",
            bold=True,
        )
        self.widgets[self.W_CONNECTION_VAL] = PgTextValue(
            surface=self._screen,
            position=grid.get_position(19, 6),
            height=grid.row_interval,
            text="1",
            bold=True,
            status=PgTextValue.Status.NORMAL,
            blink_text=True,
            border=2,
            blink_border=True,
            show_sign=True,
        )

        # 控制模式
        self.widgets[self.W_MODE_TEXT] = PgText(
            surface=self._screen,
            position=grid.get_position(20, 1),
            width=grid.col_interval * 5,
            height=grid.row_interval,
            text="CTRL MODE:",
            text_color=self.palette.TEXT_PRIMARY.RGBA,
            bold=True,
        )
        self.widgets[self.W_MODE_VAL] = PgText(
            surface=self._screen,
            position=grid.get_position(20, 6),
            width=grid.col_interval * 8,
            height=grid.row_interval,
            text="DIRECT",
            text_color=self.palette.SUCCESS,
            bold=True,
        )

        # 按键显示
        self.widgets[self.W_KEY_PRESSED_TEXT] = PgText(
            surface=self._screen,
            position=grid.get_position(21, 1),
            width=grid.col_interval * 5,
            height=grid.row_interval,
            text="KEY PRESS:",
            text_color=self.palette.TEXT_PRIMARY,
            bold=True,
        )
        self.widgets[self.W_KEY_PRESSED_VAL] = PgText(
            surface=self._screen,
            position=grid.get_position(21, 6),
            width=grid.col_interval * 8,
            height=grid.row_interval,
            text="NONE",
            text_color=self.palette.WARNING.RGBA,
            bold=True,
        )

    def _update(self):
        if pygame.K_h in self._keys_released:
            self.widgets[self.W_HELP_MODEL].show = not self.widgets[self.W_HELP_MODEL].show

        self.widgets[self.W_THROTTLE_BAR].update(0.3)
        self.widgets[self.W_BRAKE_BAR].update(0.9)
        self.widgets[self.W_STEERING_BAR].update(-0.6)

if __name__ == "__main__":
    app = KeyboardControl(
        show_grid_debug= True,
    )
    app.run()