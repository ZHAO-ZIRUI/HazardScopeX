# 最简服务器程序
from shared.simulator import CarlaContext
from shared.utils import Config, Logging

if __name__ == "__main__":
    # 基础组件初始化
    config = Config.from_yaml('config.yaml')                # 读取配置文件
    logger = Logging.from_config(config).get_logger('Main') # 设置日志记录器

    logger.info('Starting simple server')
    with CarlaContext.from_config(config) as context:        # 创建 CARLA 上下文
        context.spin()                                       # 启动主线程阻塞循环
    logger.info('Goodbye!')