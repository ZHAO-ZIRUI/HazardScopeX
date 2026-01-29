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
        # context.change_map('Town10HD_Opt')
        context.change_map('Town04')
        vehicle = PlayerVehicle(context, context.spawn_points[0])
        # for i in range(4):

        context.actors.spawn_all()
        context.actors.wait_stable(vehicle)
        # f1 = FactorCaseFrontVehicleStatic(context, vehicle)
        # f1 = FactorCase2WheelApproaching(context, vehicle)
        # f1 = FactorCasePedestrianDartOut(context, vehicle)
        f1 = FactorCaseHighwayMerge(context, vehicle)
        # f1 = FactorCaseFrontVehicleCutIn(context, vehicle)

        # f2 = FactorWeatherDustStorm(context, vehicle, dust_level=3)
        # f2 = FactorWeatherRain(context, vehicle, rain_level=3)
        f2 = FactorWeatherFog(context, vehicle, fog_level=3)

        # f3 = FactorCameraChromaticAberration(context, vehicle)
        # f3 = FactorCameraColorCast(context, vehicle)
        # f3 = FactorCameraOverexposure(context, vehicle)
        # f3 = FactorCameraUnderexposure(context, vehicle)
        # f3 = FactorCameraMultiple(context, vehicle, exposure_level=3, cast_level=3, aberration_level=3)

        factors = [f1, f2]
        
        with Injector(context, *factors) as injector:       # 执行注入
            injector.spin_until_finished(*factors)

    logger.info('Goodbye!')
