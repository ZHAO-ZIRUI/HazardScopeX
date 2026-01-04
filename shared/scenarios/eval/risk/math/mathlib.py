from typing import TypeAlias
import numpy as np

EPS = 1e-6

def eq(value1: float, value2: float) -> bool:
    return abs(value1 - value2) < EPS


class Vector:
    """基础的向量类，支持基础的向量操作符运算
    """

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        self._data = np.array([x, y, z])

    @property
    def x(self):
        return self._data[0]
    
    @property
    def y(self):
        return self._data[1]
    
    @property
    def z(self):
        return self._data[2]

    def __add__(self, value: 'Vector') -> 'Vector':
        if not isinstance(value, Vector):
            raise TypeError("非法向量操作：加法 " + value)

        return Vector(self.x+value.x, self.y+value.y, self.z+value.z)

    def __sub__(self, value: 'Vector') -> 'Vector':
        if not isinstance(value, Vector):
            raise TypeError("非法向量操作：减法 " + value)

        return Vector(self.x-value.x, self.y-value.y, self.z-value.z) 
    
    def __mul__(self, scalar: float) -> 'Vector':
        if not isinstance(scalar, (float, int)):
            raise TypeError("非法向量操作：乘法 " + value)

        return Vector(self.x*scalar, self.y*scalar, self.z*scalar)
    
    def __rmul__(self, scalar: float) -> 'Vector':
        return self.__mul__(scalar)

    def __eq__(self, value: object) -> bool:
        """
        重定义等于
        """
        if isinstance(value, Vector):
            return eq(self.x, value.x) and eq(self.y, value.y) and eq(self.z, value.z)
        else:
            return False
        
    def __repr__(self) -> str:
        return self.__str__()
    
    def __str__(self) -> str:
        return f"V({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"

    def length(self):
        return np.linalg.norm(self._data)


    # ---------------------------------------------
    # ----- 向量与向量操作区 -----------------------
    # ---------------------------------------------

    def distance(self, vector: 'Vector'):
        return np.linalg.norm(self._data - vector._data)

Point: TypeAlias = Vector


# ------------
# --- 测试 ---
# ------------

if __name__ == '__main__':
    a = Vector(3, 4, 0)
    b = Vector(2, 3, 0)

    print(a.length()) # 5
    print(a.distance(b)) # 1.414
