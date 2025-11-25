from enum import Enum


class CarlaBlueprints(Enum):
    """CARLA 蓝图枚举类
    
    包含所有CARLA蓝图库中的蓝图标识符
    参考: https://carla.readthedocs.io/en/latest/bp_library/
    """
    
    # AI 控制器
    CONTROLLER_AI_WALKER = 'controller.ai.walker'
    
    # 传感器 - 相机
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
    
    # 静态物体
    STATIC_PROP_ADVERTISEMENT = 'static.prop.advertisement'
    STATIC_PROP_ATM = 'static.prop.atm'
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
    STATIC_PROP_CALIBRATOR = 'static.prop.calibrator'
    STATIC_PROP_CHAINBARRIER = 'static.prop.chainbarrier'
    STATIC_PROP_CHAINBARRIERGATE = 'static.prop.chainbarriergate'
    STATIC_PROP_CLOTHCONTAINER = 'static.prop.clothcontainer'
    STATIC_PROP_CLOTHESLINE = 'static.prop.clothesline'
    STATIC_PROP_COLACAN = 'static.prop.colacan'
    STATIC_PROP_CONSTRUCTIONCONE = 'static.prop.constructioncone'
    STATIC_PROP_CONTAINER = 'static.prop.container'
    STATIC_PROP_CREASEDBOX01 = 'static.prop.creasedbox01'
    STATIC_PROP_CREASEDBOX02 = 'static.prop.creasedbox02'
    STATIC_PROP_CREASEDBOX03 = 'static.prop.creasedbox03'
    STATIC_PROP_DIRTDEBRIS01 = 'static.prop.dirtdebris01'
    STATIC_PROP_DIRTDEBRIS02 = 'static.prop.dirtdebris02'
    STATIC_PROP_DIRTDEBRIS03 = 'static.prop.dirtdebris03'
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
    STATIC_PROP_GNOME = 'static.prop.gnome'
    STATIC_PROP_GUITARCASE = 'static.prop.guitarcase'
    STATIC_PROP_IRONPLANK = 'static.prop.ironplank'
    STATIC_PROP_KIOSK_01 = 'static.prop.kiosk_01'
    STATIC_PROP_MAILBOX = 'static.prop.mailbox'
    STATIC_PROP_MAPTABLE = 'static.prop.maptable'
    STATIC_PROP_MESH_01 = 'static.prop.mesh_01'
    STATIC_PROP_MESH_02 = 'static.prop.mesh_02'
    STATIC_PROP_MESH_03 = 'static.prop.mesh_03'
    STATIC_PROP_MESH_04 = 'static.prop.mesh_04'
    STATIC_PROP_MESH_05 = 'static.prop.mesh_05'
    STATIC_PROP_MESH_06 = 'static.prop.mesh_06'
    STATIC_PROP_MESH_07 = 'static.prop.mesh_07'
    STATIC_PROP_MESH_08 = 'static.prop.mesh_08'
    STATIC_PROP_MESH_09 = 'static.prop.mesh_09'
    STATIC_PROP_MESH_10 = 'static.prop.mesh_10'
    STATIC_PROP_MESH_11 = 'static.prop.mesh_11'
    STATIC_PROP_MESH_12 = 'static.prop.mesh_12'
    STATIC_PROP_MOTORHELMET = 'static.prop.motorhelmet'
    STATIC_PROP_PERGOLA = 'static.prop.pergola'
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
    VEHICLE_MITSUBISH_FUSOROSA = 'vehicle.mitsubishi.fusorosa'
    
    # 摩托车/自行车
    VEHICLE_VESPA_ZX125 = 'vehicle.vespa.zx125'
    VEHICLE_YAMAHA_YZF = 'vehicle.yamaha.yzf'
    VEHICLE_HARLEY_DAVIDSON_LOW_RIDER = 'vehicle.harley-davidson.low_rider'
    VEHICLE_KAWASAKI_NINJA = 'vehicle.kawasaki.ninja'
    VEHICLE_GAZELLE_OMAFIETS = 'vehicle.gazelle.omafiets'
    VEHICLE_DIAMONDBACK_CENTURY = 'vehicle.diamondback.century'
    VEHICLE_BH_CROSSBIKE = 'vehicle.bh.crossbike'
    
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

    @classmethod
    def LARGE_VEHICLES(cls) -> list[str]:
        return [
            cls.VEHICLE_CARLAMOTORS_EUROPEAN_HGV.value,
            cls.VEHICLE_MERCEDES_SPRINTER.value,
            cls.VEHICLE_VOLKSWAGEN_T2.value,
            cls.VEHICLE_TESLA_CYBERTRUCK.value,
            cls.VEHICLE_MITSUBISH_FUSOROSA.value,
            cls.VEHICLE_CARLAMOTORS_FIRETRUCK.value,
        ]

    @classmethod
    def TWO_WHEELS(cls) -> list[str]:
        return [
            cls.VEHICLE_VESPA_ZX125.value,
            cls.VEHICLE_YAMAHA_YZF.value,
            cls.VEHICLE_HARLEY_DAVIDSON_LOW_RIDER.value,
            cls.VEHICLE_KAWASAKI_NINJA.value,
            cls.VEHICLE_GAZELLE_OMAFIETS.value,
            cls.VEHICLE_DIAMONDBACK_CENTURY.value,
            cls.VEHICLE_BH_CROSSBIKE.value,
            cls.VEHICLE_DIAMONDBACK_CENTURY.value,
        ]

    @classmethod
    def NORMAL_TRAFFIC(cls) -> list[str]:
        """返回所有以 VEHICLE_ 开头的车辆蓝图"""
        return [
            member.value
            for name, member in cls.__members__.items()
            if name.startswith('VEHICLE_')
        ]