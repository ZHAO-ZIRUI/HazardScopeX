from enum import Enum
from typing import Literal


class CarlaSpawnPoints(Enum):
    """CARLA spawnpoint 枚举类
    
    """

    'Carla/Maps/SUSTech_COE_ParkingLot' = {
        'straight_roads': [],
        'turning_roads': [],
        'entry_lanes': [],
        'export_lanes': [],
        'crossroads': [],
        'T_shaped_intersections': [],
        'circular_island_roads': [],
    },
    'Carla/Maps/Town10HD_Opt' = {
        'straight_roads': [],
        'turning_roads': [],
        'entry_lanes': [],
        'export_lanes': [],
        'crossroads': [],
        'T_shaped_intersections': [],
        'circular_island_roads': [],
    },
    'Carla/Maps/Town04' = {
        'straight_roads': [],
        'turning_roads': [],
        'entry_lanes': [],
        'export_lanes': [],
        'crossroads': [],
        'T_shaped_intersections': [],
        'circular_island_roads': [],
    },
    
    @classmethod
    def straight_roads(cls) -> list[int]:
        # return [walker.value for walker in cls.__members__.values() if walker.value.startswith('walker.pedestrian.')]
        return 

    @classmethod
    def turning_roads(cls) -> list[int]:
        return
    
    @classmethod
    def entry_lanes(cls) -> list[int]:
        return
    
    @classmethod
    def export_lanes(cls) -> list[int]:
        return
    
    @classmethod
    def crossroads(cls) -> list[int]:
        return
    
    @classmethod
    def T_shaped_intersections(cls) -> list[int]:
        return

    @classmethod
    def circular_island_roads(cls) -> list[int]:
        return