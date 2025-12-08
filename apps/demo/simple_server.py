# 最简服务器程序
from pathlib import Path
from shared.simulator import CarlaContext
from shared.utils import Logging

if __name__ == "__main__":
    # 基础组件初始化
    config = Path('config.yaml')                            # 读取配置文件
    logger = Logging.load(config).get_logger('Main')        # 设置日志记录器

    logger.info('Starting simple server')
    with CarlaContext(config) as context:                   # 创建 CARLA 上下文
        context.spin()                                       # 启动主线程阻塞循环
    logger.info('Goodbye!')