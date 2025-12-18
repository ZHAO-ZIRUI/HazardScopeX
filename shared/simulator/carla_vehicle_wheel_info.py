from enum import Enum
'''
carla中已有vehicle的wheel信息枚举
'''



class CalraVehicleTeslaModel3(Enum):
    '''
    TeslaModel3的wheel信息枚举  单位为米
    '''
    # 车体总长
    VEHICLE_LENGTH = 4.72
    # 车体总高
    VEHICLE_HEIGHT = 1.44
    #轮胎半径
    WHEEL_RADIUS = 0.383
    #轮胎宽度
    WHEEL_WIDTH = 0.235
    #前轮中心 ↔ 后轮中心 的距离
    WHEEL_BASE = 2.875
    #左轮到右轮的距离
    WHEEL_THREAD = 1.584
    #前轴中心到车头 的距离
    FRONT_OVERHANG = 0.868
    #后轴中心到车尾的距离
    REAR_OVERHANG = 0.977



VehicleWheelFactory = {
    "vehicle.tesla.model3":CalraVehicleTeslaModel3
}

