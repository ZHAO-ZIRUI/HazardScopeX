from typing import List, Tuple, TypeAlias
import numpy as np

EPS = 1e-6

def eq(value1: float, value2: float) -> bool:
    """近似等于，用于浮点数"""
    return abs(value1 - value2) < EPS


class Vector2D:
    """基础的向量类，支持基础的向量操作符运算
    """

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self._data = np.array([x, y])

    @property
    def x(self):
        return self._data[0]
    
    @property
    def y(self):
        return self._data[1]
    
    # @property
    # def angle(self):
    #     if self.y >= 0: 
    #         return np.degrees(np.arcsin(self.y / self.length()))

    def __add__(self, value: 'Vector2D') -> 'Vector2D':
        if not isinstance(value, Vector2D):
            raise TypeError("非法向量操作：加法 " + value)

        return Vector2D(self.x+value.x, self.y+value.y)

    def __sub__(self, value: 'Vector2D') -> 'Vector2D':
        if not isinstance(value, Vector2D):
            raise TypeError("非法向量操作：减法 " + value)

        return Vector2D(self.x-value.x, self.y-value.y) 
    
    def __mul__(self, scalar: float) -> 'Vector2D':
        if not isinstance(scalar, (float, int)):
            raise TypeError("非法向量操作：乘法 " + scalar)

        return Vector2D(self.x*scalar, self.y*scalar)
    
    def __rmul__(self, scalar: float) -> 'Vector2D':
        return self.__mul__(scalar)
    
    def __truediv__(self, scalar: float) -> 'Vector2D':
        if not isinstance(scalar, (float, int)):
            raise TypeError("非法向量操作：除法 " + scalar)
        return Vector2D(self.x/scalar, self.y/scalar)

    def __eq__(self, value: object) -> bool:
        """
        重定义等于
        """
        if isinstance(value, Vector2D):
            return eq(self.x, value.x) and eq(self.y, value.y)
        else:
            return False

    def length_sq(self):
        return self.x ** 2 + self.y ** 2

    def length(self):
        return np.linalg.norm(self._data)
    
    def norm(self):
        return Vector2D(self.x / self.length(), self.y / self.length())
    
    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        return f"V({self.x:.2f}, {self.y:.2f})"

    # =============================================
    # 向量与向量操作区
    # =============================================

    def distance(self, other: 'Vector2D'):
        return np.linalg.norm(self._data - other._data)
    
    def dot(self, other: 'Vector2D'):
        return self.x * other.x + self.y * other.y
    
    def cross_z(self, other: 'Vector2D'):
        return self.x * other.y - self.y * other.x

Point2D: TypeAlias = Vector2D

# ==============================================================
# 向量工厂
# ==============================================================
def create_vector2d_with_angle(length: float = 1, angle_by_degree: float = 0.0):
    """使用偏转角度创建向量"""
    return Vector2D(length * np.cos(np.radians(angle_by_degree)), length * np.sin(np.radians(angle_by_degree)))


# ==============================================================
# 向量与向量操作区
# ==============================================================

def get_orientation(p: Point2D, q: Point2D, r: Point2D) -> int:
    """计算向量 pq 和向量 pr 的相对方向关系 [1, 0, -1] -> (左转，共线，右转)

    Args:
        p (Point2D): 轴点
        q (Point2D): 初始转点
        r (Point2D): 最终转点

    Raises:
        ValueError: _description_

    Returns:
        int: 1, 0, -1
    """
    v1 = q - p
    v2 = r - p

    cross = v1.cross_z(v2)

    if eq(cross, 0):
        return 0
    
    return 1 if cross > 0 else -1


class Line:

    def __init__(self, start_point: Point2D, end_point: Point2D) -> None:
        self.p = start_point
        self.v = end_point - start_point
    
    @property
    def endpoints(self):
        """线段的两个端点"""
        return self.p, self.p + self.v
    
    @property
    def v_norm(self):
        """单位方向向量"""
        return self.v.norm()
    
    def __str__(self) -> str:
        p1, p2 = self.endpoints
        return f"Line({p1}, {p2})"

    def __repr__(self) -> str:
        return self.__str__()
    
    # =========================
    # 直线与直线操作
    # =========================

    def parallel(self, other: 'Line') -> bool:
        """直线与直线是否平行

        Args:
            other (Line): 直线（线段）

        Returns:
            bool: 
        """
        return eq(self.v.cross_z(other.v), 0)


Segment: TypeAlias = Line

