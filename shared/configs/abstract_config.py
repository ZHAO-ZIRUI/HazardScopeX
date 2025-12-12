from abc import ABC
from pathlib import Path
from typing_extensions import Self
from dataclasses import dataclass, fields, MISSING

from shared.configs import ExternalConfigReader


@dataclass
class AbstractConfig(ABC):
    """
    抽象配置类, 用于定义配置的接口

    配置项需要以 field 定义, 并使用 metadata 中的 route 属性指定配置项的路由
    """

    @classmethod
    def load(cls, path_or_reader: Path | ExternalConfigReader) -> Self:
        """加载配置
        
        Args:
            path_or_reader (Path | ExternalConfigReader): 配置路径或 ExternalConfigReader 实例

        Returns:
            Self: 配置实例
        """
        # 先创建带有全部默认值的实例
        instance = cls()
        
        # 解析配置源
        if isinstance(path_or_reader, Path):
            reader = ExternalConfigReader.load(path_or_reader)
        elif isinstance(path_or_reader, ExternalConfigReader):
            reader = path_or_reader
        else:
            raise ValueError(f"Invalid config path or reader: {path_or_reader}")
        
        # 根据配置覆盖默认值
        for field in fields(instance):
            if field.metadata.get('route') is not None:
                route = field.metadata['route']
                default_value = field.default if field.default != MISSING else getattr(instance, field.name)
                setattr(instance, field.name, reader.get(route, default=default_value))
        
        return instance