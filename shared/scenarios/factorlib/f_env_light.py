from typing_extensions import Self
from collections import namedtuple

from shared.scenarios import Factor
from shared.define import FactorLevel
from shared.simulator import CarlaContext, CarlaVehicle

ENV_LIGHT_PARAMS = namedtuple(
    'EnvLightParams',
    [
        'sun_altitude_angle',
        'city_lights_mode',  # 'default' | 'on' | 'off'
    ],
)


class FactorEnvLight(Factor):
    NAME = 'F_EnvLight'

    # NONE 正午, LOW 黄昏, MEDIUM 夜晚, HIGH 夜晚且城市灯光关闭
    M_LEVEL_VALUE = {
        FactorLevel.NONE: ENV_LIGHT_PARAMS(70.0, 'off'),
        FactorLevel.LOW: ENV_LIGHT_PARAMS(2.0, 'on'),
        FactorLevel.MEDIUM: ENV_LIGHT_PARAMS(-10.0, 'on'),
        FactorLevel.HIGH: ENV_LIGHT_PARAMS(-10.0, 'off'),
    }

    def __init__(
        self,
        context: CarlaContext,
        ego_vehicle: CarlaVehicle,
        level: FactorLevel,
        *,
        ignore_factor_ego_control: bool = False,
        keepalive_after_trigger: float = 0.0,
    ):
        super().__init__(
            context,
            ego_vehicle,
            level,
            ignore_factor_ego_control=ignore_factor_ego_control,
            keepalive_after_trigger=keepalive_after_trigger,
        )

    def __post_init__(self) -> Self:
        self.hook_bringup.append(self.set_env_light)
        return super().__post_init__()

    def set_env_light(self) -> None:
        params: ENV_LIGHT_PARAMS = self.M_LEVEL_VALUE[self._level]

        # 调整太阳高度角控制环境亮度
        weather = self._context.world.get_weather()
        weather.sun_altitude_angle = params.sun_altitude_angle
        self._context.world.set_weather(weather)

        # 调整城市灯光开关
        self._apply_city_lights(params.city_lights_mode)

    def _apply_city_lights(self, mode: str) -> None:
        """根据模式控制城市灯光开关, 若当前 CARLA 版本不支持 LightManager 则静默跳过"""
        world = self._context.world
        if not hasattr(world, 'get_lightmanager'):
            return

        light_manager = world.get_lightmanager()
        lights = light_manager.get_all_lights()

        if mode == 'off':
            light_manager.turn_off(lights)
        elif mode == 'on':
            light_manager.turn_on(lights)