# ==================================================================================
# 直线与线段相关的操作
# ==================================================================================
def intersect_with_two_segments(seg1: Segment, seg2: Segment):
    """求线段与线段的交点，如果没有交点则返回None

    Args:
        other (Segment): 线段

    Returns:
        Optional[Point2D]: 返回线段交点，没有则返回None
    """

    if seg1.parallel(seg2):
        return None

    a = seg1.v
    b = seg2.v
    u = seg1.p - seg2.p
    
    t1 = b.cross_z(u) / a.cross_z(b)
    t2 = a.cross_z(u) / a.cross_z(b)

    if 0 <= t1 <= 1 and 0 <= t2 <= 1:
        return seg1.p + t1 * a
    return None

def point_to_segment_distance(p: Vector2D, a: Vector2D, b: Vector2D) -> float:
    """计算点 P 到线段 AB 的最短距离"""
    ab = b - a
    ap = p - a
    bp = p - b
    
    # 计算投影长度比例 t
    # t = (AP · AB) / |AB|^2
    ab_len_sq = ab.length_sq()
    if ab_len_sq < 1e-9:
        return float(ap.length())
    
    t = ap.dot(ab) / ab_len_sq
    
    if t < 0:
        return float(ap.length())      # 投影在 A 点外，最近点是 A
    elif t > 1:
        return float(bp.length())      # 投影在 B 点外，最近点是 B
    else:
        # 投影在线段上，计算垂直距离
        closest_point = a + (ab * t)
        return (p - closest_point).length()

# ==================================================================================
# 凸包类
# ==================================================================================

class ConvexHull:

    def __init__(self, points: List[Vector2D]) -> None:
        """
        使用 Monotone Chain 算法，从点集中构建凸包
        """
        if len(points) < 3:
            raise ValueError("凸包至少需要3个点。")
            
        # 1. 排序：按 x 坐标升序，x 相同则按 y 坐标升序
        sorted_points = sorted(points, key=lambda p: (p.x, p.y))
        
        # 2. 构建下凸包 (Lower Hull)
        lower_hull: List[Vector2D] = []
        for p in sorted_points:
            while len(lower_hull) >= 2 and \
                  get_orientation(lower_hull[-2], lower_hull[-1], p) <= 0:
                lower_hull.pop()
            lower_hull.append(p)

        # 3. 构建上凸包 (Upper Hull)
        upper_hull: List[Vector2D] = []
        # 从后往前遍历
        for p in reversed(sorted_points):
            while len(upper_hull) >= 2 and \
                  get_orientation(upper_hull[-2], upper_hull[-1], p) <= 0:
                upper_hull.pop()
            upper_hull.append(p)
            
        # 4. 组合上下凸包，并移除重复的起点和终点
        # 结果集是按逆时针顺序排列的凸包边界点
        self.hull_points: List[Vector2D] = lower_hull[:-1] + upper_hull[:-1]
        
        self._cache_hull_properties()


    def _cache_hull_properties(self):
        """缓存 AABB 和 外接圆 包围盒
        """
        if not self.hull_points:
            self.min_x, self.max_x, self.min_y, self.max_y = 0, 0, 0, 0
            self.center = Point2D(0, 0)
            self.radius = 0.0

        xs = [point.x for point in self.hull_points]
        ys = [point.y for point in self.hull_points]

        # AABB（包围盒）
        self.min_x, self.max_x = min(xs), max(xs)
        self.min_y, self.max_y = min(ys), max(ys)

        # 外接圆
        self.center = Point2D(sum(xs) / len(xs), sum(ys) / len(ys)) # 重心
        
        max_dist = 0
        for point in self.hull_points:
            dist = self.center.distance(point)
            max_dist = max(dist, max_dist)
        self.radius = max_dist

    @property
    def aabb(self) -> List[float]:
        """输出左下角和右上角坐标

        Returns:
            List[float]
        """
        return [self.min_x, self.min_y, self.max_x, self.max_y]
    
    def get_edges(self) -> List[Segment]:
        n = len(self.hull_points)
        return [Segment(self.hull_points[i], self.hull_points[(i+1)%n]) for i in range(n)]

    def is_point_inside(self, p: Vector2D) -> bool:
        """
        检测点 p 是否在凸包内部（或边界上）。
        使用叉积：点 p 必须始终位于所有凸包边界边的同一侧。
        """
        n = len(self.hull_points)
        if n < 3: return False # 不是有效凸包

        # 我们假设凸包点是逆时针排列 (Monotone Chain 保证了这一点)
        # 如果是逆时针，所有叉积结果应该 >= 0 (即点 p 位于边的左侧或共线)
        for i in range(n):
            p1 = self.hull_points[i]
            p2 = self.hull_points[(i + 1) % n]
            
            # 计算向量 (p2 - p1) 和 (p - p1) 的叉积
            # 如果叉积 < 0，则点 p 位于边的右侧，因此在凸包外部
            if get_orientation(p1, p2, p) < 0:
                return False
                
        return True

