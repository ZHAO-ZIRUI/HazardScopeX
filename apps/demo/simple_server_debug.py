# ==============================================================
# 简单的服务器程序样例, 包含 Debug 工具的使用样例
# 
# 启动 CARLA 服务器并保持运行
#
#
# 逻辑：
# 1. 初始化 CARLA 上下文
# 2. 启动主线程阻塞循环
# ==============================================================
from shared.simulator import CarlaContext
from shared.utils import Logging

if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('DEMO FOR EMPTY SERVER')

    with CarlaContext() as context:
        # 启动主线程阻塞循环
        with context.log_tick_details(): # 在 Tick 过程中打印详细信息
            context.spin()

    logger.info('GOODBYE!')