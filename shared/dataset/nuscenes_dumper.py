import os
import sqlite3
import uuid
import datetime
import json
import time
import carla
import numpy as np
from pathlib import Path
from typing import TYPE_CHECKING, Tuple, List,Iterable
from typing_extensions import Self

from pyquaternion import Quaternion
from shared.dataset import DatasetDumper
from shared.simulator import CarlaSensor
from shared.data import BaseData, Image, PointCloud
from shared.utils import PostInitMeta

if TYPE_CHECKING:
    from shared.simulator import CarlaContext

class NuScenesDB(metaclass=PostInitMeta):

    def __init__(self, db_path: str = ":memory:"):
        """初始化 NuScenes 数据库
        
        Args:
            db_path (str, optional): 数据库路径，默认为 ":memory:" 表示使用内存数据库。如果传入文件路径，则创建文件数据库.
        """
        self._db_path = db_path
        self._conn, self._cursor = self._create_database()
        
    
    @property
    def is_memory_db(self) -> bool:
        """检查是否是内存数据库
        
        Returns:
            bool: 如果是内存数据库返回 True, 否则返回 False
        """
        return self._db_path == ":memory:"

    def __post_init__(self) -> Self:
        self._create_tables()
        return self

    def __enter__(self) -> Self:
        return self
    
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
        
    def get_nuscenes_token(self) -> str:
        return str(uuid.uuid4().hex)
    
    def get_nuscenes_timestamp(self, timestamp: float) -> int:
        """将秒级时间戳转换为微秒级时间戳
        
        Args:
            timestamp (float): 秒级时间戳
            
        Returns:
            int: 微秒级时间戳
        """
        return int(timestamp * NuScenesDumper.TIMESTAMP_TO_MICROSECONDS)   

    def _decode_json_list(self, json_str: str) -> List[float]:
        return json.loads(json_str)
    
    def _format_json(self, obj) -> str:
        """格式化 JSON 输出，使用 tab 缩进和换行
        
        Args:
            obj: 要序列化的对象
            
        Returns:
            str: 格式化后的 JSON 字符串
        """
        return json.dumps(obj, indent='\t', ensure_ascii=False)
    
    def _create_database(self) -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
        is_memory_db = self._db_path == ":memory:"
        
        if not is_memory_db and os.path.exists(self._db_path):
            raise FileExistsError(f"File {self._db_path} already exists")
        
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        cursor = conn.cursor()

        return conn, cursor
        
    def _create_tables(self):
        self._create_table_log()
        self._create_table_map()
        self._create_table_pair_log_map()
        self._create_table_scene()
        self._create_table_sample()
        self._create_table_sample_data()
        self._create_table_ego_pose()
        self._create_table_calibrated_sensor()
        self._create_table_sensor()
        self._create_table_visibility()
        self._create_table_attribute()
        self._create_table_category()
        self._create_table_instance()
        self._create_table_sample_annotation()
        self._create_table_lidarseg()
        self._create_table_can_bus_pose()
        self._create_table_can_bus_steeranglefeedback()
    
    def _create_table_log(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS log (
                token TEXT PRIMARY KEY,
                logfile TEXT NOT NULL,
                vehicle TEXT NOT NULL,
                date_captured TEXT NOT NULL,
                location TEXT NOT NULL
            )
        ''')
        
    def _create_table_map(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS map (
                token TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                filename TEXT NOT NULL
            )
        ''')
        
    def _create_table_pair_log_map(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS pair_log_map (
                log_token TEXT NOT NULL,
                map_token TEXT NOT NULL,
                FOREIGN KEY (log_token) REFERENCES log (token),
                FOREIGN KEY (map_token) REFERENCES map (token)
            )
        ''')
        
    def _create_table_scene(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS scene (
                token TEXT PRIMARY KEY,
                log_token TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (log_token) REFERENCES log (token)
            )
        ''')

    def _create_table_sample(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS sample (
                token TEXT PRIMARY KEY,
                scene_token TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                prev TEXT,
                next TEXT,
                FOREIGN KEY (scene_token) REFERENCES scene (token),
                FOREIGN KEY (prev) REFERENCES sample (token),
                FOREIGN KEY (next) REFERENCES sample (token)
            )
        ''')
        
    def _create_table_sample_data(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS sample_data (
                token TEXT PRIMARY KEY,
                sample_token TEXT NOT NULL,
                ego_pose_token TEXT NOT NULL,
                calibrated_sensor_token TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                fileformat TEXT NOT NULL,
                is_key_frame BOOLEAN NOT NULL,
                height INTEGER DEFAULT 0,
                width INTEGER DEFAULT 0,
                filename TEXT NOT NULL,
                prev TEXT,
                next TEXT,
                FOREIGN KEY (sample_token) REFERENCES sample (token),
                FOREIGN KEY (prev) REFERENCES sample_data (token),
                FOREIGN KEY (next) REFERENCES sample_data (token),
                FOREIGN KEY (ego_pose_token) REFERENCES ego_pose (token),
                FOREIGN KEY (calibrated_sensor_token) REFERENCES calibrated_sensor (token)
            )
        ''')
        
    def _create_table_ego_pose(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS ego_pose (
                token TEXT PRIMARY KEY,
                timestamp INTEGER NOT NULL,
                translation TEXT NOT NULL,  -- Store as JSON string
                rotation TEXT NOT NULL      -- Store as JSON string
            )
        ''')
        
    def _create_table_calibrated_sensor(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS calibrated_sensor (
                token TEXT PRIMARY KEY,
                sensor_token TEXT NOT NULL,
                translation TEXT NOT NULL,      -- Store as JSON string
                rotation TEXT NOT NULL,         -- Store as JSON string
                camera_intrinsic TEXT NOT NULL, -- Store as JSON string
                FOREIGN KEY (sensor_token) REFERENCES sensor (token)
            )
        ''')
        
    def _create_table_sensor(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor (
                token TEXT PRIMARY KEY,
                channel TEXT NOT NULL,
                modality TEXT NOT NULL
            )
        ''')

    def _create_table_visibility(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS visibility (
                token TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                level TEXT NOT NULL
            )
        ''')
        
    def _create_table_attribute(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS attribute (
                token TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                name TEXT NOT NULL
            )
        ''')

    def _create_table_category(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS category (
                token TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                seg_index INTEGER NOT NULL
            )
        ''')

    def _create_table_instance(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS instance (
                token TEXT PRIMARY KEY,
                category_token TEXT NOT NULL,
                first_annotation_token TEXT,
                last_annotation_token TEXT,
                FOREIGN KEY (category_token) REFERENCES category (token)
            )
        ''')
        
    def _create_table_sample_annotation(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS sample_annotation (
                token TEXT PRIMARY KEY,
                sample_token TEXT NOT NULL,
                visibility_token TEXT NOT NULL,
                attribute_tokens TEXT NOT NULL,  -- Store as JSON string
                instance_token TEXT NOT NULL,
                translation TEXT NOT NULL,      -- Store as JSON string
                size TEXT NOT NULL,             -- Store as JSON string
                rotation TEXT NOT NULL,         -- Store as JSON string
                num_lidar_pts INTEGER NOT NULL,
                num_radar_pts INTEGER NOT NULL,
                next TEXT,
                prev TEXT,
                FOREIGN KEY (sample_token) REFERENCES sample (token),
                FOREIGN KEY (visibility_token) REFERENCES visibility (token),
                FOREIGN KEY (instance_token) REFERENCES instance (token),
                FOREIGN KEY (prev) REFERENCES sample_annotation (token),
                FOREIGN KEY (next) REFERENCES sample_annotation (token)
            )
        ''')
        
    def _create_table_lidarseg(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS lidarseg (
                token TEXT PRIMARY KEY,
                sample_data_token TEXT NOT NULL,
                filename TEXT NOT NULL
            )
        ''')

    def _create_table_can_bus_pose(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS can_bus_pose (
                token TEXT PRIMARY KEY,
                utime INTEGER NOT NULL,
                vel TEXT NOT NULL,  -- Store as JSON string
                accel TEXT NOT NULL,  -- Store as JSON string
                rotation_rate TEXT NOT NULL  -- Store as JSON string
            )
        ''')

    def _create_table_can_bus_steeranglefeedback(self):
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS can_bus_steeranglefeedback (
                token TEXT PRIMARY KEY,
                utime INTEGER NOT NULL,
                value TEXT NOT NULL  -- Store as JSON string
            )
        ''')


    def add_log(self, *,
                dtime: datetime.datetime = datetime.datetime.now(),
                vehicle: str = 'UNKNOW', 
                location: str = 'UNKNOW',
                map_token: str) -> str:
        """增加一条 log 记录

        Args:
            map_token (str): 指向的 map 记录的 token
            dtime (datetime.datetime, optional): 数据采集的时间. 默认使用当前时间.
            vehicle (str, optional): 采集数据时所用到的车辆描述, 如: 'n18'. 默认为 'UNKNOW'.
            location (str, optional): 数据采集的地点描述. 如: 'singapore-onenorth'. 默认为 'UNKNOW'.

        Returns:
            str: _description_
        """
        token = self.get_nuscenes_token()
        log_file = f"{vehicle}-{dtime.strftime('%Y-%m-%d-%H-%M-%S%z')}"
        date_captured = dtime.strftime("%Y-%m-%d")
        
        # 记录 log 数据
        self._cursor.execute('''
            INSERT INTO log (token, logfile, vehicle, date_captured, location) VALUES (?, ?, ?, ?, ?)
        ''', (token, log_file, vehicle, date_captured, location))
        
        # 记录 log 和 map 的关系
        self._cursor.execute('''
            INSERT INTO pair_log_map (log_token, map_token) VALUES (?, ?)
        ''', (token, map_token))

        self._conn.commit()
        return token

    def add_map(self, *,
                category: str = 'UNKNOWN', 
                filename: str = 'UNKNOWN') -> str:
        """增加一条 map 记录

        Args:
            category (str, optional): 地图的分类描述, 如: 'semantic_prior'. 默认为 'UNKNOWN'.
            filename (str, optional): 地图文件名, 指向地图的占用图像, 如: 'maps/sample.png'. 默认为 'UNKNOWN'.

        Returns:
            str: 插入数据库的 token
        """
        token = self.get_nuscenes_token()
        
        self._cursor.execute('''
            INSERT INTO map (token, category, filename) VALUES (?, ?, ?)
        ''', (token, category, filename))
        
        self._conn.commit()
        return token
    
    def add_scene(self, *,
                  log_token: str,
                  name: str = 'UNKNOWN',
                  description: str = 'UNKNOWN') -> str:
        """增加一条 scene 记录

        Args:
            log_token (str): 指向的 log 记录的 token
            name (str, optional): 场景的名称, 如: 'scene-0061'. 默认为 'UNKNOWN'.
            description (str, optional): 场景的描述, 如: 'Parked truck, construction, ...'. 默认为 'UNKNOWN'.

        Returns: 
            str: 插入数据库的 token
        """
        token = self.get_nuscenes_token()
        
        self._cursor.execute('''
            INSERT INTO scene (token, log_token, name, description) VALUES (?, ?, ?, ?)
        ''', (token, log_token, name, description))
        
        self._conn.commit()
        return token

    def add_sample(self, *,
                   scene_token: str,
                   timestamp: float = time.time(),
                   prev: str = None) -> str:
        """增加一条 sample 记录, 每一个 sample 是一帧采集

        Args:
            scene_token (str): 指向的 scene 记录的 token
            timestamp (float): 时间戳, 采用标准 Unix 时间戳, 单位为秒, 默认使用当前时间戳
            prev (str, optional): 前一个 sample 记录的 token, 默认为 None

        Returns:
            str: 插入数据库的 token
        """
        token = self.get_nuscenes_token()
        timestamp = self.get_nuscenes_timestamp(timestamp)
        
        self._cursor.execute('''
            INSERT INTO sample (token, scene_token, timestamp, prev) VALUES (?, ?, ?, ?)
        ''', (token, scene_token, timestamp, prev))
        
        if prev:
            self._cursor.execute('''
                UPDATE sample SET next = ? WHERE token = ?
            ''', (token, prev))
        self._conn.commit()
        return token
    
    def add_sensor(self, *,
                   channel: str,
                   modality: str) -> str:
        """增加一条 sensor 记录

        Args:
            channel (str, optional): 传感器的通道描述, 如: 'CAM_FRONT'.
            modality (str, optional): 传感器的模态描述, 如: 'camera'.

        Returns:
            str: 插入数据库的 token
        """
        token = self.get_nuscenes_token()
        
        self._cursor.execute('''
            INSERT INTO sensor (token, channel, modality) VALUES (?, ?, ?)
        ''', (token, channel, modality))
        
        self._conn.commit()
        return token
    
    def add_calibrated_sensor(self, *,
                               sensor_token: str,
                               translation: List[float],
                               rotation: List[float],
                               camera_intrinsic: List[float] = list()) -> str:
        """增加一条 calibrated_sensor 记录

        Args:
            sensor_token (str): 指向的 sensor 记录的 token
            translation (list[float]): 平移向量
            rotation (list[float]): 旋转矩阵
            camera_intrinsic (list[float], optional): 如果传感器是相机, 则需要提供相机内参, 默认为空列表

        Returns:
            str: 插入数据库的 token
        """
        token = self.get_nuscenes_token()
        
        # 转换部分数据为 json 格式
        translation = json.dumps(translation)
        rotation = json.dumps(rotation)
        camera_intrinsic = json.dumps(camera_intrinsic)
        
        self._cursor.execute('''
            INSERT INTO calibrated_sensor (token, sensor_token, translation, rotation, camera_intrinsic) VALUES (?, ?, ?, ?, ?)
        ''', (token, sensor_token, translation, rotation, camera_intrinsic))
        
        self._conn.commit()
        return token
    
    def add_ego_pose(self, *,
                     token: str,
                     timestamp: float = time.time(),
                     translation: List[float],
                     rotation: List[float]) -> str:
        """增加一条 ego_pose 记录

        Args:
            token (str, optional): 需要与 sample_data 表中的 token 一致
            timestamp (float, optional): 时间戳, 采用标准 Unix 时间戳, 单位为秒, 默认使用当前时间戳
            translation (list[float]): 平移向量
            rotation (list[float]): 旋转矩阵

        Returns:
            str: 插入数据库的 token
        """
        timestamp = self.get_nuscenes_timestamp(timestamp)
        
        # 转换部分数据为 json 格式
        translation = json.dumps(translation)
        rotation = json.dumps(rotation)
        
        self._cursor.execute('''
            INSERT INTO ego_pose (token, timestamp, translation, rotation) VALUES (?, ?, ?, ?)
        ''', (token, timestamp, translation, rotation))
        
        self._conn.commit()
        return token
    
    def add_sample_data(self, *,
                        token: str,
                        sample_token: str,
                        ego_pose_token: str,
                        calibrated_sensor_token: str,
                        timestamp: float = time.time(),
                        fileformat: str = 'UNKNOWN',
                        is_key_frame: bool = False,
                        height: int = 0,
                        width: int = 0,
                        filename: str = 'UNKNOWN',
                        prev: str = None) -> str:
        """增加一条 sample_data 记录

        Args:
            token (str, optional): 需要与 ego_pose 表中的 token 一致, 由外部程序确保一致性
            sample_token (str): 指向的 sample 记录的 token
            ego_pose_token (str): 指向的 ego_pose 记录的 token
            calibrated_sensor_token (str): 指向的 calibrated_sensor 记录的 token
            timestamp (float, optional): 时间戳, 采用标准 Unix 时间戳, 单位为秒, 默认使用当前时间戳
            fileformat (str, optional): 文件格式, 如: 'jpg'. 默认为 'UNKNOWN'.
            is_key_frame (bool, optional): 是否为关键帧, 默认为 False.
            height (int, optional): 图像高度, 默认为 0, 传入不为图像时请保持默认.
            width (int, optional): 图像宽度, 默认为 0, 传入不为图像时请保持默认.
            filename (str, optional): 文件名, 默认为 'UNKNOWN'.
            prev (str, optional): 前一个 sample_data 记录的 token, 默认为 None. 

        Returns:
            str: 插入数据库的 token
        """
        timestamp = self.get_nuscenes_timestamp(timestamp)
        
        # 记录新值
        self._cursor.execute('''
            INSERT INTO sample_data (token, sample_token, ego_pose_token, calibrated_sensor_token, timestamp, fileformat, is_key_frame, height, width, filename, prev) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (token, sample_token, ego_pose_token, calibrated_sensor_token, timestamp, fileformat, is_key_frame, height, width, filename, prev))
        
        # 更新前一个 sample_data 记录的 next 值
        if prev:
            self._cursor.execute('''
                UPDATE sample_data SET next = ? WHERE token = ?
            ''', (token, prev))
        
        self._conn.commit()
        return token

    def add_visibility(self, *,
                       token: str = None,
                       description: str,
                       level: str) -> str:
        """增加一条 visibility 记录

        Args:
            description (str): 可见性描述, 如: 'visible'.
            level (str): 可见性等级, 如: 'low'.

        Returns:
            str: 插入数据库的 token
        """
         # token = token or self.get_nuscenes_token()
        self._cursor.execute('''
            INSERT INTO visibility (token, description, level) VALUES (?, ?, ?)
        ''', (token, description, level))
        
        self._conn.commit()
        return token
    
    def add_attribute(self, *,
                      name: str,
                      description: str = 'NOT_SET') -> str:
        """增加一条 attribute 记录

        Args:
            name (str): 属性名称, 如: 'car'.
            description (str, optional): 属性描述, 默认为 'NOT_SET'.

        Returns:
            str: 插入数据库的 token
        """
        token = self.get_nuscenes_token()
        
        self._cursor.execute('''
            INSERT INTO attribute (token, name, description) VALUES (?, ?, ?)
        ''', (token, name, description))
        
        self._conn.commit()
        return token

    def add_category(self, *,
                     index: int,
                     name: str,
                     description: str = 'UNKNOWN') -> str:
        """增加一条 category 记录

        Args:
            name (str): 类别名称, 如: 'car'.
            description (str, optional): 类别描述, 默认为 'UNKNOWN'.

        Returns:
            str: 插入数据库的 token
        """
        token = self.get_nuscenes_token()
        
        self._cursor.execute('''
            INSERT INTO category (token, name, description, seg_index) VALUES (?, ?, ?, ?)
        ''', (token, name, description, index))
        
        self._conn.commit()
        return token
        
    def add_instance(self, *,
                 category_token: str,
                 first_annotation_token: str | None = None) -> str:
        """增加一条 instance 记录

        Args:
            category_token (str): 指向的 category 记录的 token
            first_annotation_token (str, optional): 可以忽略，通常让系统自动维护

        Returns:
            str: 插入数据库的 token
        """
        token = self.get_nuscenes_token()

        # 初始时先不设 first/last，由 update_instance_annotation_links 统一维护
        first_token = ""
        last_token = ""

        self._cursor.execute(
            '''
            INSERT INTO instance (
                token,
                category_token,
                first_annotation_token,
                last_annotation_token
            ) VALUES (?, ?, ?, ?)
            ''',
            (token, category_token, first_token, last_token)
        )

        self._conn.commit()
        return token
    
    def update_instance_annotation_links(self, instance_token: str, annotation_token: str) -> None:
        """
        根据新的 sample_annotation，更新 instance 表中的
        first_annotation_token / last_annotation_token 字段。

        - 如果 instance 目前还没有 first_annotation_token（为空字符串或 NULL），
        则把 first 和 last 都设为当前 annotation。
        - 否则，只更新 last_annotation_token 为当前 annotation。
        """
        # 1. 查询当前 instance 的 first / last
        self._cursor.execute(
            'SELECT first_annotation_token, last_annotation_token FROM instance WHERE token = ?',
            (instance_token,)
        )
        row = self._cursor.fetchone()
        if not row:
            # 理论上不会发生：instance 不存在
            return
        first_token, last_token = row
        # 注意：first_token 可能是 None 或 ""，表示还没设置
        if not first_token:  # None 或 空字符串 都视为未设置
            new_first = annotation_token
            new_last = annotation_token
        else:
            new_first = first_token
            new_last = annotation_token
        self._cursor.execute(
            '''
            UPDATE instance
            SET first_annotation_token = ?, last_annotation_token = ?
            WHERE token = ?
            ''',
            (new_first, new_last, instance_token)
        )
        self._conn.commit()
    
    def add_sample_annotation(self, *,
                               token: str,
                               sample_token: str,
                               visibility_token: str,
                               attribute_tokens: List[str] = [],
                               instance_token: str,
                               translation: List[float],
                               size: List[float],
                               rotation: List[float],
                               num_lidar_pts: int,
                               num_radar_pts: int,
                               prev: str = None) -> str:
        """增加一条 sample_annotation 记录

        Args:
            token (str): 指向的 sample_data 记录的 token
            sample_token (str): 指向的 sample 记录的 token
            visibility_token (str): 指向的 visibility 记录的 token
            attribute_tokens (list[str], optional): 属性记录的 token 列表, 默认为空列表
            instance_token (str): 指向的 instance 记录的 token  
            translation (list[float]): 平移向量
            size (list[float]): 尺寸向量
            rotation (list[float]): 旋转矩阵
            num_lidar_pts (int): 激光雷达点数
            num_radar_pts (int): 雷达点数

        Returns:
            str: 插入数据库的 token
        """        
        # if abs(translation[0]-1) <0.5 or abs(size[0]-1) <0.5:
        #     print("size:",size," translation:",translation)
        # 转换部分数据为 json 格式
        attribute_tokens = json.dumps(attribute_tokens)
        translation = json.dumps(translation)
        size = json.dumps(size)
        rotation = json.dumps(rotation)

        # 查找 prev，该 instance 的前一个 token 记录，默认为 None
        # 如果 last_annotation_token 为空字符串，则 prev 为 None，表示这是第一个 annotation
        self._cursor.execute('''
            SELECT last_annotation_token FROM instance WHERE token = ?
        ''',(instance_token, ))
        result = self._cursor.fetchall()
        if result and result[0][0]:
            prev = result[0][0]  # 非空字符串，表示存在前一个 annotation
        else:
            prev = None  # 空字符串或 None，表示这是第一个 annotation

        # 记录新值
        self._cursor.execute('''
            INSERT INTO sample_annotation (token, sample_token, visibility_token, attribute_tokens, instance_token, translation, size, rotation, num_lidar_pts, num_radar_pts, prev) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (token, sample_token, visibility_token, attribute_tokens, instance_token, translation, size, rotation, num_lidar_pts, num_radar_pts, prev))

        # 更新 instance 表的 last_annotation_token
        self._cursor.execute('''
            UPDATE instance SET last_annotation_token = ? WHERE token = ?
        ''', (token, instance_token))

        # 更新前一个 sample_annotation 记录的 next 值
        if prev:
            self._cursor.execute('''
                UPDATE sample_annotation SET next = ? WHERE token = ?
            ''', (token, prev))

        self._conn.commit()
        return token
    
    def add_lidarseg(self, *,
                     token: str,
                     sample_data_token: str,
                     filename: str) -> str:
        """增加一条 lidarseg 记录

        Args:
            token (str): 指向的 sample_data 记录的 token
            sample_data_token (str): 指向的 sample_data 记录的 token
            filename (str): 文件名
        """
        self._cursor.execute('''
            INSERT INTO lidarseg (token, sample_data_token, filename) VALUES (?, ?, ?)
        ''', (token, sample_data_token, filename))
        
        self._conn.commit()
        return token
    
    def add_can_bus_pose(self, *,
                     token: str,
                     utime: float = time.time(),
                     vel: List[float],
                     accel: List[float],
                     rotation_rate: List[float]) -> str:
        """增加一条 can_bus_pose 记录

        Args:
            token (str, optional): 主键，仅用作占位
            utime (float, optional): 时间戳, 默认使用当前时间戳
            vel (list[float]): 速度矢量
            accel (list[float]): 加速度矢量
            rotation_rate (list[float]): 角速度矢量

        Returns:
            str: 插入数据库的 token
        """
        utime = self.get_nuscenes_timestamp(utime)
        
        # 转换部分数据为 json 格式
        vel = json.dumps(vel)
        accel = json.dumps(accel)
        rotation_rate = json.dumps(rotation_rate)
        
        self._cursor.execute('''
            INSERT INTO can_bus_pose (token, utime, vel, accel, rotation_rate) VALUES (?, ?, ?, ?, ?)
        ''', (token, utime, vel, accel, rotation_rate))
        
        self._conn.commit()
        return token

    def add_can_bus_steeranglefeedback(self, *,
                                       token: str,
                                       utime: float = time.time(),
                                       value: float) -> str:
        """增加一条 can_bus_steeranglefeedback 记录

        Args:
            token (str, optional): 主键，仅用作占位
            utime (float, optional): 时间戳, 默认使用当前时间戳
            value (float): steering angle, 取值范围为[-7.7, 6.3]

        Returns:
            str: 插入数据库的 token
        """
        utime = self.get_nuscenes_timestamp(utime)

        # value 存储为 JSON 字符串以保持一致性
        value_json = json.dumps(value)
        
        self._cursor.execute('''
            INSERT INTO can_bus_steeranglefeedback (token, utime, value) VALUES (?, ?, ?)
        ''', (token, utime, value_json))
        
        self._conn.commit()
        return token

    def dump_log(self) -> str:
        """导出 log 表为 json 格式

        Returns:
            str: json 格式的 log 表, 与 nuScence 定义一致
        """
        self._cursor.execute('''
            SELECT * FROM log
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        return self._format_json([dict(zip(columns, row)) for row in rows])
        
    def dump_map(self) -> str:
        """导出 map 表为 json 格式
        
        以下字段由数据库查询获得:
        - log_tokens

        Returns:
            str: json 格式的 map 表, 与 nuScence 定义一致
        """
        self._cursor.execute('''
            SELECT m.*, GROUP_CONCAT(plm.log_token) as log_tokens
            FROM map m
            LEFT JOIN pair_log_map plm ON m.token = plm.map_token
            GROUP BY m.token
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        result = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            # 将log_tokens字符串转换为列表
            if row_dict['log_tokens']:
                row_dict['log_tokens'] = row_dict['log_tokens'].split(',')
            else:
                row_dict['log_tokens'] = []
            result.append(row_dict)
        return self._format_json(result)
    
    def dump_scene(self) -> str:
        """导出 scene 表为 json 格式
        
        以下字段由数据库查询获得:
        - nbr_samples
        - first_sample_token
        - last_sample_token

        Returns:
            str: json 格式的 scene 表, 与 nuScence 定义一致
        """
        self._cursor.execute('''
            SELECT s.*, 
                   COUNT(sa.token) AS nbr_samples,
                   (SELECT sa1.token FROM sample sa1 WHERE sa1.scene_token = s.token AND sa1.prev IS NULL) AS first_sample_token,
                   (SELECT sa2.token FROM sample sa2 WHERE sa2.scene_token = s.token AND sa2.next IS NULL) AS last_sample_token
            FROM scene s
            LEFT JOIN sample sa ON s.token = sa.scene_token
            GROUP BY s.token
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        
        # 将 None 转换为空字符串
        result = []
        for row in rows:
            row_dict = {col: (val if val is not None else '') for col, val in zip(columns, row)}
            result.append(row_dict)
        
        return self._format_json(result)

    def dump_sample(self) -> str:
        """导出 sample 表为 json 格式

        Returns:
            str: json 格式的 sample 表, 与 nuScence 定义一致
        """
        self._cursor.execute('''
            SELECT * FROM sample
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        
        # 将 None 转换为空字符串
        result = []
        for row in rows:
            row_dict = {col: (val if val is not None else '') for col, val in zip(columns, row)}
            result.append(row_dict)
        
        return self._format_json(result)

    def dump_sensor(self) -> str:
        """导出 sensor 表为 json 格式

        Returns:
            str: json 格式的 sensor 表, 与 nuScence 定义一致
        """
        self._cursor.execute('''
            SELECT * FROM sensor
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        return self._format_json([dict(zip(columns, row)) for row in rows])

    def dump_calibrated_sensor(self) -> str:
        """导出 calibrated_sensor 表为 json 格式

        Returns:
            str: json 格式的 calibrated_sensor 表, 与 nuScence 定义一致
        """
        self._cursor.execute('''
            SELECT * FROM calibrated_sensor
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        
        result = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            # Decode the JSON strings for translation, rotation, and camera_intrinsic
            row_dict['translation'] = self._decode_json_list(row_dict['translation'])
            row_dict['rotation'] = self._decode_json_list(row_dict['rotation'])
            row_dict['camera_intrinsic'] = self._decode_json_list(row_dict['camera_intrinsic'])
            result.append(row_dict)
        
        return self._format_json(result)
    
    def dump_ego_pose(self) -> str:
        """导出 ego_pose 表为 json 格式

        Returns:
            str: json 格式的 ego_pose 表, 与 nuScence 定义一致
        """
        self._cursor.execute('''
            SELECT * FROM ego_pose
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        
        result = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            row_dict['translation'] = self._decode_json_list(row_dict['translation'])
            row_dict['rotation'] = self._decode_json_list(row_dict['rotation'])
            result.append(row_dict)
            
        return self._format_json(result)
    
    def dump_sample_data(self) -> str:
        """导出 sample_data 表为 json 格式

        Returns:
            str: json 格式的 sample_data 表, 与 nuScence 定义一致
        """
        self._cursor.execute('''
            SELECT * FROM sample_data
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        
        result = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            # Convert None to empty string for 'next' and 'prev'
            row_dict['next'] = row_dict['next'] if row_dict['next'] is not None else ''
            row_dict['prev'] = row_dict['prev'] if row_dict['prev'] is not None else ''
            result.append(row_dict)
        
        return self._format_json(result)

    def dump_visibility(self) -> str:
        """导出 visibility 表为 json 格式

        Returns:
            str: json 格式的 visibility 表, 与 nuScence 定义一致
        """
        self._cursor.execute('''
            SELECT * FROM visibility
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        return self._format_json([dict(zip(columns, row)) for row in rows])

    def dump_attribute(self) -> str:
        """导出 attribute 表为 json 格式

        Returns:
            str: json 格式的 attribute 表, 与 nuScence 定义一致 
        """
        self._cursor.execute('''
            SELECT * FROM attribute
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        return self._format_json([dict(zip(columns, row)) for row in rows])

    def dump_instance(self) -> str:
        """导出 instance 表为 json 格式

        Returns:
            str: json 格式的 instance 表, 与 nuScence 定义一致
        """
        self._cursor.execute('''
            SELECT i.*, 
                COUNT(sa.instance_token) AS nbr_annotations
            FROM instance i
            LEFT JOIN sample_annotation sa ON i.token = sa.instance_token
            GROUP BY i.token
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        
        result = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            # 将 None 转换为空字符串，符合 nuScenes 标准
            row_dict['first_annotation_token'] = row_dict['first_annotation_token'] if row_dict['first_annotation_token'] is not None else ''
            row_dict['last_annotation_token'] = row_dict['last_annotation_token'] if row_dict['last_annotation_token'] is not None else ''
            result.append(row_dict)
        
        return self._format_json(result)

    def dump_category(self) -> str:
        """导出 category 表为 json 格式

        Returns:
            str: json 格式的 category 表, 与 nuScence 定义一致
        """
        self._cursor.execute('''
            SELECT * FROM category
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        
        # 在字典中替换 'seg_index' 为 'index' 
        return self._format_json([
            {('index' if col == 'seg_index' else col): value for col, value in zip(columns, row)}
            for row in rows
        ])

    def dump_lidarseg(self) -> str:
        """导出 lidarseg 表为 json 格式

        Returns:
            str: json 格式的 lidarseg 表, 与 nuScence 定义一致
        """
        self._cursor.execute('''
            SELECT * FROM lidarseg
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        return self._format_json([dict(zip(columns, row)) for row in rows])
    
    def dump_sample_annotation(self) -> str:
        """导出 sample_annotation 表为 json 格式

        Returns:
            str: json 格式的 sample_annotation 表, 与 nuScence 定义一致
        """
        self._cursor.execute('''
            SELECT * FROM sample_annotation
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        
        result = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            row_dict['attribute_tokens'] = json.loads(row_dict['attribute_tokens'])
            row_dict['translation'] = self._decode_json_list(row_dict['translation'])
            row_dict['size'] = self._decode_json_list(row_dict['size'])
            row_dict['rotation'] = self._decode_json_list(row_dict['rotation'])
            row_dict['next'] = row_dict['next'] if row_dict['next'] is not None else ''
            row_dict['prev'] = row_dict['prev'] if row_dict['prev'] is not None else ''
            result.append(row_dict)
        
        return self._format_json(result)

    def dump_can_bus_pose(self) -> str:
        """导出 can_bus_pose 表为 json 格式

        Returns:
            str: json 格式的 can_bus_pose 表, 内含 UniAD 系模型需要读取的数据
        """
        self._cursor.execute('''
            SELECT * FROM can_bus_pose
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        
        result = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            # Decode the JSON strings for vel, accel, and rotation_rate
            row_dict['vel'] = json.loads(row_dict['vel'])
            row_dict['accel'] = json.loads(row_dict['accel'])
            row_dict['rotation_rate'] = json.loads(row_dict['rotation_rate'])
            result.append(row_dict)
            
        return self._format_json(result)

    def dump_can_bus_steer_angle_feedback(self) -> str:
        """导出 can_bus_steeranglefeedback 表为 json 格式

        Returns:
            str: json 格式的 can_bus_steeranglefeedback 表, 内含 UniAD 系模型需要读取的数据
        """
        self._cursor.execute('''
            SELECT * FROM can_bus_steeranglefeedback
        ''')
        rows = self._cursor.fetchall()
        columns = [column[0] for column in self._cursor.description]
        
        result = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            row_dict['value'] = json.loads(row_dict['value'])
            result.append(row_dict)
            
        return self._format_json(result)

    def get_category_token_by_index(self, index: int) -> str:
        """根据 index 获取 category 表中的 token"""
        self._cursor.execute('''
            SELECT token FROM category WHERE seg_index = ?
        ''', (index,))
        return self._cursor.fetchone()[0]
    
    def update_instance(self, *,
                        token: str,
                        last_annotation_token: str) -> None:
        """更新 instance 表中的记录"""
        self._cursor.execute('''
            UPDATE instance SET last_annotation_token = ? WHERE token = ?
        ''', (last_annotation_token, token))
        self._conn.commit()
    
    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
            self._cursor = None

class NuScenesDumper(DatasetDumper):
    """
    导出为 NuScenes 数据集格式
    """

    DATASET_TYPE = 'nuScenes'
    
    # 文件夹名称
    FOLDER_SAMPLES = 'samples'
    FOLDER_SWEEPS = 'sweeps'
    FOLDER_MAPS = 'maps'
    FOLDER_LIDARSEG = 'lidarseg/carla_nuscenes_meta'
    
    # JSON 文件名
    FILE_LOG = 'log.json'
    FILE_MAP = 'map.json'
    FILE_SCENE = 'scene.json'
    FILE_SAMPLE = 'sample.json'
    FILE_SAMPLE_DATA = 'sample_data.json'
    FILE_EGO_POSE = 'ego_pose.json'
    FILE_CALIBRATED_SENSOR = 'calibrated_sensor.json'
    FILE_SENSOR = 'sensor.json'
    FILE_VISIBILITY = 'visibility.json'
    FILE_ATTRIBUTE = 'attribute.json'
    FILE_CATEGORY = 'category.json'
    FILE_INSTANCE = 'instance.json'
    FILE_SAMPLE_ANNOTATION = 'sample_annotation.json'
    FILE_LIDARSEG = 'lidarseg.json'
    FILE_CAN_BUS_POSE = 'can_bus_pose.json'
    FILE_CAN_BUS_STEER_ANGLE_FEEDBACK = 'can_bus_steer_angle_feedback.json'

    # 常量
    TIMESTAMP_INCREMENT_MICROSECONDS = 50000  # 恢复缺失 sample 时的时间戳增量（微秒）
    TIMESTAMP_TO_MICROSECONDS = 1_000_000  # 秒到微秒的转换因子
    VEHICLE_SPEED_THRESHOLD = 0.5  # 判断车辆是否移动的速度阈值（m/s）
    PEDESTRIAN_SPEED_THRESH = 0.1 # 判断行人是否移动的速度阈值（m/s）
    STEER_ANGLE_MULTIPLIER = 70.0  # 转向角转换倍数
    STEER_ANGLE_MIN = -7.7  # 转向角最小值（度）
    STEER_ANGLE_MAX = 6.3  # 转向角最大值（度）

    # nuScenes 标准类别定义 (index, name, description)
    NUSCENES_CATEGORIES = [
        (0, "noise", "Any lidar return that does not correspond to a physical object, such as dust, vapor, noise, fog, raindrops, smoke and reflections."),
        (1, "animal", "All animals, e.g. cats, rats, dogs, deer, birds."),
        (2, "human.pedestrian.adult", "Adult subcategory."),
        (3, "human.pedestrian.child", "Child subcategory."),
        (4, "human.pedestrian.construction_worker", "Construction worker"),
        (5, "human.pedestrian.personal_mobility", "A small electric or self-propelled vehicle, e.g. skateboard, segway, or scooters, on which the person typically travels in a upright position. Driver and (if applicable) rider should be included in the bounding box along with the vehicle."),
        (6, "human.pedestrian.police_officer", "Police officer."),
        (7, "human.pedestrian.stroller", "Strollers. If a person is in the stroller, include in the annotation."),
        (8, "human.pedestrian.wheelchair", "Wheelchairs. If a person is in the wheelchair, include in the annotation."),
        (9, "movable_object.barrier", "Temporary road barrier placed in the scene in order to redirect traffic. Commonly used at construction sites. This includes concrete barrier, metal barrier and water barrier. No fences."),
        (10, "movable_object.debris", "Movable object that is left on the driveable surface that is too large to be driven over safely, e.g tree branch, full trash bag etc."),
        (11, "movable_object.pushable_pullable", "Objects that a pedestrian may push or pull. For example dolleys, wheel barrows, garbage-bins, or shopping carts."),
        (12, "movable_object.trafficcone", "All types of traffic cone."),
        (13, "static_object.bicycle_rack", "Area or device intended to park or secure the bicycles in a row. It includes all the bikes parked in it and any empty slots that are intended for parking bikes."),
        (14, "vehicle.bicycle", "Human or electric powered 2-wheeled vehicle designed to travel at lower speeds either on road surface, sidewalks or bike paths."),
        (15, "vehicle.bus.bendy", "Bendy bus subcategory. Annotate each section of the bendy bus individually."),
        (16, "vehicle.bus.rigid", "Rigid bus subcategory."),
        (17, "vehicle.car", "Vehicle designed primarily for personal use, e.g. sedans, hatch-backs, wagons, vans, mini-vans, SUVs and jeeps. If the vehicle is designed to carry more than 10 people use vehicle.bus. If it is primarily designed to haul cargo use vehicle.truck."),
        (18, "vehicle.construction", "Vehicles primarily designed for construction. Typically very slow moving or stationary. Cranes and extremities of construction vehicles are only included in annotations if they interfere with traffic. Trucks used to haul rocks or building materials are considered vehicle.truck rather than construction vehicles."),
        (19, "vehicle.emergency.ambulance", "All types of ambulances."),
        (20, "vehicle.emergency.police", "All types of police vehicles including police bicycles and motorcycles."),
        (21, "vehicle.motorcycle", "Gasoline or electric powered 2-wheeled vehicle designed to move rapidly (at the speed of standard cars) on the road surface. This category includes all motorcycles, vespas and scooters."),
        (22, "vehicle.trailer", "Any vehicle trailer, both for trucks, cars and bikes."),
        (23, "vehicle.truck", "Vehicles primarily designed to haul cargo including pick-ups, lorrys, trucks and semi-tractors. Trailers hauled after a semi-tractor should be labeled as vehicle.trailer"),
        (24, "flat.driveable_surface", "All paved or unpaved surfaces that a car can drive on with no concern of traffic rules."),
        (25, "flat.other", "All other forms of horizontal ground-level structures that do not belong to any of driveable_surface, curb, sidewalk and terrain. Includes elevated parts of traffic islands, delimiters, rail tracks, stairs with at most 3 steps and larger bodies of water (lakes, rivers)."),
        (26, "flat.sidewalk", "Sidewalk, pedestrian walkways, bike paths, etc. Part of the ground designated for pedestrians or cyclists. Sidewalks do **not** have to be next to a road."),
        (27, "flat.terrain", "Natural horizontal surfaces such as ground level horizontal vegetation (< 20 cm tall), grass, rolling hills, soil, sand and gravel."),
        (28, "static.manmade", "Includes man-made structures but not limited to: buildings, walls, guard rails, fences, poles, drainages, hydrants, flags, banners, street signs, electric circuit boxes, traffic lights, parking meters and stairs with more than 3 steps."),
        (29, "static.other", "Points in the background that are not distinguishable, or objects that do not match any of the above labels."),
        (30, "static.vegetation", "Any vegetation in the frame that is higher than the ground, including bushes, plants, potted plants, trees, etc. Only tall grass (> 20cm) is part of this, ground level grass is part of `terrain`."),
        (31, "vehicle.ego", "The vehicle on which the cameras, radar and lidar are mounted, that is sometimes visible at the bottom of the image."),
    ]
    
    # nuScenes 标准属性定义 (name, description)
    NUSCENES_ATTRIBUTES = [
        ("vehicle.moving", "Vehicle is moving."),
        ("vehicle.stopped", "Vehicle, with a driver/rider in/on it, is currently stationary but has an intent to move."),
        ("vehicle.parked", "Vehicle is stationary (usually for longer duration) with no immediate intent to move."),
        ("cycle.with_rider", "There is a rider on the bicycle or motorcycle."),
        ("cycle.without_rider", "There is NO rider on the bicycle or motorcycle."),
        ("pedestrian.sitting_lying_down", "The human is sitting or lying down."),
        ("pedestrian.standing", "The human is standing."),
        ("pedestrian.moving", "The human is moving."),
        ("default", "Default attribute."),
    ]
    
    
    # nuScenes 标准可见性定义 ('description', 'token','level')
    NUSCENES_VISIBILITIES = [
        ("visibility of whole object is between 0 and 40%",    "1",  "v0-40"),
        ("visibility of whole object is between 40 and 60%",   "2", "v40-60"),
        ("visibility of whole object is between 60 and 80%",   "3", "v60-80"),
        ("visibility of whole object is between 80 and 100%",  "4",    "v80-100"),
    ]    
    
    # CARLA 语义标签到 nuScenes 类别的映射
    CARLA_NUSCENES_MAPPING = {
        1: 24,      # road -> flat.driveable_surface
        2: 26,      # sidewalk -> flat.sidewalk
        3: 28,      # building -> static.manmade
        4: 28,      # wall -> static.manmade
        5: 9,       # fence -> movable_object.barrier
        6: 28,      # pole -> static.manmade
        7: 28,      # traffic light -> static.manmade
        8: 28,      # traffic sign -> static.manmade
        9: 30,      # vegetation -> static.vegetation
        10: 27,     # terrain -> flat.terrain
        11: 0,      # sky -> noise
        12: 2,      # pedestrian -> human.pedestrian.adult
        13: 2,      # rider -> human.pedestrian.adult
        14: 17,     # car -> vehicle.car
        15: 23,     # truck -> vehicle.truck
        16: 16,     # bus -> vehicle.bus.rigid
        17: 0,      # train -> noise
        18: 21,     # motorcycle -> vehicle.motorcycle
        19: 14,     # bicycle -> vehicle.bicycle
        20: 29,     # static -> static.other
        21: 10,     # dynamic -> movable_object.debris
        22: 29,     # other -> static.other
        23: 25,     # water -> flat.other
        24: 24,     # road line -> flat.driveable_surface
        25: 25,     # ground -> flat.other
        26: 28,     # bridge -> static.manmade
        27: 25,     # rail -> flat.other
        28: 9,      # guard rail -> movable_object.barrier
        29: 24,     # lane-marking -> flat.driveable_surface
        30: 25,     # parking -> flat.other
    }

    def __init__(
        self,
        context: 'CarlaContext',
        *,
        name: str = None,
        path: str | Path | None = None,
        vehicle: str = 'UNKNOWN',
        location: str = 'UNKNOWN',
        map_category: str = 'semantic_prior',
        map_filename: str = 'maps/sample.png',
        carla_vehicle = None  # CarlaVehicle 实例，用于获取 CAN bus 数据
    ):
        """初始化 NuScenes 数据集导出器

        Args:
            context (CarlaContext): 仿真上下文
            name (str, optional): 数据集名称. 默认为 None, 将根据时间自动生成.
            path (str | Path, optional): 数据集保存路径. 默认为 None, 将根据配置文件自动确定.
            vehicle (str, optional): 车辆描述, 如: 'n18'. 默认为 'UNKNOWN'.
            location (str, optional): 数据采集地点描述, 如: 'singapore-onenorth'. 默认为 'UNKNOWN'.
            map_category (str, optional): 地图分类描述, 如: 'semantic_prior'. 默认为 'semantic_prior'.
            map_filename (str, optional): 地图文件名, 如: 'maps/sample.png'. 默认为 'maps/sample.png'.
        """
        self._vehicle = vehicle
        self._location = location
        self._map_category = map_category
        self._map_filename = map_filename
        self._carla_vehicle = carla_vehicle  # CarlaVehicle 实例，用于获取 CAN bus 数据
        
        super().__init__(
            context=context,
            name=name,
            path=path,
        )
        self._sensor_tokens: dict[CarlaSensor, str] = {}
        self._calibrated_sensor_tokens: dict[CarlaSensor, str] = {}
        self._sensor_folders: dict[CarlaSensor, Path] = {}
        self._sensor_naming_policies: dict[CarlaSensor, 'DatasetDumper.NamingPolicy'] = {}
        
        self._current_sample_token: str = None
        self._prev_sample_token: str = None
        self._prev_sample_data_tokens: dict[CarlaSensor, str] = {}
        self._timestamp_ego_pose_tokens: dict[int, str] = {}
        self._known_objects: dict[int, str] = {}
        self._default_visibility_token: str = None
        self._default_attribute_token: str = None
        
        self._prev_can_bus_vel: List[float] = [0.0, 0.0, 0.0]
        self._prev_can_bus_timestamp: float = 0.0
        self._timestamp_offset: float = 0.0

        self.sensor_tf = self._carla_vehicle.get_sensor_vehicle_rear_wheels_center_tf() # nuscenes车体右手坐标系下的各传感器外参
        # attribute.name -> token 的缓存，避免每一帧都查数据库
        self._attribute_token_cache: dict[str, str] = {}
        self._all_sensors_ready = False  # 所有传感器是否已经至少有一帧数据

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        result = super().__exit__(exc_type, exc_value, traceback)
        if self._db:
            self._db.close()
        return result

    def __post_init__(self) -> Self:
        
        super().__post_init__()
        self._db = NuScenesDB(db_path=":memory:")
        self.logger.info(f'NuScenes database created (in-memory)')
        
        self._map_token = self._db.add_map(
            category=self._map_category,
            filename=self._map_filename
        )
        self.logger.debug(f'Map token created: {self._map_token}')
        
        self._log_token = self._db.add_log(
            vehicle=self._vehicle,
            location=self._location,
            map_token=self._map_token
        )
        self.logger.debug(f'Log token created: {self._log_token}')
        
        # 获取数据集名称（从路径中提取）
        dataset_name = self._path.name
        self._scene_token = self._db.add_scene(
            log_token=self._log_token,
            name=dataset_name,
            description=f'Scene exported from CARLA simulation'
        )
        self.logger.debug(f'Scene token created: {self._scene_token}')
        
        # 初始化基础元数据
        self._setup_db_category()
        self._setup_db_attribute()
        self._setup_db_visibility()
        
        # 创建文件夹
        self._folder_samples = self._path / self.FOLDER_SAMPLES
        self._folder_sweeps = self._path / self.FOLDER_SWEEPS
        self._folder_maps = self._path / self.FOLDER_MAPS
        self._folder_lidarseg = self._path / self.FOLDER_LIDARSEG #lidarseg路径
        os.makedirs(self._folder_samples, exist_ok=True)
        os.makedirs(self._folder_sweeps, exist_ok=True)
        os.makedirs(self._folder_maps, exist_ok=True)
        os.makedirs(self._folder_lidarseg, exist_ok=True)
        self.logger.debug(f'Created folders: samples, sweeps, maps, lidarseg')
        
        # 注册 tick 钩子
        self._append_hook_befre_next_tick(self._tick_record_sample)
        
        # 注册 flush 钩子（先恢复缺失的记录，再导出 JSON）
        # self.hook_after_final_flush.append(self._recover_missing_sample_data)
        self.hook_after_final_flush.append(self._export_json_files)
        self._hook_after_final_flush.append(self._log_result)
        
        
        return self
    
    def _setup_db_category(self) -> None:
        """初始化 category 表，填充 nuScenes 标准类别定义"""
        for index, name, description in self.NUSCENES_CATEGORIES:
            self._db.add_category(index=index, name=name, description=description)
        self.logger.debug(f'Initialized {len(self.NUSCENES_CATEGORIES)} categories')
    
    def _setup_db_attribute(self) -> None:
        """初始化 attribute 表，填充 nuScenes 标准属性定义"""
        for name, description in self.NUSCENES_ATTRIBUTES:
            token = self._db.add_attribute(name=name, description=description)
            if name == "default":
                self._default_attribute_token = token
        self.logger.debug(f'Initialized {len(self.NUSCENES_ATTRIBUTES)} attributes')
        
        # 保存默认 attribute token
        if self._default_attribute_token is None:
            # 如果 default 不存在，使用第一个
            self._db._cursor.execute('SELECT token FROM attribute LIMIT 1')
            result = self._db._cursor.fetchone()
            if result:
                self._default_attribute_token = result[0]
    
    def _setup_db_visibility(self) -> None:
        """初始化 visibility 表，填充 nuScenes 标准可见性定义"""
        for description, token,level in self.NUSCENES_VISIBILITIES:
            token = self._db.add_visibility(token=token,description=description, level=level)
            if description == "4":
                self._default_visibility_token = token
        self.logger.debug(f'Initialized {len(self.NUSCENES_VISIBILITIES)} visibility levels')
        
        # 保存默认 visibility token
        if self._default_visibility_token is None:
            # 如果 fully_visible 不存在，使用第一个
            self._db._cursor.execute('SELECT token FROM visibility LIMIT 1')
            result = self._db._cursor.fetchone()
            if result:
                self._default_visibility_token = result[0]

    def split_vehicle_sensor(self,name: str) -> Tuple[str, str]:
        sensors = sorted(set(self._carla_vehicle.VEHICLE_SENSORS), key=len, reverse=True)  # 先匹配最长的，避免前缀冲突
        for sensor in sensors:
            suffix = "_" + sensor
            if name.endswith(suffix):
                vehicle = name[:-len(suffix)]
                if not vehicle:
                    raise ValueError(f"车辆名为空：{name!r}")
                return sensor
        raise ValueError(f"无法从字符串识别传感器后缀：{name!r}")

    def _all_sensors_warmed_up(self) -> bool:
        '''
        判断所有需要导出的传感器是否至少产出过一帧数据
        返回 True 之后，就不会再退回 False（用 _all_sensors_ready 记住结果）。
        '''
        # 已经确认过一次，就不用每帧都重新扫，提高一点效率
        if self._all_sensors_ready:
            return True
        # 这里定义“哪些传感器必须有数据之后才开始录”
        # 默认用所有在 self._sensor_tokens 里的传感器
        required_sensors = list(self._sensor_tokens.keys())
        for sensor in required_sensors:
            sensor_folder = self._sensor_folders.get(sensor)
            if not sensor_folder:
                # 理论上不会出现，如果出现可以选择直接 return False 或者跳过
                self.logger.debug(f"[NUSC] Sensor {sensor.name} has no folder configured, treat as not ready.")
                return False
            folder_abs = os.path.abspath(sensor_folder)
            prefix = folder_abs + os.sep
            # 检查 _dataset 里是否有以该目录开头的 key
            has_any_data = any(
                str(path).startswith(prefix) for path in self._data_buffer.keys()
            )
            if not has_any_data:
                # 这个传感器至今一个数据帧都没有
                return False
            # 走到这里说明所有 required_sensors 都在 _dataset 里出现过至少一次
            self._all_sensors_ready = True
            self.logger.info("[NUSC] All sensors have produced at least one frame. Start recording samples.")
            return True

    def bind_sensor_output(self, sensor: CarlaSensor, path: str | Path | None = None, naming_policy: 'DatasetDumper.NamingPolicy' = None) -> Self:
        """绑定传感器数据输出到内存缓存, 并创建 sensor 和 calibrated_sensor 记录
        
        Args:
            sensor (CarlaSensor): 传感器
            path (str | Path | None, optional): 文件夹路径. 默认为 None, 将根据传感器名称自动确定.
            naming_policy (NamingPolicy, optional): 命名策略. 默认为 None, 将根据传感器类型自动确定.
        
        Returns:
            Self: 返回自身
        """
        sensor_name = self.split_vehicle_sensor(sensor.name)
        
        if path is None:
            path = sensor.name
        
        samples_folder_path = Path(self.FOLDER_SAMPLES) / path
        folder_path_abs = (self._path / samples_folder_path).resolve()
        
        if naming_policy is None:
            if sensor.is_camera:
                naming_policy = self.NamingPolicy(extension='jpg')
            elif sensor.is_lidar:
                naming_policy = self.NamingPolicy(extension='bin')
            else:
                raise ValueError(f"Unsupported sensor type: {sensor.bp.id}")
        
        self._sensor_folders[sensor] = folder_path_abs
        self._sensor_naming_policies[sensor] = naming_policy
        super().bind_sensor_output(sensor, samples_folder_path, naming_policy)
        
        modality = 'camera' if sensor.is_camera else 'lidar'
        sensor_token = self._db.add_sensor(channel=sensor_name, modality=modality)
        self.logger.debug(f'Sensor created: {sensor_name}')
        self._sensor_tokens[sensor] = sensor_token
        self.logger.debug(f'Sensor token created for {sensor_name}: {sensor_token}')
        
        # 获取carla传感器到nuscenes车体右手坐标系下lidar(x右, y前, z上) camera(x右, y下, z前)到车体后轮中心（x向前，y向左，z向上）的外参
        sensor_vehicle_rear_center_matrix_nus = self.sensor_tf[sensor_name]
        translation = sensor_vehicle_rear_center_matrix_nus[:3, 3].tolist()
        rotation_matrix = sensor_vehicle_rear_center_matrix_nus[:3, :3]
        rotation_quaternion = self._rotation_matrix_to_quaternion(rotation_matrix)
        rotation = rotation_quaternion.tolist()

        camera_intrinsic = []
        if sensor.is_camera:
            K = sensor.get_camera_intrinsics_matrix()
            camera_intrinsic = K.tolist()
        
        calibrated_sensor_token = self._db.add_calibrated_sensor(
            sensor_token=sensor_token,
            translation=translation,
            rotation=rotation,
            camera_intrinsic=camera_intrinsic
        )
        self._calibrated_sensor_tokens[sensor] = calibrated_sensor_token
        self.logger.debug(f'Calibrated sensor token created for {sensor.name}: {calibrated_sensor_token}')
        
        return self

    def _rotation_matrix_to_quaternion(self, rotation_matrix: np.ndarray) -> np.ndarray:
        """将旋转矩阵转换为四元数，格式为 w, x, y, z
        
        Args:
            rotation_matrix (np.ndarray): 3x3 旋转矩阵
            
        Returns:
            np.ndarray: 四元数，格式为 w, x, y, z
        """
        trace = np.trace(rotation_matrix)
        
        if trace > 0:
            s = np.sqrt(trace + 1.0) * 2
            w = 0.25 * s
            x = (rotation_matrix[2, 1] - rotation_matrix[1, 2]) / s
            y = (rotation_matrix[0, 2] - rotation_matrix[2, 0]) / s
            z = (rotation_matrix[1, 0] - rotation_matrix[0, 1]) / s
        else:
            if rotation_matrix[0, 0] > rotation_matrix[1, 1] and rotation_matrix[0, 0] > rotation_matrix[2, 2]:
                s = np.sqrt(1.0 + rotation_matrix[0, 0] - rotation_matrix[1, 1] - rotation_matrix[2, 2]) * 2
                w = (rotation_matrix[2, 1] - rotation_matrix[1, 2]) / s
                x = 0.25 * s
                y = (rotation_matrix[0, 1] + rotation_matrix[1, 0]) / s
                z = (rotation_matrix[0, 2] + rotation_matrix[2, 0]) / s
            elif rotation_matrix[1, 1] > rotation_matrix[2, 2]:
                s = np.sqrt(1.0 + rotation_matrix[1, 1] - rotation_matrix[0, 0] - rotation_matrix[2, 2]) * 2
                w = (rotation_matrix[0, 2] - rotation_matrix[2, 0]) / s
                x = (rotation_matrix[0, 1] + rotation_matrix[1, 0]) / s
                y = 0.25 * s
                z = (rotation_matrix[1, 2] + rotation_matrix[2, 1]) / s
            else:
                s = np.sqrt(1.0 + rotation_matrix[2, 2] - rotation_matrix[0, 0] - rotation_matrix[1, 1]) * 2
                w = (rotation_matrix[1, 0] - rotation_matrix[0, 1]) / s
                x = (rotation_matrix[0, 2] + rotation_matrix[2, 0]) / s
                y = (rotation_matrix[1, 2] + rotation_matrix[2, 1]) / s
                z = 0.25 * s
        
        return np.array([w, x, y, z])

    def _tick_record_sample(self, snapshot: carla.WorldSnapshot) -> Self:
        """在 TICK 时记录 sample 和 sample_data
        
        Args:
            snapshot (carla.WorldSnapshot): CARLA 世界快照
        """
        if self._frame_counter == 0:
            return self
        # 在创建 sample 之前检查 sensors 是否已经 warm-up 完成
        # if not self._all_sensors_warmed_up():
        #     self.logger.debug(
        #     f"[NUSC] Sensors not warmed up yet at frame_counter={self._frame_counter}, "
        #     f"skip sample recording for this tick.")
        #     return self
        timestamp = self._initialize_timestamp(snapshot)
        if timestamp is None:
            return self
        
        if not self._create_sample_record(timestamp):
            return self
        
        current_ego_pose_token = self._ensure_ego_pose_token(timestamp)
        if current_ego_pose_token is None:
            return self
        
        self._record_sensor_sample_data(timestamp, current_ego_pose_token)
        self._prev_sample_token = self._current_sample_token
        
        if self._carla_vehicle and self._carla_vehicle.actor:
            self._record_can_bus_data(timestamp)
        
        return self
    
    def _initialize_timestamp(self, snapshot: carla.WorldSnapshot) -> float:
        """初始化并计算相对时间戳
        
        Args:
            snapshot (carla.WorldSnapshot): CARLA 世界快照
            
        Returns:
            float: 相对时间戳，如果失败返回 None
        """
        if self._timestamp_offset == 0.0:
            self._timestamp_offset = snapshot.timestamp.elapsed_seconds
            self.logger.debug(f'Timestamp offset is set to: {self._timestamp_offset}')
        
        if self._scene_token is None:
            self.logger.error('Scene token is None, cannot create sample')
            return None
        
        return snapshot.timestamp.elapsed_seconds - self._timestamp_offset
    
    def _create_sample_record(self, timestamp: float) -> bool:
        """创建 sample 记录
        
        Args:
            timestamp (float): 相对时间戳
            
        Returns:
            bool: 是否成功创建
        """
        self._current_sample_token = self._db.add_sample(
            scene_token=self._scene_token,
            timestamp=timestamp,
            prev=self._prev_sample_token
        )
        return True
    
    def _ensure_ego_pose_token(self, timestamp: float) -> str:
        """确保当前时间戳有对应的 ego_pose token
        
        Args:
            timestamp (float): 相对时间戳
            
        Returns:
            str: ego_pose token，如果失败返回 None
        """
        timestamp_nuscenes = self._db.get_nuscenes_timestamp(timestamp)
        
        if timestamp_nuscenes not in self._timestamp_ego_pose_tokens:
            vehicle = self._get_vehicle_from_sensors()
            if not vehicle:
                return None
            
            ego_pose_token = self._create_ego_pose(vehicle, timestamp)
            if ego_pose_token:
                self._timestamp_ego_pose_tokens[timestamp_nuscenes] = ego_pose_token
        
        return self._timestamp_ego_pose_tokens.get(timestamp_nuscenes)
    
    def _get_vehicle_from_sensors(self):
        """从传感器获取车辆对象
        
        Returns:
            车辆对象，如果未找到返回 None
        """
        # 注意：返回类型应该是 CarlaVehicle，但由于循环导入问题，使用动态类型
        for sensor in self._sensor_tokens.keys():
            vehicle = sensor.parent if sensor.parent else None
            if vehicle:
                return vehicle
        return None
    
    def _create_ego_pose(self, vehicle, timestamp: float) -> str:
        """创建 ego_pose 记录
        
        Args:
            vehicle: 车辆对象
            timestamp (float): 相对时间戳
            
        Returns:
            str: ego_pose token
        """
        vehicle_tf = vehicle.tf_now # 车辆当前timestamp在地图中的rotation和translation
        # 获取ego_pose  carla左手坐标系下（x向前，y向右，z向上）
        vehicle_center_world_matrix_carla = np.array(vehicle_tf.get_matrix())
        # 获取「车体中心 → 后轮中心」的转换矩阵 (在 CARLA 车体坐标系下)
        vehicle_to_vehicle_rear_tf_carla = self.sensor_tf["vehicle_to_vehicle_rear"]
        # 计算「后轮中心 → 车体中心」的逆变换：
        vehicle_rear_to_vehicle_tf_carla = np.linalg.inv(vehicle_to_vehicle_rear_tf_carla)
        # 在 CARLA 世界坐标下，计算「后轮中心」的位姿：
        vehicle_rear_world_matrix_carla = vehicle_center_world_matrix_carla @ vehicle_rear_to_vehicle_tf_carla
        #  将 CARLA 左手系下的 T_W_R 转换到 nuScenes 右手系：
        vehicle_rear_world_matrix_nus = self._carla_vehicle.carla_ego_to_nuscenes_ego_extrinsic(vehicle_rear_world_matrix_carla)
        ego_translation = vehicle_rear_world_matrix_nus[:3, 3].tolist()
        ego_rotation_matrix = vehicle_rear_world_matrix_nus[:3, :3]
        ego_rotation_quaternion = self._rotation_matrix_to_quaternion(ego_rotation_matrix)
        ego_rotation = ego_rotation_quaternion.tolist()

        ego_pose_token = self._db.get_nuscenes_token()
        self._db.add_ego_pose(
            token=ego_pose_token,
            timestamp=timestamp,
            translation=ego_translation,
            rotation=ego_rotation
        )
        return ego_pose_token
    
    def _record_sensor_sample_data(self, timestamp: float, ego_pose_token: str) -> None:
        """记录所有传感器的 sample_data
        
        Args:
            timestamp (float): 相对时间戳
            ego_pose_token (str): ego_pose token
        """
        for sensor in self._sensor_tokens.keys():
            
            sensor_file_path = self._find_sensor_file_path(sensor)
            if sensor_file_path is None:
                continue
            
            sample_data_token = self._create_sample_data_record(
                sensor=sensor,
                sensor_file_path=sensor_file_path,
                timestamp=timestamp,
                ego_pose_token=ego_pose_token
            )
            
            if sample_data_token:
                self._prev_sample_data_tokens[sensor] = sample_data_token
    
    def _find_sensor_file_path(self, sensor: CarlaSensor) -> str:
        """查找传感器文件路径
        
        Args:
            sensor (CarlaSensor): 传感器对象
            
        Returns:
            str: 文件路径，如果未找到返回 None
        """
        sensor_folder = self._sensor_folders.get(sensor)
        naming_policy = self._sensor_naming_policies.get(sensor)
        
        if sensor_folder is None or naming_policy is None:
            return None
        # the original is self._frame_counter
        # counter_str = str(self._frame_counter - 1).rjust(naming_policy.zfill_length, naming_policy.zfill_char)
        counter_str = str(self._frame_counter).rjust(naming_policy.zfill_length, naming_policy.zfill_char)
        sensor_file_path = (sensor_folder / f"{counter_str}.{naming_policy.extension}").resolve()
        if sensor_file_path not in self._data_buffer:
            prev_frame_counter = max(0, self._frame_counter - 1)
            prev_counter_str = str(prev_frame_counter).rjust(naming_policy.zfill_length, naming_policy.zfill_char)
            prev_sensor_file_path = (sensor_folder / f"{prev_counter_str}.{naming_policy.extension}").resolve()
            
            if prev_sensor_file_path in self._data_buffer:
                sensor_file_path = prev_sensor_file_path
            elif not sensor_file_path.exists():
                self.logger.debug(f'Sensor {sensor.name} data not found for frame {self._frame_counter}, skipping')
                return None
        
        return str(sensor_file_path)
    
    def _create_sample_data_record(self, sensor: CarlaSensor, sensor_file_path: str, timestamp: float, ego_pose_token: str) -> str:
        """创建 sample_data 记录
        
        Args:
            sensor (CarlaSensor): 传感器对象
            sensor_file_path (str): 传感器文件路径
            timestamp (float): 相对时间戳
            ego_pose_token (str): ego_pose token
            
        Returns:
            str: sample_data token
        """
        fileformat = 'jpg' if sensor.is_camera else 'bin'
        height = 0
        width = 0
        if sensor.is_camera:
            height = sensor.bp.get_attribute('image_size_y').as_int()
            width = sensor.bp.get_attribute('image_size_x').as_int()
        
        relative_path = os.path.relpath(sensor_file_path, self._path)
        prev_sample_data_token = self._prev_sample_data_tokens.get(sensor, None)
        
        sample_data_token = self._db.get_nuscenes_token()
        self._db.add_sample_data(
            token=sample_data_token,
            sample_token=self._current_sample_token,
            ego_pose_token=ego_pose_token,
            calibrated_sensor_token=self._calibrated_sensor_tokens[sensor],
            timestamp=timestamp,
            fileformat=fileformat,
            is_key_frame=True,
            height=height,
            width=width,
            filename=relative_path,
            prev=prev_sample_data_token
        )
        # 语义lidar用bin表示
        if sensor.is_lidar and 'semantic' in sensor.bp.id.lower():
            bin_filename = relative_path.split('/')[-1]
            lidarseg_bin_filename = Path(self.FOLDER_LIDARSEG) / bin_filename
            self._db.add_lidarseg(
                token=sample_data_token,
                sample_data_token=sample_data_token,
                filename=str(lidarseg_bin_filename)
            )
            self._process_semantic_lidar_annotations(
                sensor=sensor,
                sample_token=self._current_sample_token,
                sample_data_token=sample_data_token
            )
        
        return sample_data_token
    
    def _record_can_bus_data(self, timestamp: float) -> None:
        """记录 CAN bus 数据（速度和转向角）
        
        Args:
            timestamp (float): 当前时间戳
        """
        if not (self._carla_vehicle and self._carla_vehicle.actor):
            return
        
        try:
            velocity = self._carla_vehicle.actor.get_velocity()
            angular_velocity = self._carla_vehicle.actor.get_angular_velocity()
            
            vel = [velocity.x, -velocity.y, velocity.z]
            rotation_rate = [angular_velocity.x, -angular_velocity.y, angular_velocity.z]
            
            dt = timestamp - self._prev_can_bus_timestamp if self._prev_can_bus_timestamp > 0 else 0.0
            if dt > 0:
                accel = [
                    (vel[0] - self._prev_can_bus_vel[0]) / dt,
                    (vel[1] - self._prev_can_bus_vel[1]) / dt,
                    (vel[2] - self._prev_can_bus_vel[2]) / dt
                ]
            else:
                accel = [0.0, 0.0, 0.0]
            
            self._prev_can_bus_vel = vel
            self._prev_can_bus_timestamp = timestamp
            
            can_bus_pose_token = self._db.get_nuscenes_token()
            self._db.add_can_bus_pose(
                token=can_bus_pose_token,
                utime=timestamp,
                vel=vel,
                accel=accel,
                rotation_rate=rotation_rate
            )
            
            control = self._carla_vehicle.actor.get_control()
            steer_angle = control.steer if hasattr(control, 'steer') else 0.0
            steer_angle_deg = max(self.STEER_ANGLE_MIN, min(self.STEER_ANGLE_MAX, steer_angle * self.STEER_ANGLE_MULTIPLIER))
            
            can_bus_steer_token = self._db.get_nuscenes_token()
            self._db.add_can_bus_steeranglefeedback(
                token=can_bus_steer_token,
                utime=timestamp,
                value=steer_angle_deg
            )
        except Exception as e:
            self.logger.warning(f'Failed to record CAN bus data: {e}')
    
    def get_attribute_token(self, name: str) -> str | None:
        """根据 attribute.name 拿 token，带缓存"""
        if name in self._attribute_token_cache:
            return self._attribute_token_cache[name]
        self._db._cursor.execute('SELECT token FROM attribute WHERE name = ?', (name,))
        row = self._db._cursor.fetchone()
        if not row:
            return None
        token = row[0]
        self._attribute_token_cache[name] = token
        return token

    def carla_lidar_points_nus_lidar(self,points_carla: np.ndarray)-> np.ndarray:
        '''
        将点云从 carla 的坐标系转换成 nuscenes 的坐标系
        carla lidar 坐标系   x向前 y向右 z向上，左手坐标系
        nuscenes lidar 坐标系  x向右 y向前 z向上，右手坐标系
        '''
        assert points_carla.ndim == 2 and points_carla.shape[1] >= 3
        points_nusc = points_carla.copy()
        xyz_c = points_carla[:, :3].T # (3,N)
        # 1 y 取反 （右手系）
        S = np.array([
        [1.0,  0.0, 0.0],
        [0.0, -1.0, 0.0],
        [0.0,  0.0, 1.0],], dtype=float)
        # 2  绕 z 轴 +90°（右手系）
        Rz_90 = np.array([
        [0.0, -1.0, 0.0],
        [1.0,  0.0, 0.0],
        [0.0,  0.0, 1.0],], dtype=float)
        xyz_step1 = S @ xyz_c          # 先反射
        xyz_nusc  = Rz_90 @ xyz_step1  # 再旋转
        points_nusc[:, :3] = xyz_nusc.T
        return points_nusc
    
    def get_actor_info(self,actor: carla.Actor) -> dict:
        '''
        利用carla的actor接口获取目标在carla地图的位置，并转化为nuscenes地图坐标系下的位置
        '''
        actor_info = {}
        actor_transform = actor.get_transform()
        loc = actor_transform.location
        rot = actor_transform.rotation
        yaw_c = rot.yaw
        bbox = actor.bounding_box
        bbox_loc_local = bbox.location
        bbox_tf_world = actor_transform
        bbox_center_world = bbox_tf_world.transform(bbox_loc_local)
        extents = bbox.extent
        center_translation_nus = [bbox_center_world.x, -bbox_center_world.y, bbox_center_world.z] #  y轴取反
        w = 2 * extents.y # 左右方向
        l = 2 * extents.x   # 前后方向
        h = 2 * extents.z
        size_nus = [w, l, h]
        yaw_nu = - np.deg2rad(yaw_c)  # 取反 + 角度转弧度
        q_nu = Quaternion(axis=[0, 0, 1], angle=yaw_nu)
        rotation_nu = [q_nu.w, q_nu.x, q_nu.y, q_nu.z]   # 写进 json 的顺序
        actor_velocity = actor.get_velocity()
        actor_info["size_nus"] = size_nus
        actor_info["center_translation_nus"] = center_translation_nus
        actor_info["rotation_nu"] = rotation_nu
        actor_info["velocity"] = actor_velocity
        return actor_info


    def _process_semantic_lidar_annotations(self, sensor: CarlaSensor, sample_token: str, sample_data_token: str) -> None:
        """处理语义激光雷达数据，创建 instance 和 sample_annotation 记录
        
        Args:
            sensor (CarlaSensor): 语义激光雷达传感器
            sample_token (str): 当前 sample 的 token
            sample_data_token (str): 当前 sample_data 的 token
        """
        # counter_str = str(self._frame_counter - 1).rjust(6, '0')
        counter_str = str(self._frame_counter).rjust(6, '0')
        sensor_file_path = (self._sensor_folders[sensor] / f"{counter_str}.bin").resolve()
        
        if sensor_file_path not in self._data_buffer:
            prev_frame_counter = max(0, self._frame_counter - 1)
            prev_counter_str = str(prev_frame_counter).rjust(6, '0')
            prev_sensor_file_path = (self._sensor_folders[sensor] / f"{prev_counter_str}.bin").resolve()
            
            if prev_sensor_file_path in self._data_buffer:
                sensor_file_path = prev_sensor_file_path
            else:
                self.logger.debug(f'Semantic lidar data not found for frame {self._frame_counter}, skipping annotation')
                return
        
        point_cloud_data = self._data_buffer[sensor_file_path]
        if not isinstance(point_cloud_data, PointCloud) or point_cloud_data.format != self._carla_vehicle.POINT_FORMAT:
            return
        
        points = point_cloud_data.raw.copy() # copy操作，不会更改raw内容
        object_ids = np.asarray(points[PointCloud.FIELD_OBJECT_ID]) # 目标id
        semantic_tags = np.asarray(points[PointCloud.FIELD_OBJECT_SEMANTIC_TAG]) # 目标语义标签id     
        unique_object_ids = np.unique(object_ids) # 得到所有不同的 object id
        unique_object_ids = unique_object_ids[unique_object_ids > 0] # 过滤掉 <=0 的 id（可能 0 代表背景 / 无效）。
        
        if len(unique_object_ids) == 0:
            return
        
        for object_id in unique_object_ids:
            actual_actor = self._context.world.get_actor(int(object_id))
            if actual_actor.type_id == 'vehicle.tesla.model3':
                continue
            if 'vehicle' in actual_actor.type_id or 'box' in actual_actor.type_id:
                object_mask = object_ids == object_id
                object_points = points[object_mask]
                object_semantic_tag = int(semantic_tags[object_mask][0]) 
                nuscenes_category_id = self.CARLA_NUSCENES_MAPPING.get(object_semantic_tag, 0)
                self._db._cursor.execute('SELECT token FROM category WHERE "seg_index" = ?', (nuscenes_category_id,))
                category_result = self._db._cursor.fetchone()
                if not category_result:
                    self.logger.warning(f'Category not found for index {nuscenes_category_id}, skipping object {object_id}')
                    continue
                category_token = category_result[0]
                if object_id not in self._known_objects:
                    instance_token = self._db.add_instance(category_token=category_token, first_annotation_token=None)
                    self._known_objects[object_id] = instance_token
                else:
                    instance_token = self._known_objects[object_id]
                actor_info = self.get_actor_info(actual_actor)
                actor_velocity = actor_info['velocity'] # 目标速度
                # 框内点的个数
                num_lidar_pts = len(object_points)
                num_radar_pts = 0
                # 可视程度
                visibility_token = '4'
                #  获取属性（attribute） 基于该 object 自己的速度
                attribute_tokens = []
                # 车辆类别：car (17), motorcycle (21), truck (23) 行人类别: rider: pedestrian (1) ,pedestrian:pedestrian
                vehicle_category_ids = [17, 21, 23]
                if nuscenes_category_id in vehicle_category_ids:
                    if actor_velocity.x > self.VEHICLE_SPEED_THRESHOLD or actor_velocity.y > self.VEHICLE_SPEED_THRESHOLD:
                        token = self.get_attribute_token("vehicle.moving")
                    else:
                        token = self.get_attribute_token("vehicle.stopped")
                    if token:
                        attribute_tokens.append(token)
                if not attribute_tokens and self._default_attribute_token:
                    attribute_tokens = [self._default_attribute_token]
                # 创建 sample_annotation 记录
                annotation_token = self._db.get_nuscenes_token()
                self._db.add_sample_annotation(
                    token=annotation_token,
                    sample_token=sample_token,
                    visibility_token=visibility_token,
                    attribute_tokens=attribute_tokens,
                    instance_token=instance_token,
                    translation=actor_info['center_translation_nus'],
                    size=actor_info["size_nus"],
                    rotation=actor_info["rotation_nu"],
                    num_lidar_pts=num_lidar_pts,
                    num_radar_pts=num_radar_pts
                )
                self._db.update_instance_annotation_links(
                instance_token=instance_token,
                annotation_token=annotation_token,)
            else:
                continue
        self.logger.debug(f'Processed {len(unique_object_ids)} objects from semantic lidar data')

    def _flush_data(self, data: BaseData, file_path: Path) -> None:
        """将传感器数据导出到磁盘

        Args:
            data (BaseData): 传感器数据
            file_path (str): 文件路径

        Returns:
            Self: 返回自身
        """
        if isinstance(data, Image):
            data.to_file(file_path)
            return None
        if isinstance(data, PointCloud):
            # nuScenes 使用 .pcd 格式存储点云
            if file_path.suffix == '.bin':
                points = data.raw
                points_x = np.asarray(points[PointCloud.FIELD_X])
                points_y = np.asarray(points[PointCloud.FIELD_Y])
                points_z = np.asarray(points[PointCloud.FIELD_Z])
                points_xyz_carla = np.stack([points_x, points_y, points_z], axis=1)
                # 将点云从 carla 的坐标系转换成 nuscenes 的坐标系
                points_xyz_nus = self.carla_lidar_points_nus_lidar(points_xyz_carla)
                # 确认点数一致
                assert points_xyz_nus.shape[0] == points.shape[0]
                points_xyz_nus = points_xyz_nus.astype(points[PointCloud.FIELD_X].dtype, copy=False)
                # 按字段写回结构化数组
                points[PointCloud.FIELD_X] = points_xyz_nus[:, 0]
                points[PointCloud.FIELD_Y] = points_xyz_nus[:, 1]
                points[PointCloud.FIELD_Z] = points_xyz_nus[:, 2]
                data.to_file(file_path)
                
                if data.format == self._carla_vehicle.POINT_FORMAT:
                    
                    lidarseg_bin_file_name = str(file_path).split('/')[-1]
                    lidarseg_bin_file_path = self._folder_lidarseg / Path(lidarseg_bin_file_name)
                    semantic_tags = np.asarray(points[PointCloud.FIELD_OBJECT_SEMANTIC_TAG])
                    mapped_semantics = np.zeros_like(semantic_tags, dtype=np.uint8)
                    for carla_id, nuscenes_id in self.CARLA_NUSCENES_MAPPING.items():
                        mapped_semantics[semantic_tags == carla_id] = nuscenes_id
                    mapped_semantics.tofile(str(lidarseg_bin_file_path))
                
                return None
        raise ValueError(f'Unsupported sensor data type: {type(data)}')

    def _export_json_files(self) -> Self:
        """导出所有 JSON 文件"""
        self.logger.info('Exporting NuScenes JSON files...')
        
        json_files = {
            self.FILE_LOG: self._db.dump_log,
            self.FILE_MAP: self._db.dump_map,
            self.FILE_SCENE: self._db.dump_scene,
            self.FILE_SAMPLE: self._db.dump_sample,
            self.FILE_SAMPLE_DATA: self._db.dump_sample_data,
            self.FILE_EGO_POSE: self._db.dump_ego_pose,
            self.FILE_CALIBRATED_SENSOR: self._db.dump_calibrated_sensor,
            self.FILE_SENSOR: self._db.dump_sensor,
            self.FILE_VISIBILITY: self._db.dump_visibility,
            self.FILE_ATTRIBUTE: self._db.dump_attribute,
            self.FILE_CATEGORY: self._db.dump_category,
            self.FILE_INSTANCE: self._db.dump_instance,
            self.FILE_SAMPLE_ANNOTATION: self._db.dump_sample_annotation,
            self.FILE_LIDARSEG: self._db.dump_lidarseg,
            self.FILE_CAN_BUS_POSE: self._db.dump_can_bus_pose,
            self.FILE_CAN_BUS_STEER_ANGLE_FEEDBACK: self._db.dump_can_bus_steer_angle_feedback,
        }
        
        for filename, dump_func in json_files.items():
            file_path = self._path / filename
            json_content = dump_func()
            with open(file_path, 'w') as f:
                f.write(json_content)
            self.logger.debug(f'Exported {filename}')
        
        self.logger.info('NuScenes JSON files exported')
        return self
    
    def _recover_missing_sample_data(self) -> Self:
        """恢复缺失的 sample_data 记录（当文件存在但 sample_data 记录缺失时）"""
        if not hasattr(self, '_sensor_tokens') or not hasattr(self, '_sensor_folders'):
            return self
        
        self._db._cursor.execute('''
            SELECT token, timestamp FROM sample ORDER BY timestamp
        ''')
        all_samples = self._db._cursor.fetchall()
        
        recovered_count = 0
        created_samples = {}
        
        for sensor in self._sensor_tokens.keys():
            sensor_recovered = self._recover_sensor_sample_data(
                sensor=sensor,
                all_samples=all_samples,
                created_samples=created_samples
            )
            recovered_count += sensor_recovered
        
        if recovered_count > 0:
            self.logger.info(f'Recovered {recovered_count} missing sample_data records')
        
        return self
    
    def _recover_sensor_sample_data(self, sensor: CarlaSensor, all_samples: list, created_samples: dict) -> int:
        """恢复单个传感器的缺失 sample_data 记录
        
        Args:
            sensor (CarlaSensor): 传感器对象
            all_samples (list): 所有 sample 记录
            created_samples (dict): 已创建的 sample 缓存
            
        Returns:
            int: 恢复的记录数量
        """
        sensor_folder = self._sensor_folders.get(sensor)
        naming_policy = self._sensor_naming_policies.get(sensor)
        
        if not (sensor_folder and naming_policy and sensor_folder.exists()):
            return 0
        
        calibrated_sensor_token = self._calibrated_sensor_tokens.get(sensor)
        if not calibrated_sensor_token:
            return 0
        
        expected_extensions = ['.jpg'] if sensor.is_camera else ['.bin'] if sensor.is_lidar else None
        if not expected_extensions:
            return 0
        
        files = [f.name for f in sensor_folder.iterdir()
                if f.is_file() and any(f.name.lower().endswith(ext) for ext in expected_extensions)]
        
        self._db._cursor.execute('''
            SELECT filename FROM sample_data WHERE calibrated_sensor_token = ?
        ''', (calibrated_sensor_token,))
        existing_files = {row[0] for row in self._db._cursor.fetchall()}
        
        recovered_count = 0
        for filename in sorted(files):
            if self._recover_single_file_sample_data(
                sensor=sensor,
                filename=filename,
                sensor_folder=sensor_folder,
                naming_policy=naming_policy,
                calibrated_sensor_token=calibrated_sensor_token,
                existing_files=existing_files,
                all_samples=all_samples,
                created_samples=created_samples
            ):
                recovered_count += 1
        
        return recovered_count
    
    def _recover_single_file_sample_data(
        self,
        sensor: CarlaSensor,
        filename: str,
        sensor_folder: Path,
        naming_policy: 'DatasetDumper.NamingPolicy',
        calibrated_sensor_token: str,
        existing_files: set,
        all_samples: list,
        created_samples: dict
    ) -> bool:
        """恢复单个文件的 sample_data 记录
        
        Args:
            sensor (CarlaSensor): 传感器对象
            filename (str): 文件名
            sensor_folder (Path): 传感器文件夹路径
            naming_policy (NamingPolicy): 命名策略
            calibrated_sensor_token (str): calibrated_sensor token
            existing_files (set): 已存在的文件集合
            all_samples (list): 所有 sample 记录
            created_samples (dict): 已创建的 sample 缓存
            
        Returns:
            bool: 是否成功恢复
        """
        file_path = (sensor_folder / filename).resolve()
        
        if not file_path.exists():
            return False
        
        relative_path = os.path.relpath(file_path, self._path)
        
        if relative_path in existing_files:
            return False
        
        frame_number = self._parse_frame_number(filename, naming_policy)
        if frame_number is None:
            return False
        
        if len(all_samples) == 0:
            self.logger.warning(f'No samples found in database, cannot recover {filename}')
            return False
        
        sample_token, ego_pose_token = self._get_or_create_sample_token(
            frame_number=frame_number,
            all_samples=all_samples,
            created_samples=created_samples
        )
        
        if not sample_token:
            return False
        
        if not ego_pose_token:
            sample_index = frame_number - 1
            if sample_index == len(all_samples) and frame_number in created_samples:
                _, ego_pose_token = created_samples[frame_number]
            else:
                ego_pose_token = self._find_ego_pose_token_by_sample(sample_token)
        
        if not ego_pose_token:
            self.logger.debug(f'No ego_pose token found for sample {sample_token}, skipping {filename}')
            return False
        
        prev_sample_data_token = self._find_prev_sample_data_token(
            calibrated_sensor_token=calibrated_sensor_token,
            sample_token=sample_token
        )
        
        self._create_recovered_sample_data(
            sensor=sensor,
            sample_token=sample_token,
            ego_pose_token=ego_pose_token,
            calibrated_sensor_token=calibrated_sensor_token,
            relative_path=relative_path,
            file_path=file_path,
            prev_sample_data_token=prev_sample_data_token
        )
        
        self.logger.debug(f'Recovered missing sample_data for {sensor.name}: {filename}')
        return True
    
    def _parse_frame_number(self, filename: str, naming_policy: 'DatasetDumper.NamingPolicy') -> int:
        """从文件名解析帧号
        
        Args:
            filename (str): 文件名
            naming_policy (NamingPolicy): 命名策略
            
        Returns:
            int: 帧号，如果解析失败返回 None
        """
        frame_number_str = filename.replace(f'.{naming_policy.extension}', '')
        try:
            return int(frame_number_str)
        except ValueError:
            return None
    
    def _get_or_create_sample_token(self, frame_number: int, all_samples: list, created_samples: dict) -> tuple:
        """获取或创建 sample token
        
        Args:
            frame_number (int): 帧号（从文件名解析，如 000001.pcd -> 1）
            all_samples (list): 所有 sample 记录（按 timestamp 排序，索引从 0 开始）
            created_samples (dict): 已创建的 sample 缓存
            
        Returns:
            tuple: (sample_token, ego_pose_token)，如果失败返回 (None, None)
        """
        # frame_number 从文件名解析（如 000001.pcd -> 1），需要减 1 才是 all_samples 的索引
        sample_index = frame_number - 1
        
        if sample_index < 0:
            self.logger.debug(f'Frame number {frame_number} is invalid (must be >= 1), skipping')
            return None, None
        elif sample_index < len(all_samples):
            sample_token = all_samples[sample_index][0]
            return sample_token, None
        elif sample_index == len(all_samples):
            if frame_number not in created_samples:
                created_samples[frame_number] = self._create_missing_sample(all_samples)
            sample_token, ego_pose_token = created_samples[frame_number]
            return sample_token, ego_pose_token
        else:
            self.logger.debug(f'Frame number {frame_number} (index {sample_index}) exceeds sample count {len(all_samples)}, skipping')
            return None, None
    
    def _create_missing_sample(self, all_samples: list) -> tuple:
        """创建缺失的 sample 和对应的 ego_pose
        
        Args:
            all_samples (list): 所有 sample 记录
            
        Returns:
            tuple: (sample_token, ego_pose_token)
        """
        last_sample_timestamp = all_samples[-1][1]
        last_sample_token = all_samples[-1][0]
        
        sample_token = self._db.get_nuscenes_token()
        new_timestamp = last_sample_timestamp + self.TIMESTAMP_INCREMENT_MICROSECONDS
        self._db.add_sample(
            scene_token=self._scene_token,
            timestamp=new_timestamp,
            prev=last_sample_token
        )
        self._db._cursor.execute('''
            UPDATE sample SET next = ? WHERE token = ?
        ''', (sample_token, last_sample_token))
        self._db._conn.commit()
        
        ego_pose_token = self._find_ego_pose_token_by_sample(last_sample_token)
        if ego_pose_token:
            new_ego_pose_token = self._create_ego_pose_from_existing(ego_pose_token, last_sample_timestamp)
            return sample_token, new_ego_pose_token
        else:
            return sample_token, None
    
    def _create_ego_pose_from_existing(self, existing_ego_pose_token: str, base_timestamp: int) -> str:
        """从现有的 ego_pose 创建新的 ego_pose
        
        Args:
            existing_ego_pose_token (str): 现有的 ego_pose token
            base_timestamp (int): 基础时间戳
            
        Returns:
            str: 新的 ego_pose token
        """
        self._db._cursor.execute('''
            SELECT translation, rotation FROM ego_pose WHERE token = ?
        ''', (existing_ego_pose_token,))
        ego_result = self._db._cursor.fetchone()
        
        if not ego_result:
            return None
        
        new_ego_pose_token = self._db.get_nuscenes_token()
        new_timestamp = base_timestamp + self.TIMESTAMP_INCREMENT_MICROSECONDS
        self._db.add_ego_pose(
            token=new_ego_pose_token,
            timestamp=new_timestamp,
            translation=json.loads(ego_result[0]),
            rotation=json.loads(ego_result[1])
        )
        return new_ego_pose_token
    
    def _find_prev_sample_data_token(self, calibrated_sensor_token: str, sample_token: str) -> str:
        """查找前一个 sample_data token
        
        Args:
            calibrated_sensor_token (str): calibrated_sensor token
            sample_token (str): sample token
            
        Returns:
            str: prev sample_data token，如果未找到返回 None
        """
        self._db._cursor.execute('''
            SELECT token FROM sample_data WHERE calibrated_sensor_token = ? AND sample_token = ? ORDER BY timestamp DESC LIMIT 1
        ''', (calibrated_sensor_token, sample_token))
        prev_result = self._db._cursor.fetchone()
        if prev_result:
            return prev_result[0]
        
        self._db._cursor.execute('''
            SELECT sd.token FROM sample_data sd
            JOIN sample s ON sd.sample_token = s.token
            WHERE sd.calibrated_sensor_token = ? AND s.timestamp < (SELECT timestamp FROM sample WHERE token = ?)
            ORDER BY s.timestamp DESC LIMIT 1
        ''', (calibrated_sensor_token, sample_token))
        prev_result = self._db._cursor.fetchone()
        return prev_result[0] if prev_result else None
    
    def _create_recovered_sample_data(
        self,
        sensor: CarlaSensor,
        sample_token: str,
        ego_pose_token: str,
        calibrated_sensor_token: str,
        relative_path: str,
        file_path: Path,
        prev_sample_data_token: str
    ) -> None:
        """创建恢复的 sample_data 记录
        
        Args:
            sensor (CarlaSensor): 传感器对象
            sample_token (str): sample token
            ego_pose_token (str): ego_pose token
            calibrated_sensor_token (str): calibrated_sensor token
            relative_path (str): 相对路径
            file_path (Path): 文件绝对路径
            prev_sample_data_token (str): 前一个 sample_data token
        """
        fileformat = 'jpg' if sensor.is_camera else 'bin'
        height = 0
        width = 0
        if sensor.is_camera:
            height = sensor.bp.get_attribute('image_size_y').as_int()
            width = sensor.bp.get_attribute('image_size_x').as_int()
        
        self._db._cursor.execute('''
            SELECT timestamp FROM sample WHERE token = ?
        ''', (sample_token,))
        timestamp_result = self._db._cursor.fetchone()
        timestamp = timestamp_result[0] if timestamp_result else 0.0
        
        sample_data_token = self._db.get_nuscenes_token()
        self._db.add_sample_data(
            token=sample_data_token,
            sample_token=sample_token,
            ego_pose_token=ego_pose_token,
            calibrated_sensor_token=calibrated_sensor_token,
            timestamp=timestamp,
            fileformat=fileformat,
            is_key_frame=True,
            height=height,
            width=width,
            filename=relative_path,
            prev=prev_sample_data_token
        )
        
        if sensor.is_lidar and 'semantic' in sensor.bp.id.lower():
            bin_filename = relative_path.split('/')[-1]
            bin_file_path = Path(self.FOLDER_LIDARSEG) / bin_filename
            if bin_file_path.exists():
                self._db.add_lidarseg(
                    token=sample_data_token,
                    sample_data_token=sample_data_token,
                    filename=bin_filename
                )
    
    def _find_sample_token_by_frame(self, frame_number: int) -> str:
        """根据帧号查找 sample token
        
        注意：frame_number 是从文件名解析的（如 000000.jpg -> 0），
        而 sample 是按时间戳排序的。如果某些帧的数据被跳过，
        需要找到对应位置的 sample。
        """
        self._db._cursor.execute('''
            SELECT token FROM sample ORDER BY timestamp LIMIT 1 OFFSET ?
        ''', (frame_number,))
        result = self._db._cursor.fetchone()
        if result:
            return result[0]
        
        self.logger.debug(f'No sample found at offset {frame_number}, trying to find by count')
        self._db._cursor.execute('''
            SELECT COUNT(*) FROM sample
        ''')
        total_samples = self._db._cursor.fetchone()[0]
        
        if frame_number < total_samples:
            self._db._cursor.execute('''
                SELECT token FROM sample ORDER BY timestamp LIMIT 1 OFFSET ?
            ''', (frame_number,))
            result = self._db._cursor.fetchone()
            return result[0] if result else None
        
        return None
    
    def _find_ego_pose_token_by_sample(self, sample_token: str) -> str:
        """根据 sample token 查找 ego_pose token"""
        self._db._cursor.execute('''
            SELECT ego_pose_token FROM sample_data WHERE sample_token = ? LIMIT 1
        ''', (sample_token,))
        result = self._db._cursor.fetchone()
        if result:
            return result[0]
        
        self._db._cursor.execute('''
            SELECT timestamp FROM sample WHERE token = ?
        ''', (sample_token,))
        result = self._db._cursor.fetchone()
        if result:
            timestamp = result[0]
            self._db._cursor.execute('''
                SELECT token FROM ego_pose WHERE timestamp = ? LIMIT 1
            ''', (timestamp,))
            result = self._db._cursor.fetchone()
            if result:
                return result[0]
        
        return None

    def _log_result(self) -> None:
        """记录导出结果"""
        if not self._path.exists():
            self.logger.error(f'Dataset export result check: False')
            self.logger.error(f'Main folder does not exist: "{self._path}"')
            return
        
        entry_counts, missing_files = self._collect_json_entry_counts()
        sample_data_list = self._load_sample_data_list()
        warnings, has_errors = self._validate_json_entry_counts(entry_counts, missing_files, sample_data_list)
        warnings, has_errors = self._validate_file_counts(entry_counts, warnings, has_errors, sample_data_list)
        self._report_validation_results(warnings, missing_files, has_errors, entry_counts)
        
        return self
    
    def _collect_json_entry_counts(self) -> tuple[dict[str, int], list[str]]:
        """收集 JSON 文件的条目数量"""
        json_files = [
            self.FILE_LOG, self.FILE_MAP, self.FILE_SCENE, self.FILE_SAMPLE,
            self.FILE_SAMPLE_DATA, self.FILE_EGO_POSE, self.FILE_CALIBRATED_SENSOR,
            self.FILE_SENSOR, self.FILE_VISIBILITY, self.FILE_ATTRIBUTE,
            self.FILE_CATEGORY, self.FILE_INSTANCE, self.FILE_SAMPLE_ANNOTATION,
            self.FILE_LIDARSEG, self.FILE_CAN_BUS_POSE, self.FILE_CAN_BUS_STEER_ANGLE_FEEDBACK
        ]
        
        missing_files = []
        entry_counts = {}
        
        for filename in json_files:
            file_path = self._path / filename
            if not file_path.exists():
                missing_files.append(filename)
                continue
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                entry_counts[filename] = len(data)
            else:
                entry_counts[filename] = 0
                self.logger.warning(f'{filename} is not a JSON array')
        
        return entry_counts, missing_files
    
    def _validate_json_entry_counts(self, entry_counts: dict[str, int], missing_files: list[str], sample_data_list: list) -> tuple[list[str], bool]:
        """验证 JSON 文件的条目数量"""
        warnings = []
        has_errors = bool(missing_files)
        
        if missing_files:
            self.logger.error(f'Dataset export result check: False')
            self.logger.error(f'Missing JSON files: {missing_files}')
        
        if self.FILE_LOG in entry_counts and entry_counts[self.FILE_LOG] != 1:
            warnings.append(f'{self.FILE_LOG}: expected 1 entry, got {entry_counts[self.FILE_LOG]}')
        
        if self.FILE_MAP in entry_counts and entry_counts[self.FILE_MAP] != 1:
            warnings.append(f'{self.FILE_MAP}: expected 1 entry, got {entry_counts[self.FILE_MAP]}')
        
        if self.FILE_SCENE in entry_counts and entry_counts[self.FILE_SCENE] != 1:
            warnings.append(f'{self.FILE_SCENE}: expected 1 entry, got {entry_counts[self.FILE_SCENE]}')
        
        if self.FILE_SENSOR in entry_counts:
            count = entry_counts[self.FILE_SENSOR]
            expected_count = len(self._sensor_tokens) if hasattr(self, '_sensor_tokens') else None
            if expected_count and count != expected_count:
                warnings.append(f'{self.FILE_SENSOR}: expected {expected_count} entries, got {count}')
            elif count == 0:
                warnings.append(f'{self.FILE_SENSOR}: has 0 entries')
        
        if self.FILE_CALIBRATED_SENSOR in entry_counts:
            count = entry_counts[self.FILE_CALIBRATED_SENSOR]
            expected_count = len(self._calibrated_sensor_tokens) if hasattr(self, '_calibrated_sensor_tokens') else None
            if expected_count and count != expected_count:
                warnings.append(f'{self.FILE_CALIBRATED_SENSOR}: expected {expected_count} entries, got {count}')
            elif count == 0:
                warnings.append(f'{self.FILE_CALIBRATED_SENSOR}: has 0 entries')
        
        if self.FILE_SAMPLE in entry_counts and self.FILE_SAMPLE_DATA in entry_counts:
            sample_count = entry_counts[self.FILE_SAMPLE]
            sample_data_count = entry_counts[self.FILE_SAMPLE_DATA]
            if sample_count > 0:
                sensor_count = len(self._sensor_tokens) if hasattr(self, '_sensor_tokens') else 0
                if sensor_count > 0:
                    expected_min = sample_count * sensor_count * 0.9
                    expected_max = sample_count * sensor_count * 1.1
                    if sample_data_count < expected_min or sample_data_count > expected_max:
                        warnings.append(f'{self.FILE_SAMPLE_DATA}: has {sample_data_count} entries, expected approximately {sample_count * sensor_count}')
        
        if self.FILE_EGO_POSE in entry_counts:
            ego_pose_count = entry_counts[self.FILE_EGO_POSE]
            sample_count = entry_counts.get(self.FILE_SAMPLE, 0)
            if sample_count > 0 and ego_pose_count != sample_count:
                warnings.append(f'{self.FILE_EGO_POSE}: has {ego_pose_count} entries, expected {sample_count}')
            elif ego_pose_count == 0:
                warnings.append(f'{self.FILE_EGO_POSE}: has 0 entries')
        
        semantic_lidar_count, semantic_lidar_sensors = self._get_semantic_lidar_info()
        if self.FILE_LIDARSEG in entry_counts:
            lidarseg_count = entry_counts[self.FILE_LIDARSEG]
            if semantic_lidar_count > 0:
                lidar_top_sample_data_count = 0
                if hasattr(self, '_sensor_tokens') and hasattr(self, '_calibrated_sensor_tokens') and sample_data_list:
                    for sensor in self._sensor_tokens.keys():
                        if sensor.is_lidar and 'semantic' in sensor.bp.id.lower():
                            calibrated_sensor_token = self._calibrated_sensor_tokens.get(sensor)
                            if calibrated_sensor_token:
                                lidar_top_sample_data_count = len([
                                    d for d in sample_data_list
                                    if d.get('calibrated_sensor_token') == calibrated_sensor_token
                                    and d.get('filename', '').endswith('.bin')
                                ])
                                break
                if lidar_top_sample_data_count > 0:
                    expected_count = lidar_top_sample_data_count
                    if lidarseg_count != expected_count:
                        warnings.append(f'{self.FILE_LIDARSEG}: has {lidarseg_count} entries, expected {expected_count}')
                elif lidarseg_count == 0:
                    warnings.append(f'{self.FILE_LIDARSEG}: has 0 entries')
            elif semantic_lidar_count > 0 and lidarseg_count == 0:
                warnings.append(f'{self.FILE_LIDARSEG}: has 0 entries')
        
        return warnings, has_errors
    
    def _get_semantic_lidar_info(self) -> tuple[int, list]:
        """获取语义激光雷达信息"""
        semantic_lidar_count = 0
        semantic_lidar_sensors = []
        if hasattr(self, '_sensor_tokens'):
            for sensor in self._sensor_tokens.keys():
                if sensor.is_lidar and 'semantic' in sensor.bp.id.lower():
                    semantic_lidar_count += 1
                    semantic_lidar_sensors.append(sensor)
        return semantic_lidar_count, semantic_lidar_sensors
    
    def _validate_file_counts(self, entry_counts: dict[str, int], warnings: list[str], has_errors: bool, sample_data_list: list) -> tuple[list[str], bool]:
        """验证实际文件数量"""
        if not (self._folder_samples and os.path.exists(self._folder_samples)):
            return warnings, has_errors
        
        if not (hasattr(self, '_sensor_tokens') and hasattr(self, '_sensor_folders')):
            return warnings, has_errors
        
        warnings = self._validate_sensor_file_counts(entry_counts, sample_data_list, warnings)
        warnings, has_errors = self._validate_lidarseg_file_counts(entry_counts, warnings, has_errors)
        
        return warnings, has_errors
    
    def _load_sample_data_list(self) -> list:
        """加载 sample_data.json 列表"""
        sample_data_path = self._path / self.FILE_SAMPLE_DATA
        if not sample_data_path.exists():
            return []
        
        with open(sample_data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _validate_sensor_file_counts(self, entry_counts: dict[str, int], sample_data_list: list, warnings: list[str]) -> list[str]:
        """验证传感器文件数量"""
        for sensor in self._sensor_tokens.keys():
            self.logger.debug(f"the sensor in _validate_sensor_file_counts is {sensor}")
            sensor_folder = self._sensor_folders.get(sensor)
            if not (sensor_folder and os.path.exists(sensor_folder)):
                continue
            
            folder_name = sensor_folder.name
            expected_extensions = ['.jpg'] if sensor.is_camera else ['.bin'] if sensor.is_lidar else None
            
            if expected_extensions:
                actual_files = [f.name for f in sensor_folder.iterdir()
                              if f.is_file() and any(f.name.lower().endswith(ext) for ext in expected_extensions)]
                actual_file_count = len(actual_files)
            else:
                actual_file_count = len([f for f in sensor_folder.iterdir() if f.is_file()])
            
            calibrated_sensor_token = self._calibrated_sensor_tokens.get(sensor)
            sensor_sample_data_count = 0
            if calibrated_sensor_token and sample_data_list:
                sensor_sample_data_count = sum(1 for sd in sample_data_list
                                             if sd.get('calibrated_sensor_token') == calibrated_sensor_token)
            
            self.logger.debug(f'Sensor folder "{folder_name}": {actual_file_count} file(s) (expected {sensor_sample_data_count})')
            
            if sensor_sample_data_count > 0 and actual_file_count != sensor_sample_data_count:
                warnings.append(f'Sensor "{folder_name}": has {sensor_sample_data_count} entries in {self.FILE_SAMPLE_DATA}, but found {actual_file_count} files')
        
        return warnings
    
    def _validate_lidarseg_file_counts(self, entry_counts: dict[str, int], warnings: list[str], has_errors: bool) -> tuple[list[str], bool]:
        """验证 lidarseg 文件数量"""
        semantic_lidar_count, semantic_lidar_sensors = self._get_semantic_lidar_info()
        if semantic_lidar_count == 0 or not hasattr(self, '_sensor_folders'):
            return warnings, has_errors
        
        lidar_bin_files = []
        for sensor in semantic_lidar_sensors:
            sensor_folder = self._sensor_folders.get(sensor)
            if sensor_folder and sensor_folder.exists():
                folder_name = sensor_folder.name
                bin_files = [f.name for f in sensor_folder.iterdir() if f.is_file() and f.name.endswith('.bin')]
                lidar_bin_files.extend(bin_files)
                self.logger.debug(f'Semantic lidar folder "{folder_name}": {len(bin_files)} .bin file(s)')
        
        if self.FILE_LIDARSEG in entry_counts:
            lidarseg_count = entry_counts[self.FILE_LIDARSEG]
            total_bin_files = len(lidar_bin_files)
            if total_bin_files != lidarseg_count:
                warnings.append(f'{self.FILE_LIDARSEG}: has {lidarseg_count} entries in JSON, but found {total_bin_files} .bin files')
                has_errors = True
        
        return warnings, has_errors
    
    def _report_validation_results(self, warnings: list[str], missing_files: list[str], has_errors: bool, entry_counts: dict[str, int]) -> None:
        """报告验证结果"""
        if warnings:
            if not missing_files and not has_errors:
                self.logger.warning(f'Dataset export result check: Warning (some entries may be skipped due to missing data)')
            else:
                self.logger.error(f'Dataset export result check: False')
            self.logger.error(f'Issues found:')
            for warning in warnings:
                self.logger.error(f'  {warning}')
        else:
            self.logger.info(f'Dataset export result check: True')
            self.logger.debug(f'JSON file entry counts:')
            for filename, count in sorted(entry_counts.items()):
                if count is not None:
                    self.logger.debug(f'  {filename}: {count} entries')