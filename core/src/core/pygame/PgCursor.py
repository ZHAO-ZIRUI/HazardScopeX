from typing import Tuple, List, Any
from pydantic import Field, PrivateAttr

from core.pygame import PgWidget


class PgCursor(PgWidget):

    interval: int = Field(ge=1)
    vertical: bool = Field(default=False, frozen=True)

    color: None | Tuple[int, int, int, int] = None

    _cache_poses: List[Tuple[int, int]] = PrivateAttr(default_factory=list)

    def model_post_init(self, context: Any, /) -> None:
        self.color = self.color or self.palette.WARNING
        self._cache_poses = []
        if self.vertical:
            # 垂直方向
            x = self.position[0]
            y = self.position[1]
            while y <= self.position[1] + self.height:
                self._cache_poses.append((x, y))
                y += self.interval
        else:
            # 水平方向
            x = self.position[0]
            y = self.position[1]
            while x <= self.position[0] + self.width:
                self._cache_poses.append((x, y))
                x += self.interval

    def __getitem__(self, index: int) -> Tuple[int, int]:
        if not self._cache_poses:
            raise IndexError("Cursor positions not initialized")
        return self._cache_poses[index]

    def __len__(self):
        return len(self._cache_poses)

    def _draw_content(self):
        if self.show:
            for pos in self._cache_poses:
                self.surface.set_at(pos, self.color)  # 白色点
            