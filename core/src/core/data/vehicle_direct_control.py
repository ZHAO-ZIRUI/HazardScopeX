import carla
import random
from typing_extensions import Self

from core.data import SimulatorInput


class VehicleDirectControl(SimulatorInput):
    """车辆底层控制"""

    def __init__(
            self,
            *,
            throttle: float = 0.0,
            steering: float = 0.0,
            brake: float = 0.0,
            reverse: bool = False,
    ):
        """
        :param throttle: 加速踏板开度, 范围 ``[0,1]``
        :param steering: 方向盘归一化转角, 范围 ``[-1,1]``
        :param brake: 刹车踏板开度, 范围 ``[0,1]``
        :param reverse: 是否为倒挡, 默认为 ``False``
        """
        super().__init__()

        # 数据检查
        if throttle < 0 or throttle > 1:
            raise ValueError(f"throttle must be between 0 and 1, given {throttle}")
        if steering < -1 or steering > 1:
            raise ValueError(f"steering must be between -1 and 1, given {steering}")
        if brake < 0 or brake > 1:
            raise ValueError(f"brake must be between 0 and 1, given {brake}")
        if throttle > 0 and brake > 0:
            raise ValueError(f"throttle and brake are mutually exclusive, given {throttle}, {brake}")

        self._data = (throttle, steering, brake, reverse)

    @property
    def throttle(self) -> float:
        return self._data[0]

    @property
    def steering(self) -> float:
        return self._data[1]

    @property
    def brake(self) -> float:
        return self._data[2]

    @property
    def reverse(self) -> bool:
        return self._data[3]

    def to_carla(
        self,
        disturbance = False
    ) -> carla.VehicleControl:
        """
        转换为 `` carla.VehicleControl`` 实例
        :param disturbance: 是否进行微量扰动以令每次得到的值均不同, 避免 RPC 调用不生效
        :return: ``carla.VehicleControl`` 实例
        """
        # 对输入值进行小范围随机扰动, 避免 RPC 调用不生效
        r_throttle = random.uniform(self.throttle - 0.001, self.throttle + 0.001)
        r_steer = random.uniform(self.steering - 0.001, self.steering + 0.001)
        r_brake = random.uniform(self.brake - 0.001, self.brake + 0.001)

        # 防止随机扰动后越界
        r_throttle = max(-1.0, min(1.0, r_throttle))
        r_steer = max(-1.0, min(1.0, r_steer))
        r_brake = max(-1.0, min(1.0, r_brake))

        # 处理置 0 的特殊情况
        if self.throttle == 0.0:
            r_throttle = 0
        if self.steering == 0.0:
            r_steer = 0
        if self.brake == 0.0:
            r_brake = 0

        if disturbance:
            instance = carla.VehicleControl(
                throttle=r_throttle,
                steer=r_steer,
                brake=r_brake,
                hand_brake=False,
                reverse=self.reverse
            )
        else:
            instance = carla.VehicleControl(
                throttle=self.throttle,
                steer=self.steering,
                brake=self.brake,
                hand_brake=False,
                reverse=self.reverse
            )
        return instance

    @classmethod
    def from_carla(cls, control: carla.VehicleControl) -> Self:
        """
        从 CARLA 类中转换数据
        :param control: ``carla.VehicleControl`` 实例
        :return: ``VehicleDirectControl`` 实例
        """
        instance = cls(
            throttle=control.throttle,
            steering=control.steering,
            brake=control.brake,
            reverse=control.reverse
        )
        return instance