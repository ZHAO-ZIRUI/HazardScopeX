import logging
import pygame
from typing import Any, Dict, Set, Tuple
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from rich.logging import RichHandler

from core.pygame import PgColor, PgWidget


class PgApp(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,   # 增加赋值时的检查, 务必保持开启
    )

    logger_name: str = Field(default=None)
    logger_level: int = Field(default=logging.INFO)

    window_width: int = Field(default=800, ge=0, frozen=True)
    window_height: int = Field(default=600, ge=0, frozen=True)
    window_title: str = Field(default=None)
    window_fps: int = Field(default=30, ge=0, frozen=True)

    palette: PgColor = Field(default_factory=PgColor)
    widgets: Dict[str, PgWidget] = Field(default_factory=dict, frozen=True)

    _frame: int = PrivateAttr(default=0)
    _clock: pygame.time.Clock = PrivateAttr(default_factory=pygame.time.Clock)
    _screen: pygame.Surface = PrivateAttr()
    _logger: logging.Logger = PrivateAttr()
    _pressed_keys: Set[str] = PrivateAttr(default_factory=set)

    @property
    def frame(self) -> int:
        return self._frame

    @property
    def width(self) -> int:
        return self.window_width

    @property
    def height(self) -> int:
        return self.window_height

    @property
    def center(self) -> Tuple[int, int]:
        return self.window_width // 2, self.window_height // 2

    @property
    def center_x(self) -> int:
        return self.window_width // 2

    @property
    def center_y(self) -> int:
        return self.window_height // 2

    def model_post_init(self, context: Any, /) -> None:
        # 默认值处理
        if not self.window_title:
            self.window_title = self.__class__.__name__
        if not self.logger_name:
            self.logger_name = self.__class__.__name__

        # 日志系统
        self._logger = self._create_logger()

        # 完成
        self._logger.debug("Initialization complete")
        return

    def run(self):
        """执行 PyGame 主循环"""
        # 初始化 PyGame 窗口
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption(self.window_title)
        self._screen = pygame.display.set_mode((self.window_width, self.window_height))

        self._logger.info("Program started")
        try:
            self._setup_widgets()
            while True:
                self._screen.fill(self.palette.BACKGROUND)
                self._event_handler()
                self._update()
                self._draw()
                pygame.display.update()
                self._clock.tick(self.window_fps)

                # 按键退出
                if pygame.K_ESCAPE in self._pressed_keys:
                    self._logger.debug("User exit ESC")
                    break

        except KeyboardInterrupt:
            self._logger.debug("User exit Ctrl-C")
        finally:
            pygame.quit()
        self._logger.info("Goodbye")

    def _event_handler(self):
        """Pygame 事件处理程序"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                break
            elif event.type == pygame.KEYDOWN:
                self._pressed_keys.add(event.key)
            elif event.type == pygame.KEYUP:
                self._pressed_keys.discard(event.key)

    def _draw(self):
        """每个 Tick 执行一次绘制的内容, 用于展示动态对象"""
        for widget in self.widgets.values():
                widget.draw()

    def _setup_widgets(self):
        """程序开始时调用一次, 用于初始化控件"""
        pass

    def _update(self):
        """更新, 在 ``draw_tick()`` 前被调用, 用于更新状态机"""
        pass

    def _create_logger(self) -> logging.Logger:
        """
        建立类内的日志系统
        :return: ``logging.Logger`` 实例
        """
        formatter = logging.Formatter("[bold cyan][%(name)s][/] %(message)s")
        handler = RichHandler(
            rich_tracebacks=True,
            show_time=True,
            markup=True,
        )
        handler.setFormatter(formatter)
        logger = logging.getLogger(self.logger_name)
        logger.setLevel(self.logger_level)
        logger.propagate = False
        logger.addHandler(handler)
        return logger

    @field_validator("window_title", mode="after")
    @classmethod
    def _on_field_update_window_title(cls, v: str) -> str:
        pygame.display.set_caption(v)
        return v
