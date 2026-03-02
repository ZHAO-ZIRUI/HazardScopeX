from shared.scenarios.factorlib import *
from shared.define import FactorLevel
from shared.simulator import CarlaContext, CarlaVehicle
from shared.scenarios import Factor

def get_weather_light_pre_combine(context: CarlaContext, ego_vehicle: CarlaVehicle) -> list[list[Factor]]:
    weather_levels = (FactorLevel.LOW, FactorLevel.MEDIUM, FactorLevel.HIGH)
    light_levels = tuple(FactorLevel)

    # 每个组合都创建全新因子实例, 避免 teardown 后复用对象导致钩子丢失
    combines: list[list[Factor]] = []

    # 纯粹的时间因子
    combines.extend(
        [FactorEnvLight(context, ego_vehicle, level=light_level)]
        for light_level in light_levels
    )

    # 雨天 + 光照 的笛卡尔积组合
    combines.extend(
        [
            FactorWeatherRain(context, ego_vehicle, level=weather_level),
            FactorEnvLight(context, ego_vehicle, level=light_level),
        ]
        for weather_level in weather_levels
        for light_level in light_levels
    )

    # 雾天 + 光照 的笛卡尔积组合
    combines.extend(
        [
            FactorWeatherFog(context, ego_vehicle, level=weather_level),
            FactorEnvLight(context, ego_vehicle, level=light_level),
        ]
        for weather_level in weather_levels
        for light_level in light_levels
    )

    return combines
