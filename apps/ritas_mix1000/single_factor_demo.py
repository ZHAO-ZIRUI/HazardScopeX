# 简单的因子注入样例
from shared.scenarios.evaluator import SimpleRiskEvaluator
from shared.simulator import *
from shared.utils import Logging
from shared.configs import ConfigManager, ExternalConfigReader
from shared.prefabs import PlayerVehicle
from shared.scenarios import Injector

from factors import *
from pathlib import Path

if __name__ == "__main__":
    # 基础组件初始化
    configReader = ExternalConfigReader(dict()).load(Path("config.yaml"))
    config = ConfigManager().load(configReader)    # 加载配置到配置管理器
    print("config:",config.context," ",config.actor_manager," ",config.io_manager)
    logger = Logging.load(configReader).get_logger('Main') # 设置日志记录器

    with CarlaContext(configReader) as context:
        context.change_map('Town10HD_Opt')

        vehicle = PlayerVehicle(context, context.spawn_points[0])

        context.actors.spawn_all()
        context.actors.wait_stable(vehicle)

        evaluator = SimpleRiskEvaluator(context)
        evaluator.bind_evaluate_actor('hero', vehicle)

        # 绑定传感器输出到内存
        context.io.create_shm(topic='cam_game').bind_sensor_output(vehicle.cam_game)

        f1 = FactorCaseVehicleFollow(context, vehicle)

        factors = [f1]
        
        with Injector(context, *factors) as injector:       # 执行注入
            injector.spin_until_finished(evaluator, *factors)

    logger.info('Goodbye!')
