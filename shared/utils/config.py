import yaml
import json
from typing import Dict, Any
from typing_extensions import Self


class Config:
    """
    配置文件读取类
    """

    ALLOWED_TYPES = (int, float, str, bool)

    def __init__(self, config: Dict):
        self._config = config

    def get(self, route: str, default=None, target_type: type = None) -> Any:
        """以路由地柜方式找到深层字典中的值, 并进行类型转换. 
    
        Args:
            route (str): 路由, 以 / 分隔, 如: /foo/bar
            default (_type_, optional): 默认值.
            target_type (type, optional): 类型转换类型.

        Returns:
            Any: 根据类型转换类型, 返回对应的值.
        """
        if not route:
            return default

        # 清理 route 头尾可能存在的 /
        if route.startswith('/'):
            route = route[1:]
        if route.endswith('/'):
            route = route[:-1]

        # 执行递归查找
        keys = route.split('/')
        current = self._config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                # 未找到配置项，返回默认值
                return default

        # 找到了配置项，进行类型转换
        return self._type_convert(current, target_type)

        
    def _type_convert(self, value: Any, target_type: type) -> Any:
        if target_type not in self.ALLOWED_TYPES:
            raise TypeError(f"Invalid target type: {target_type}")
        
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
        with open(file_path, 'r') as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        return cls(config)

    @classmethod
    def from_json(cls, file_path: str) -> Self:
        with open(file_path, 'r') as file:
            config = json.load(file)
        return cls(config)