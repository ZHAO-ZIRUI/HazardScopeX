from typing import Dict, TypeVar

T = TypeVar('T')


class RouteConfig(object):

    def __init__(self, config: Dict):
        self._config = config

    def get(self, route: str, default: T = None) -> T:
        """
        以路由递归的方式找到深度字典中的值, 路由以 / 分隔
        :param route: 字典路由
        :param default: 默认返回值
        :return:
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
                
        return current
        