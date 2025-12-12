class PostInitMeta(type):
    """元类, 提供 __post_init__ 方法, 在所有 __init__ 完成后调用"""
    
    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        instance.__post_init__()
        return instance