# =====================================================================
# 凸包碰撞检测与距离计算
# =====================================================================
def intersect_segment_with_convex_hull(hull: ConvexHull, segment: Segment) -> List[Point2D]:
    """求线段与凸包的交点

    Args:
        hull (ConvexHull): 凸包
        segment (Segment): 线段

    Returns:
        List[Point2D]: 交点列表。可能的数量为 [0,1,2]
    """

    intersection = []

    start_point, end_point = segment.endpoints

    # 线段在凸包内
    if hull.is_point_inside(start_point) and hull.is_point_inside(end_point):
        return []

    edges = hull.get_edges()
    for edge in edges:
        p = intersect_with_two_segments(edge, segment)
        if p is not None:
            intersection.append(p)

    return intersection

def distance_to_hull(hull: ConvexHull, p: Point2D) -> float:
    """计算点到凸包的距离，选用外接圆包围盒和轴对齐矩形包围盒的更大值

    Args:
        hull (ConvexHull): 凸包
        p (Point2D): 点

    Returns:
        float: 距离值
    """
    if hull.is_point_inside(p):
        return 0.0

    min_dist = float('inf')
    for seg in hull.get_edges():
        a, b = seg.endpoints
        dist = point_to_segment_distance(p, a, b)
        if dist < min_dist:
            min_dist = dist
            
    return min_dist


def distance_hull_bounding_circle(hull1: ConvexHull, hull2: ConvexHull):
    """使用外接圆包围盒计算两个凸包的距离，如果两圆相交，则返回 0

    Args:
        hull1 (ConvexHull): 凸包1
        hull2 (ConvexHull): 凸包2
    """
    center1 = hull1.center
    center2 = hull2.center

    return max(center1.distance(center2) - hull1.radius - hull2.radius, 0)
    

def distance_hull_aabb(hull1: ConvexHull, hull2: ConvexHull):
    """使用轴对齐包围矩形方法计算两个凸包的距离，如果矩形相交，则返回 0

    Args:
        hull1 (ConvexHull): 凸包1
        hull2 (ConvexHull): 凸包2
    """
    # 判断 x 轴方向的距离
    x_gap = max(hull1.min_x, hull2.min_x) - min(hull1.max_x, hull2.max_x)
    x_gap = max(0, x_gap)

    # 判断 y 轴方向的距离
    y_gap = max(hull1.min_y, hull2.min_y) - min(hull1.max_y, hull2.max_y)
    y_gap = max(0, y_gap)

    return np.sqrt(x_gap ** 2 + y_gap ** 2)


# ==============================================================================================
# Carla 类与转换
# ==============================================================================================


# ------------
# --- 测试 ---
# ------------

if __name__ == '__main__':
    points = [
        (2, 0),
        (0, 2),
        (-2, 0),
        (0, -2),
        (3, 0),
        (4, 0),
        (3, -2),
        (4, -2)
    ]


    points = [Point2D(p[0], p[1]) for p in points]

    convex_hull1 = ConvexHull(points[0:4])
    convex_hull2 = ConvexHull(points[4:8])
    
    # 测试凸包相关功能
    print(convex_hull1.hull_points) # [(-2, 0), (0, -2), (2, 0), (0, 2)]
    print(convex_hull2.hull_points) # [(3, -2), (4, -2), (4, 0), (3, 0)]
    print(convex_hull1.aabb) # [-2, -2, 2, 2]
    print(convex_hull2.aabb) # [3, -2, 4, 2]
    print(distance_hull_bounding_circle(convex_hull1, convex_hull2)) # [0.52]
    print(distance_hull_aabb(convex_hull1, convex_hull2)) # [1.0]
    print(convex_hull1.is_point_inside(Point2D(0, 0))) # True
    print(convex_hull1.is_point_inside(Point2D(2, 2))) # False

    # 测试凸包与线段相关功能
    seg = Segment(Point2D(0, 0), Point2D(2, 2))
    print(intersect_segment_with_convex_hull(convex_hull1, seg)) # [(1, 1)]
    print(intersect_segment_with_convex_hull(convex_hull2, seg)) # []
    print(distance_to_hull(convex_hull1, Point2D(2, -2))) # [0.83]
    # 测试向量工厂函数
    v1 = create_vector2d_with_angle(angle_by_degree=45) # (0.71, 0.71)

    print(v1)
