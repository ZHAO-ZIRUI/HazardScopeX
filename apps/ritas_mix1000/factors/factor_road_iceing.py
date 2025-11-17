import carla
from shared.scenarios import Factor
from shared.simulator import *


class FactorRoadIceing(Factor):
    NAME = 'F_RoadIceing'

    def __init__(
        self, 
        context: CarlaContext, 
        vehicle: CarlaVehicle,
        *,
        after_seconds: float = 3.0,
        steer_right_delay_seconds: float = 0.5,
        reenable_delay_seconds: float = 1.0,
    ):
        super().__init__(context)
        self._vehicle = vehicle
        self._after_ticks = int(after_seconds * self._context.fps)
        self._steer_right_delay_ticks = int(steer_right_delay_seconds * self._context.fps)
        self._reenable_delay_ticks = int(reenable_delay_seconds * self._context.fps)
        self._current_ticks = 0
        self._autopilot_disabled = False
        self._autopilot_disabled_at_tick = -1
        self._steer_right_applied = False
        self._autopilot_reenabled = False

    def setup(self) -> None:
        weather = self._context.world.get_weather()
        weather.wetness = 100
        weather.precipitation_deposits = 100
        self._context.world.set_weather(weather)
        return super().setup()

    def tick(self) -> None:
        # 延迟后禁用 autopilot 并向左急打方向（打满）
        if not self._autopilot_disabled and self._current_ticks >= self._after_ticks:
            self._autopilot_disabled = True
            self._autopilot_disabled_at_tick = self._current_ticks
            # 禁用 autopilot
            self._vehicle.set_carla_autopilot(enable=False)
            # 向左急打方向（打满，steer = -1.0）
            control = carla.VehicleControl()
            control.steer = -1.0
            control.throttle = 0.5  # 保持一定速度
            self._vehicle.actor.apply_control(control)
            self.logger.info(f'Disabled autopilot and steered left (full) after {self._after_ticks / self._context.fps:.1f} seconds')
        
        # 0.5秒后向右急打方向（打满）
        if (self._autopilot_disabled and not self._steer_right_applied and 
            self._autopilot_disabled_at_tick >= 0 and 
            (self._current_ticks - self._autopilot_disabled_at_tick) >= self._steer_right_delay_ticks):
            self._steer_right_applied = True
            # 向右急打方向（打满，steer = 1.0）
            control = carla.VehicleControl()
            control.steer = 1.0
            control.throttle = 0.5  # 保持一定速度
            self._vehicle.actor.apply_control(control)
            self.logger.info(f'Steered right (full) after {self._steer_right_delay_ticks / self._context.fps:.1f} seconds')
        
        # 持续应用控制直到重新启用 AP
        if self._autopilot_disabled and not self._autopilot_reenabled:
            control = carla.VehicleControl()
            if self._steer_right_applied:
                control.steer = 1.0  # 保持向右打满
            else:
                control.steer = -1.0  # 保持向左打满
            control.throttle = 0.5  # 保持一定速度
            self._vehicle.actor.apply_control(control)
        
        # 延迟后重新启用 autopilot
        if (self._autopilot_disabled and not self._autopilot_reenabled and 
            self._autopilot_disabled_at_tick >= 0 and 
            (self._current_ticks - self._autopilot_disabled_at_tick) >= self._reenable_delay_ticks):
            self._autopilot_reenabled = True
            self._vehicle.set_carla_autopilot(enable=True)
            self.logger.info(f'Re-enabled autopilot after {self._reenable_delay_ticks / self._context.fps:.1f} seconds')
        
        self._current_ticks += 1
        return super().tick()
