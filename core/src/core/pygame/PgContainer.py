import uuid
from typing import Dict
from pydantic import Field

from core.pygame import PgWidget


class PgContainer(PgWidget):
    """
    容器控件, 用于包含和管理多个子控件.
    """

    widgets: Dict[str, PgWidget] = Field(default_factory=dict, frozen=True)

    def __getitem__(self, item: str) -> PgWidget:
        return self.widgets[item]

    def __len__(self) -> int:
        return len(self.widgets)

    def add_widget(self, widget: PgWidget, name: str = None):
        if name is None:
            name = f"{self.__class__.__name__}-{id(self)}-{uuid.uuid4().hex}"
        self.widgets[name] = widget

    def get_widget(self, name: str) -> PgWidget:
        return self.widgets.get(name)

    def _draw_content(self):
        # 自动注册以 ``W_`` 开头的属性为子控件
        for name, value in self.__dict__.items():
            if name.startswith("W_"):
                if isinstance(value, PgWidget):
                    self.widgets[name] = value

        # 排序并绘制子控件
        widgets = sorted(self.widgets.values(), key=lambda x: x.z_index)
        for widget in widgets:
            widget.draw()