from enum import Enum


class CarlaMaps(Enum):
    """CARLA 地图枚举类
    
    包含所有CARLA地图库中的地图标识符, 目前以 CARLA 0.9.16 版本为准
    """
    
    TOWN_01 = 'Town01'
    TOWN_02 = 'Town02'
    TOWN_03 = 'Town03'
    TOWN_04 = 'Town04'
    TOWN_05 = 'Town05'
    TOWN_06 = 'Town06'
    TOWN_07 = 'Town07'
    # TOWN_08 = 'Town08'  # 仅用于 CARLA Leaderboard
    # TOWN_09 = 'Town09'  # 仅用于 CARLA Leaderboard
    TOWN_10 = 'Town10'
    TOWN_11 = 'Town11'
    TOWN_12 = 'Town12'
    TOWN_13 = 'Town13'
    TOWN_14 = 'Town14'
    TOWN_15 = 'Town15'