import sys
import select
import termios
import tty
from shared.simulator import CarlaContext
from shared.utils import Logging

from shared.prefabs import NuScenesVehicle
from shared.scenarios.factorlib import *
from shared.scenarios.injector import Injector
from shared.define import FactorLevel
from pre_combine import get_weather_light_pre_combine


def wait_until_keypress(context: CarlaContext) -> None:
    """
    持续推进仿真直到检测到任意键盘输入
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            context.wait_ticks(1, no_log=True)
            readable, _, _ = select.select([sys.stdin], [], [], 0)
            if readable:
                sys.stdin.read(1)
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    logger = Logging.load('config.yaml').get_logger('Main')
    logger.info('FACTOR DEBUG SCRIPT')


    SPAWN_POINT_EGO = 107 
    SPAWN_POINT_ACT = 49
    FACTOR_CLASS = FactorWeatherFog
    FACTOR_CLASS = FactorWeatherRain
    FACTOR_CLASS = FactorEnvLight

    with CarlaContext() as context:

        v_ego = NuScenesVehicle(context, context.spawn_points[SPAWN_POINT_EGO], name='EGO')

        context.actors.spawn_all()
        context.actors.wait_stable()


        factos = get_weather_light_pre_combine(context, v_ego)
        for factors in factos:
            with Injector(context, *factors) as injector:
                logger.warning(f'Factors {", ".join([f"{factor.NAME}({factor.level.value})" for factor in factors])} injected')
                wait_until_keypress(context)

    logger.info('GOODBYE!')