import uuid
from typing import Dict
from pydantic import Field

from core.pygame import PgWidget


class PgContainer(PgWidget):
    """
    容器控件, 用于包含和管理多个子控件.
    """

    sub_widgets: Dict[str, PgWidget] = Field(default_factory=dict, frozen=True)

    def __getitem__(self, item: str) -> PgWidget:
        return self.sub_widgets[item]

    def __len__(self) -> int:
        return len(self.sub_widgets)

    def add_widget(self, widget: PgWidget, name: str = None):
        if name is None:
            name = uuid.uuid4().hex
        self.sub_widgets[name] = widget

    def get_widget(self, name: str) -> PgWidget:
        return self.sub_widgets.get(name)

    def _draw_content(self):
        widgets = sorted(self.widgets.values(), key=lambda x: x.z_index)

        for widget in widgets:
            widget.draw()