from abc import ABC
from typing_extensions import Self
from dataclasses import dataclass, fields

from shared.configs import ExternalConfigReader


@dataclass
class AbstractConfig(ABC):
    """
    抽象配置类, 用于定义配置的接口

    配置项需要以 field 定义, 并使用 metadata 中的 route 属性指定配置项的路由
    """

    @classmethod
    def load(cls, path_or_reader: str | ExternalConfigReader) -> Self:
        """加载配置
        
        Args:
            path_or_reader (str | ExternalConfigReader): 配置路径或 ExternalConfigReader 实例

        Returns:
            Self: 配置实例
        """
        # 先创建带有全部默认值的实例
        instance = cls()
        
        # 解析配置源
        if isinstance(path_or_reader, str) and path_or_reader.endswith('.yaml'):
            reader = ExternalConfigReader.from_yaml(path_or_reader)
        elif isinstance(path_or_reader, str) and path_or_reader.endswith('.json'):
            reader = ExternalConfigReader.from_json(path_or_reader)
        elif isinstance(path_or_reader, ExternalConfigReader):
            reader = path_or_reader
        else:
            raise ValueError(f"Invalid config path or reader: {path_or_reader}")
        
        # 根据配置覆盖默认值
        instance._override_from_reader(reader)
        return instance

    def _override_from_reader(self, reader: ExternalConfigReader) -> Self:
        """从 ExternalConfigReader 更新实例字段
        
        Args:
            reader (ExternalConfigReader): ExternalConfigReader 实例

        Returns:
            Self: 配置实例
        """
        for field in fields(self):
            if field.metadata.get('route') is not None:
                route = field.metadata['route']
                setattr(self, field.name, reader.get(route, default=field.default))
        return self