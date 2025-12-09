# ==============================================================
# 简单的回放程序样例
# 
# 回放记录的仿真数据, 并使用 ROS2 发布传感器数据
# 回放时, 传感器通过 demo.carla.yaml 文件内描述的属性与关系重建
#
#
# 逻辑：
# 1. 加载回放数据
# 2. 通过名称查找特定传感器
# 3. 创建 ROS2 绑定输出
# ==============================================================
from shared.simulator import CarlaContext
from shared.utils import Logging
from shared.simulator import CarlaSensor

if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('DEMO FOR REPLAY')


    with CarlaContext() as context:
        
        # 回放仿真数据, 此处文件名不需要添加任何后缀
        with context.recorder.replay('20251209_111257', fps=10, log_interval=3.0):
            
            # 通过名称查找名称为 Player_CAM_GAME 的相机传感器
            cam_game = context.actors.find_by_name('Player_CAM_GAME')
            assert isinstance(cam_game, CarlaSensor)  # 断言传感器对象

            # 创建 ROS2 绑定传感器输出
            context.io.create_ros2(topic='/harzed_scope/cam/game').bind_sensor_output(cam_game)

    logger.info('GOODBYE!')
