from enum import Enum
'''
carla中已有vehicle的wheel信息枚举
'''



class CalraVehicleTeslaModel3(Enum):
    '''
    TeslaModel3的wheel信息枚举
    '''
    #轮胎半径
    WHEEL_RADIUS = 0.383
    #轮胎宽度
    WHEEL_WIDTH = 0.235
    #前轮中心 ↔ 后轮中心 的距离
    WHEEL_BASE = 3.0046
    #左轮到右轮的距离
    WHEEL_THREAD = 1.4198
    #前轴中心到车头 的距离
    FRONT_OVERHANG = 1.0
    #后轴中心到车尾的距离
    REAR_OVERHANG = 1.3
    #左轮中心到车左边界的距离
    LEFT_OVERHANG = 0.128
    #右轮中心到车右边界的距离
    RIGHT_OVERHANG = 0.128
    ## 最大转角 [rad]
    MAX_STEERING_ANGLE = 0.73


VehicleWheelFactory = {
    "vehicle.tesla.model3":CalraVehicleTeslaModel3
}

