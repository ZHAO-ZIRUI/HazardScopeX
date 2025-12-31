from enum import Enum
from typing import Literal


class CarlaBlueprints(Enum):
    """CARLA 蓝图枚举类
    
    包含所有CARLA蓝图库中的蓝图标识符, 目前以 CARLA 0.9.16 版本为准
    参考: https://carla.readthedocs.io/en/latest/bp_library/
    """
    
    # AI 控制器
    CONTROLLER_AI_WALKER = 'controller.ai.walker'
    
    # 传感器 - 相机
    SENSOR_CAMERA_COSMOS_VISUALIZATION = 'sensor.camera.cosmos_visualization'
    SENSOR_CAMERA_DEPTH = 'sensor.camera.depth'
    SENSOR_CAMERA_DVS = 'sensor.camera.dvs'
    SENSOR_CAMERA_INSTANCE_SEGMENTATION = 'sensor.camera.instance_segmentation'
    SENSOR_CAMERA_NORMALS = 'sensor.camera.normals'
    SENSOR_CAMERA_OPTICAL_FLOW = 'sensor.camera.optical_flow'
    SENSOR_CAMERA_RGB = 'sensor.camera.rgb'
    SENSOR_CAMERA_SEMANTIC_SEGMENTATION = 'sensor.camera.semantic_segmentation'
    
    # 传感器 - 激光雷达
    SENSOR_LIDAR_RAY_CAST = 'sensor.lidar.ray_cast'
    SENSOR_LIDAR_RAY_CAST_SEMANTIC = 'sensor.lidar.ray_cast_semantic'
    
    # 传感器 - 其他
    SENSOR_OTHER_COLLISION = 'sensor.other.collision'
    SENSOR_OTHER_GNSS = 'sensor.other.gnss'
    SENSOR_OTHER_IMU = 'sensor.other.imu'
    SENSOR_OTHER_LANE_INVASION = 'sensor.other.lane_invasion'
    SENSOR_OTHER_OBSTACLE = 'sensor.other.obstacle'
    SENSOR_OTHER_RADAR = 'sensor.other.radar'
    SENSOR_OTHER_RSS = 'sensor.other.rss'
    SENSOR_OTHER_V2X = 'sensor.other.v2x'
    SENSOR_OTHER_V2X_CUSTOM = 'sensor.other.v2x_custom'
    
    # 静态物体
    STATIC_PROP_ADVERTISEMENT = 'static.prop.advertisement'
    STATIC_PROP_APOROSATREE = 'static.prop.aporosatree'
    STATIC_PROP_ATM = 'static.prop.atm'
    STATIC_PROP_BARBEQUE = 'static.prop.barbeque'
    STATIC_PROP_BARREL = 'static.prop.barrel'
    STATIC_PROP_BIN = 'static.prop.bin'
    STATIC_PROP_BOX01 = 'static.prop.box01'
    STATIC_PROP_BOX02 = 'static.prop.box02'
    STATIC_PROP_BOX03 = 'static.prop.box03'
    STATIC_PROP_BRIEFCASE = 'static.prop.briefcase'
    STATIC_PROP_BROKENTILE01 = 'static.prop.brokentile01'
    STATIC_PROP_BROKENTILE02 = 'static.prop.brokentile02'
    STATIC_PROP_BROKENTILE03 = 'static.prop.brokentile03'
    STATIC_PROP_BROKENTILE04 = 'static.prop.brokentile04'
    STATIC_PROP_BUSSTOP = 'static.prop.busstop'
    STATIC_PROP_BUSSTOPLB = 'static.prop.busstoplb'
    STATIC_PROP_CALIBRATOR = 'static.prop.calibrator'
    STATIC_PROP_CHAINBARRIER = 'static.prop.chainbarrier'
    STATIC_PROP_CHAINBARRIEREND = 'static.prop.chainbarrierend'
    STATIC_PROP_CLOTHCONTAINER = 'static.prop.clothcontainer'
    STATIC_PROP_CLOTHESLINE = 'static.prop.clothesline'
    STATIC_PROP_COLACAN = 'static.prop.colacan'
    STATIC_PROP_CONSTRUCTIONCONE = 'static.prop.constructioncone'
    STATIC_PROP_CONTAINER = 'static.prop.container'
    STATIC_PROP_COCONUTPALM = 'static.prop.coconutpalm'
    STATIC_PROP_CREASEDBOX01 = 'static.prop.creasedbox01'
    STATIC_PROP_CREASEDBOX02 = 'static.prop.creasedbox02'
    STATIC_PROP_CREASEDBOX03 = 'static.prop.creasedbox03'
    STATIC_PROP_CYPRESSTREE = 'static.prop.cypresstree'
    STATIC_PROP_DIRTDEBRIS01 = 'static.prop.dirtdebris01'
    STATIC_PROP_DIRTDEBRIS02 = 'static.prop.dirtdebris02'
    STATIC_PROP_DIRTDEBRIS03 = 'static.prop.dirtdebris03'
    STATIC_PROP_DOGHOUSE = 'static.prop.doghouse'
    STATIC_PROP_FOODCART = 'static.prop.foodcart'
    STATIC_PROP_FOUNTAIN = 'static.prop.fountain'
    STATIC_PROP_GARBAGE01 = 'static.prop.garbage01'
    STATIC_PROP_GARBAGE02 = 'static.prop.garbage02'
    STATIC_PROP_GARBAGE03 = 'static.prop.garbage03'
    STATIC_PROP_GARBAGE04 = 'static.prop.garbage04'
    STATIC_PROP_GARBAGE05 = 'static.prop.garbage05'
    STATIC_PROP_GARBAGE06 = 'static.prop.garbage06'
    STATIC_PROP_GARDENLAMP = 'static.prop.gardenlamp'
    STATIC_PROP_GLASSCONTAINER = 'static.prop.glasscontainer'
    STATIC_PROP_HAYBALELB = 'static.prop.haybalelb'
    STATIC_PROP_GNOME = 'static.prop.gnome'
    STATIC_PROP_GUITARCASE = 'static.prop.guitarcase'
    STATIC_PROP_IRONPLANK = 'static.prop.ironplank'
    STATIC_PROP_KIOSK_01 = 'static.prop.kiosk_01'
    STATIC_PROP_MAILBOX = 'static.prop.mailbox'
    STATIC_PROP_MAPTABLE = 'static.prop.maptable'
    STATIC_PROP_MESH = 'static.prop.mesh'
    STATIC_PROP_MOTORHELMET = 'static.prop.motorhelmet'
    STATIC_PROP_PERGOLA = 'static.prop.pergola'
    STATIC_PROP_PLASTICBAG = 'static.prop.plasticbag'
    STATIC_PROP_PLANTPOT01 = 'static.prop.plantpot01'
    STATIC_PROP_PLANTPOT02 = 'static.prop.plantpot02'
    STATIC_PROP_PLANTPOT03 = 'static.prop.plantpot03'
    STATIC_PROP_PLANTPOT04 = 'static.prop.plantpot04'
    STATIC_PROP_PLANTPOT05 = 'static.prop.plantpot05'
    STATIC_PROP_PLANTPOT06 = 'static.prop.plantpot06'
    STATIC_PROP_PLANTPOT07 = 'static.prop.plantpot07'
    STATIC_PROP_PLANTPOT08 = 'static.prop.plantpot08'
    STATIC_PROP_PLATFORMGARBAGE01 = 'static.prop.platformgarbage01'
    STATIC_PROP_PURSE = 'static.prop.purse'
    STATIC_PROP_SHOPPINGBAG = 'static.prop.shoppingbag'
    STATIC_PROP_SHOPPINGCART = 'static.prop.shoppingcart'
    STATIC_PROP_SHOPPINGTROLLEY = 'static.prop.shoppingtrolley'
    STATIC_PROP_SLIDE = 'static.prop.slide'
    STATIC_PROP_STREETBARRIER = 'static.prop.streetbarrier'
    STATIC_PROP_STREETFOUNTAIN = 'static.prop.streetfountain'
    STATIC_PROP_STREETSIGN = 'static.prop.streetsign'
    STATIC_PROP_STREETSIGN01 = 'static.prop.streetsign01'
    STATIC_PROP_STREETSIGN04 = 'static.prop.streetsign04'
    STATIC_PROP_SWING = 'static.prop.swing'
    STATIC_PROP_SWINGCOUCH = 'static.prop.swingcouch'
    STATIC_PROP_TABLE = 'static.prop.table'
    STATIC_PROP_TRAFFICCONE01 = 'static.prop.trafficcone01'
    STATIC_PROP_TRAFFICCONE02 = 'static.prop.trafficcone02'
    STATIC_PROP_TRAFFICWARNING = 'static.prop.trafficwarning'
    STATIC_PROP_TRAMPOLINE = 'static.prop.trampoline'
    STATIC_PROP_TRASHBAG = 'static.prop.trashbag'
    STATIC_PROP_TRASHCAN01 = 'static.prop.trashcan01'
    STATIC_PROP_TRASHCAN02 = 'static.prop.trashcan02'
    STATIC_PROP_TRASHCAN03 = 'static.prop.trashcan03'
    STATIC_PROP_TRASHCAN04 = 'static.prop.trashcan04'
    STATIC_PROP_TRASHCAN05 = 'static.prop.trashcan05'
    STATIC_PROP_TRAVELCASE = 'static.prop.travelcase'
    STATIC_PROP_VENDINGMACHINE = 'static.prop.vendingmachine'
    STATIC_PROP_WARNINGACCIDENT = 'static.prop.warningaccident'
    STATIC_PROP_WARNINGCONSTRUCTION = 'static.prop.warningconstruction'
    STATIC_PROP_WATERINGCAN = 'static.prop.wateringcan'
    STATIC_PROP_BIKE_HELMET = 'static.prop.bike helmet'
    STATIC_TRIGGER_FRICTION = 'static.trigger.friction'
    
    # 车辆
    VEHICLE_AUDI_A2 = 'vehicle.audi.a2'
    VEHICLE_AUDI_ETRON = 'vehicle.audi.etron'
    VEHICLE_AUDI_TT = 'vehicle.audi.tt'
    VEHICLE_BMW_GRANDTOURER = 'vehicle.bmw.grandtourer'
    VEHICLE_CARLAMOTORS_CARLACOLA = 'vehicle.carlamotors.carlacola'
    VEHICLE_CARLAMOTORS_EUROPEAN_HGV = 'vehicle.carlamotors.european_hgv'
    VEHICLE_CARLAMOTORS_FIRETRUCK = 'vehicle.carlamotors.firetruck'
    VEHICLE_CHEVROLET_IMPALA = 'vehicle.chevrolet.impala'
    VEHICLE_CITROEN_C3 = 'vehicle.citroen.c3'
    VEHICLE_DODGE_CHARGER_2020 = 'vehicle.dodge.charger_2020'
    VEHICLE_DODGE_CHARGER_POLICE = 'vehicle.dodge.charger_police'
    VEHICLE_DODGE_CHARGER_POLICE_2020 = 'vehicle.dodge.charger_police_2020'
    VEHICLE_FORD_AMBULANCE = 'vehicle.ford.ambulance'
    VEHICLE_FORD_CROWN = 'vehicle.ford.crown'
    VEHICLE_FORD_MUSTANG = 'vehicle.ford.mustang'
    VEHICLE_JEEP_WRANGLER_RUBICON = 'vehicle.jeep.wrangler_rubicon'
    VEHICLE_LINCOLN_MKZ_2017 = 'vehicle.lincoln.mkz_2017'
    VEHICLE_LINCOLN_MKZ_2020 = 'vehicle.lincoln.mkz_2020'
    VEHICLE_MERCEDES_COUPE = 'vehicle.mercedes.coupe'
    VEHICLE_MERCEDES_COUPE_2020 = 'vehicle.mercedes.coupe_2020'
    VEHICLE_MERCEDES_SPRINTER = 'vehicle.mercedes.sprinter'
    VEHICLE_MICRO_MICROLINO = 'vehicle.micro.microlino'
    VEHICLE_MINI_COOPER_S = 'vehicle.mini.cooper_s'
    VEHICLE_MITSUBISHI_FUSOROSA = 'vehicle.mitsubishi.fusorosa'
    VEHICLE_MINI_COOPER_S_2021 = 'vehicle.mini.cooper_s_2021'
    VEHICLE_NISSAN_MICRA = 'vehicle.nissan.micra'
    VEHICLE_NISSAN_PATROL = 'vehicle.nissan.patrol'
    VEHICLE_NISSAN_PATROL_2021 = 'vehicle.nissan.patrol_2021'
    VEHICLE_SEAT_LEON = 'vehicle.seat.leon'
    VEHICLE_TESLA_CYBERTRUCK = 'vehicle.tesla.cybertruck'
    VEHICLE_TESLA_MODEL3 = 'vehicle.tesla.model3'
    VEHICLE_TOYOTA_PRIUS = 'vehicle.toyota.prius'
    VEHICLE_VOLKSWAGEN_T2 = 'vehicle.volkswagen.t2'
    VEHICLE_VOLKSWAGEN_T2_2021 = 'vehicle.volkswagen.t2_2021'
    
    # 摩托车/自行车
    VEHICLE_VESPA_ZX125 = 'vehicle.vespa.zx125'
    VEHICLE_YAMAHA_YZF = 'vehicle.yamaha.yzf'
    VEHICLE_HARLEY_DAVIDSON_LOW_RIDER = 'vehicle.harley-davidson.low_rider'
    VEHICLE_KAWASAKI_NINJA = 'vehicle.kawasaki.ninja'
    VEHICLE_GAZELLE_OMAFIETS = 'vehicle.gazelle.omafiets'
    VEHICLE_DIAMONDBACK_CENTURY = 'vehicle.diamondback.century'
    VEHICLE_BH_CROSSBIKE = 'vehicle.bh.crossbike'
    
    # 工具类
    UTIL_ACTOR_EMPTY = 'util.actor.empty'
    
    # 行人
    WALKER_PEDESTRIAN_0001 = 'walker.pedestrian.0001'
    WALKER_PEDESTRIAN_0002 = 'walker.pedestrian.0002'
    WALKER_PEDESTRIAN_0003 = 'walker.pedestrian.0003'
    WALKER_PEDESTRIAN_0004 = 'walker.pedestrian.0004'
    WALKER_PEDESTRIAN_0005 = 'walker.pedestrian.0005'
    WALKER_PEDESTRIAN_0006 = 'walker.pedestrian.0006'
    WALKER_PEDESTRIAN_0007 = 'walker.pedestrian.0007'
    WALKER_PEDESTRIAN_0008 = 'walker.pedestrian.0008'
    WALKER_PEDESTRIAN_0009 = 'walker.pedestrian.0009'
    WALKER_PEDESTRIAN_0010 = 'walker.pedestrian.0010'
    WALKER_PEDESTRIAN_0011 = 'walker.pedestrian.0011'
    WALKER_PEDESTRIAN_0012 = 'walker.pedestrian.0012'
    WALKER_PEDESTRIAN_0013 = 'walker.pedestrian.0013'
    WALKER_PEDESTRIAN_0014 = 'walker.pedestrian.0014'
    WALKER_PEDESTRIAN_0015 = 'walker.pedestrian.0015'
    WALKER_PEDESTRIAN_0016 = 'walker.pedestrian.0016'
    WALKER_PEDESTRIAN_0017 = 'walker.pedestrian.0017'
    WALKER_PEDESTRIAN_0018 = 'walker.pedestrian.0018'
    WALKER_PEDESTRIAN_0019 = 'walker.pedestrian.0019'
    WALKER_PEDESTRIAN_0020 = 'walker.pedestrian.0020'
    WALKER_PEDESTRIAN_0021 = 'walker.pedestrian.0021'
    WALKER_PEDESTRIAN_0022 = 'walker.pedestrian.0022'
    WALKER_PEDESTRIAN_0023 = 'walker.pedestrian.0023'
    WALKER_PEDESTRIAN_0024 = 'walker.pedestrian.0024'
    WALKER_PEDESTRIAN_0025 = 'walker.pedestrian.0025'
    WALKER_PEDESTRIAN_0026 = 'walker.pedestrian.0026'
    WALKER_PEDESTRIAN_0027 = 'walker.pedestrian.0027'
    WALKER_PEDESTRIAN_0028 = 'walker.pedestrian.0028'
    WALKER_PEDESTRIAN_0029 = 'walker.pedestrian.0029'
    WALKER_PEDESTRIAN_0030 = 'walker.pedestrian.0030'
    WALKER_PEDESTRIAN_0031 = 'walker.pedestrian.0031'
    WALKER_PEDESTRIAN_0032 = 'walker.pedestrian.0032'
    WALKER_PEDESTRIAN_0033 = 'walker.pedestrian.0033'
    WALKER_PEDESTRIAN_0034 = 'walker.pedestrian.0034'
    WALKER_PEDESTRIAN_0035 = 'walker.pedestrian.0035'
    WALKER_PEDESTRIAN_0036 = 'walker.pedestrian.0036'
    WALKER_PEDESTRIAN_0037 = 'walker.pedestrian.0037'
    WALKER_PEDESTRIAN_0038 = 'walker.pedestrian.0038'
    WALKER_PEDESTRIAN_0039 = 'walker.pedestrian.0039'
    WALKER_PEDESTRIAN_0040 = 'walker.pedestrian.0040'
    WALKER_PEDESTRIAN_0041 = 'walker.pedestrian.0041'
    WALKER_PEDESTRIAN_0042 = 'walker.pedestrian.0042'
    WALKER_PEDESTRIAN_0043 = 'walker.pedestrian.0043'
    WALKER_PEDESTRIAN_0044 = 'walker.pedestrian.0044'
    WALKER_PEDESTRIAN_0045 = 'walker.pedestrian.0045'
    WALKER_PEDESTRIAN_0046 = 'walker.pedestrian.0046'
    WALKER_PEDESTRIAN_0047 = 'walker.pedestrian.0047'
    WALKER_PEDESTRIAN_0048 = 'walker.pedestrian.0048'
    WALKER_PEDESTRIAN_0049 = 'walker.pedestrian.0049'
    WALKER_PEDESTRIAN_0050 = 'walker.pedestrian.0050'
    WALKER_PEDESTRIAN_0051 = 'walker.pedestrian.0051'
    WALKER_PEDESTRIAN_0052 = 'walker.pedestrian.0052'

    @classmethod
    def walkers(cls) -> list[str]:
        """获取所有行人蓝图"""
        return [walker.value for walker in cls.__members__.values() if walker.value.startswith('walker.pedestrian.')]
    
    @classmethod
    def vehicles(cls, filter: Literal[None, 'car', 'large', 'emergency', '2wheel'] = None) -> list[str]:
        """获取所有车辆蓝图
        
        Args:
            filter (Literal[None, 'car', 'large', 'emergency', '2wheel']): 过滤条件
                None: 不进行过滤
                'car': 仅获取小型家用车, 含轿车和SUV和小型货车
                'large': 仅获取大型车辆
                'emergency': 仅获取应急车辆
                '2wheel': 仅获取两轮车
        
        Returns:
            list[str]: 符合条件的车辆蓝图列表
        """
        # print("type:",type(cls)," ",cls)
        # print("self.__members__:",cls.__members__)
        all_vehicles = [vehicle.value for vehicle in cls.__members__.values() if vehicle.value.startswith('vehicle.')]
        
        if filter is None:
            return all_vehicles
        
        # 两轮车: 摩托车、踏板车、自行车
        two_wheel_vehicles = {
            'vehicle.vespa.zx125',
            'vehicle.yamaha.yzf',
            'vehicle.harley-davidson.low_rider',
            'vehicle.kawasaki.ninja',
            'vehicle.gazelle.omafiets',
            'vehicle.diamondback.century',
            'vehicle.bh.crossbike',
        }
        
        # 应急车辆: 消防车、救护车、警车
        emergency_vehicles = {
            'vehicle.carlamotors.firetruck',
            'vehicle.ford.ambulance',
            'vehicle.dodge.charger_police_2020',
        }
        
        # 大型车辆: 重型货车、大型货车、面包车、皮卡、公交车、大型应急车辆
        large_vehicles = {
            'vehicle.carlamotors.european_hgv',
            'vehicle.volkswagen.t2',
            'vehicle.mitsubishi.fusorosa',
            'vehicle.mercedes.sprinter',
            'vehicle.tesla.cybertruck',
            'vehicle.carlamotors.firetruck',
            'vehicle.ford.ambulance',
        }
        
        if filter == '2wheel':
            return [v for v in all_vehicles if v in two_wheel_vehicles]
        elif filter == 'emergency':
            return [v for v in all_vehicles if v in emergency_vehicles]
        elif filter == 'large':
            return [v for v in all_vehicles if v in large_vehicles]
        elif filter == 'car':
            # 小型家用车: 排除两轮车、应急车辆、大型车辆, 但保留皮卡和小型货车
            excluded = two_wheel_vehicles | emergency_vehicles | large_vehicles
            cars = [v for v in all_vehicles if v not in excluded]
            # 保留皮卡和小型货车
            cars.extend(['vehicle.mercedes.sprinter', 'vehicle.tesla.cybertruck'])
            return cars
        
        return all_vehicles
