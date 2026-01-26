# 简单的因子注入样例
from shared.simulator import *
from shared.utils import Logging
from shared.configs import ConfigManager, ExternalConfigReader
from shared.prefabs import PlayerVehicle
from shared.scenarios import Injector

from factors import *
from pathlib import Path

if __name__ == "__main__":
    # 基础组件初始化
    # config = Config.from_yaml('config.yaml')        
    configReader = ExternalConfigReader(dict()).load(Path("config.yaml"))
    config = ConfigManager().load(configReader)    # 加载配置到配置管理器
    logger = Logging.load(configReader).get_logger('Main') # 设置日志记录器

    with CarlaContext(configReader) as context:
        # context.change_map('Town04')
        context.change_map('Town10HD_Opt')

        vehicle = PlayerVehicle(context, context.spawn_points[0])

        context.actors.spawn_all()
        context.actors.wait_stable(vehicle)

        f1 = FactorCase2WheelApproaching(context, vehicle)
        # f2 = FactorWeatherDustStorm(context, vehicle.lidar)

        f2 = FactorCameraChromaticAberration(context, vehicle)
        # f2 = FactorCameraColorCast(context, vehicle)
        # f2 = FactorCameraOverexposure(context, vehicle)
        # f2 = FactorCameraUnderexposure(context, vehicle)

        factors = [f1, f2]
        
        with Injector(context, *factors) as injector:       # 执行注入
            injector.spin_until_finished(*factors)

    logger.info('Goodbye!')
