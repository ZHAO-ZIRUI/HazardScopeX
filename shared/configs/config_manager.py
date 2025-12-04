from typing_extensions import Self
from pathlib import Path

from shared.configs import *


class ConfigManager:
    """统一配置文件管理器"""

    def __init__(self):
        self._carla_context_config = CarlaContextConfig()
        self._carla_actor_manager_config = CarlaActorManagerConfig()

    @property
    def context(self) -> CarlaContextConfig:
        return self._carla_context_config

    @property
    def actor_manager(self) -> CarlaActorManagerConfig:
        return self._carla_actor_manager_config

    def load(self, incoming: Path | ExternalConfigReader) -> Self:
        self._carla_context_config = CarlaContextConfig.load(incoming)
        self._carla_actor_manager_config = CarlaActorManagerConfig.load(incoming)
        return self