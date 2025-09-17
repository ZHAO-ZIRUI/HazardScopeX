from typing import Dict


class RouteConfig(object):

    ALLOWED_TYPES = (bool, float, int, str)

    def __init__(self, config: Dict):
        self._config = config

    def get(self, route: str, default=None, target_type: type = None):
        """
        以路由递归的方式找到深度字典中的值, 路由以 / 分隔
        :param route: 字典路由
        :param target_type: 目标类型 (bool, float, int, str)
        :param default: 默认返回值
        :return: 转换后的值
        :exception ValueError: 当 target_type 不在 ALLOWED_TYPES 中, 或者转换失败时抛出
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
                return default
        if current is None:
            return default
            
        # 验证目标类型是否合法
        if target_type is None:
            target_type = type(default)
        elif target_type not in self.ALLOWED_TYPES:
            raise ValueError(f"target_type must be one of {self.ALLOWED_TYPES}, given {target_type}")
        return self._type_convert(current, target_type)

    @staticmethod
    def _type_convert(value, target_type: type):
        try:
            if target_type == bool:
                if isinstance(value, str):
                    return value.lower() in ('true', '1')
                return bool(value)
            elif target_type == float:
                return float(value)
            elif target_type == int:
                return int(float(value))
            elif target_type == str:
                return str(value)
            else:
                return value
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert value '{value}' to {target_type}")