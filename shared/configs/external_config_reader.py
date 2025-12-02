import yaml
import json
import uuid
from types import NoneType
from typing import Any, TypeVar
from typing_extensions import Self


class ExternalConfigReader:
    """
    外部配置文件读取类, 用于读取外部配置文件
    """
    T = TypeVar('T', int, float, str, bool, NoneType)

    RAISE_EXCEPTION = str(uuid.uuid4())  # 用于在找不到配置项时抛出异常的唯一标识符

    def __init__(self, config: dict):
        self._config = config

    def get(self, route: str, default: T | None = RAISE_EXCEPTION) -> T:
        """以路由递归方式找到深层字典中的值, 并进行类型转换. 

        注意: default 的类型会影响类型转换, 例如 default 为 int, 则返回值也会被转换为 int.
    
        Args:
            route (str): 路由, 以 / 分隔, 如: /foo/bar
            default (T | None, optional): 默认值. 如果为 RAISE_EXCEPTION, 则当找不到配置项时抛出异常.

        Returns:
            Any: 根据类型转换类型, 返回对应的值.
        """
        if not route:
            if default == self.RAISE_EXCEPTION:
                msg = f"Config item not found: empty route"
                self.logger.error(msg)
                raise KeyError(msg)
            return default

        # 清理 route 头尾可能存在的 /
        normalized_route = route
        if normalized_route.startswith('/'):
            normalized_route = normalized_route[1:]
        if normalized_route.endswith('/'):
            normalized_route = normalized_route[:-1]

        # 执行递归查找
        keys = normalized_route.split('/')
        current = self._config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                # 未找到配置项，返回默认值
                if default == self.RAISE_EXCEPTION:
                    raise KeyError(f"Config item not found: {route}")
                else:
                    return default

        # 找到配置项
        if default == self.RAISE_EXCEPTION:
            return current
        else:
            return self._type_convert(current, type(default))
        
    def _type_convert(self, value: Any, target_type: type) -> Any:
        # None, 不进行任何转换
        if target_type == NoneType:
            return value
        
        # bool 
        if target_type == bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str) and value.lower() in ['true', '1', 'yes', 'y', 't']:
                return True
            elif isinstance(value, str) and value.lower() in ['false', '0', 'no', 'n', 'f']:
                return False
            else:
                raise ValueError(f"Invalid boolean value: {value}")

        # int
        if target_type == int:
            if isinstance(value, int):
                return value
            elif isinstance(value, float):
                return int(value)
            elif isinstance(value, str):
                try:
                    return int(value)
                except ValueError:
                    raise ValueError(f"Invalid integer value: {value}")
            else:
                raise ValueError(f"Invalid integer value: {value}")

        # float
        if target_type == float:
            if isinstance(value, float):
                return value
            elif isinstance(value, int):
                return float(value)
            elif isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    raise ValueError(f"Invalid float value: {value}")
            else:
                raise ValueError(f"Invalid float value: {value}")

        # str
        return str(value)

    @classmethod
    def from_yaml(cls, file_path: str) -> Self:
        with open(file_path, 'r', encoding='utf-8') as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        return cls(config)

    @classmethod
    def from_json(cls, file_path: str) -> Self:
        with open(file_path, 'r', encoding='utf-8') as file:
            config = json.load(file)
        return cls(config)