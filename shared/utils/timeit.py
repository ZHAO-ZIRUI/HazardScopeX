import time
from functools import wraps

def timeit(func):
    # 使用 wraps 保留原函数的元数据（名称、文档等）
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"[timeit] {func.__name__} executed in {end - start:.6f} seconds")
        return result

    return wrapper