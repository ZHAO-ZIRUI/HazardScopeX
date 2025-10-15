from shared.simulator import CarlaActor


class CarlaVehicle(CarlaActor):
    """
    carla.Vehicle 的外部封装, 用于提供高级功能或适配可重启的服务端
    """

    def __init__(
        self,
    ):
        super().__init__()