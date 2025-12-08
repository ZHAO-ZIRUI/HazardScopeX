# 简单的回放程序
# 回放记录的仿真数据, 并使用 ROS2 发布传感器数据
from pathlib import Path
from shared.simulator import *
from shared.utils import Logging


if __name__ == "__main__":
    # 基础组件初始化
    config = Path('config.yaml')                            # 读取配置文件
    logger = Logging.load(config).get_logger('Main')        # 设置日志记录器

    with CarlaContext(config) as context:

        # 以上下文管理器方式回放仿真数据, 并使用 ROS2 发布传感器数据
        # 回放时, 传感器通过 demo.carla.yaml 文件内描述的属性与关系重建
        with context.recorder.replay('demo', fps=10, log_interval=3.0):

            # 可以通过 context.actors.find_by_name 找到特定的 Actor
            vehicle = context.actors.find_by_name('ACTOR_001')
            cam_game = context.actors.find_by_name('CAM_GAME')

            # 通过和其他脚本一致的方式创建 hook 绑定
            context.io.create_ros2_hp(ros_topic_name='/harzed_scope/cam/game').bind_sensor_output(cam_game)
            context.recorder.hook_on_replay_finished.append(lambda: logger.info('Replaying finished callback'))

        # 上方代码等价于
        # ------------------------------------------------------------
        # context.recorder.start_replay('demo')
        # vehicle = context.actors.find_by_name('ACTOR_001')
        # cam_game = context.actors.find_by_name('CAM_GAME')
        # context.io.create_ros2_hp(ros_topic_name='/harzed_scope/cam/game').bind_sensor_output(cam_game)
        # context.recorder.hook_on_replay_finished.append(lambda: logger.info('Replaying finished callback'))
        # context.recorder.spin_replay(fps=10, log_interval=3.0)
        # ------------------------------------------------------------

    logger.info('Goodbye!')
