import carla
import math


class CarlaVehiclePerformance:
    """
    CARLA 车辆的性能计算类
    """

    THRESHOLD_VELOCITY_LENGTH_ON_BRAKE = 1 / 3.6    # 1KM/H

    def __init__(self):
        self.max_brake_g_force = 1.0

    def __str__(self):
        return f"CarlaVehiclePerformance(max_brake_g_force={self.max_brake_g_force:.2f})"

    def calc_break_force_vector(
            self,
            velocity: carla.Vector3D,
            mass: float,
            brake: float,
            gain: float,
    ) -> carla.Vector3D:
        """
        计算刹车力的向量
        :param velocity: 用 ``carla.Vector3D`` 表示的车辆速度, 用于获取刹车力的方向
        :param mass: 车辆的质量, 单位 KG
        :param brake: 刹车踏板开度, 取值范围 ``[0,1]``
        :param gain: 刹车增益, 与里面状态有关, 取值范围 ``[-1,1]``
        :return: ``carla.Vector3D`` 车辆的刹车力向量
        :except ValueError: 输入值不在有效范围内
        """
        # 清理 brake 和 gain 的输入
        if brake < 0 or brake > 1:
            raise ValueError('brake must be between 0 and 1')
        if gain < -1 or gain > 1:
            raise ValueError('gain must be between -1 and 1')
        if mass <= 0:
            raise ValueError('mass must be greater than 0')

        # 计算刹车力的大小, F = m*a
        force = mass * 9.8 * self.max_brake_g_force * (1 + gain)

        # 计算刹车力的单位向量, 方向与速度方向相反
        velocity_length = math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)
        unit_vector = carla.Vector3D(
            -1.0 * velocity.x / velocity_length,
            -1.0 * velocity.y / velocity_length,
            -1.0 * velocity.z / velocity_length
        )

        # 如果速度低于阈值, 直接返回一个0向量以避免车辆因为力的计算在一个 tick 中瞬间改变运动方向
        if velocity_length <= self.THRESHOLD_VELOCITY_LENGTH_ON_BRAKE:
            return carla.Vector3D(0, 0, 0)

        # 计算刹车力向量
        brake_force_vector = carla.Vector3D(
            unit_vector.x * force * brake,
            unit_vector.y * force * brake,
            unit_vector.z * force * brake
        )
        return brake_force_vector
        