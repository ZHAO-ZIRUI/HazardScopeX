import carla
import time
import os
import yaml
from enum import Enum

from shared.utils import Logging
from shared.simulator import CarlaActorManager, CarlaTransform


class CarlaRecorder:
    """
    CARLA 记录器, 用于记录或回放仿真数据
    """

    RECORDER_FILE_EXTENSION = '.carla'
    METADATA_FILE_EXTENSION = '.yaml'

    class WorkMode(Enum):
        NONE = 0
        RECORD = 1
        REPLAY = 2

    def __init__(
        self,
        client: carla.Client,
        actor_manager: CarlaActorManager,
        recorder_path: str = './recorders',
    ):
        self.logger = Logging().get_logger('Recorder')

        self._work_mode = self.WorkMode.NONE
        self._recorder_path = recorder_path

        self._client = client
        self._actor_manager = actor_manager

        self._cache_file_path: str = None

    @property
    def recorder_path(self) -> str:
        return self._recorder_path

    @property
    def work_mode(self) -> WorkMode:
        return self._work_mode

    def start_record(self):
        if self._work_mode != self.WorkMode.NONE:
            self.logger.critical(f'Program Logic Error: Recorder is already in {self._work_mode.name} mode')
            raise SystemExit(1)
        
        self._work_mode = self.WorkMode.RECORD

        # 确定文件路径
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        file_name = f'{timestamp}{self.RECORDER_FILE_EXTENSION}'
        file_path = os.path.join(self._recorder_path, file_name)
        self._cache_file_path = file_path

        # 记录元数据
        metadata_file_path = f'{self._cache_file_path}{self.METADATA_FILE_EXTENSION}'
        with open(metadata_file_path, 'w') as f:
            yaml.dump(self._actor_manager.serialize(), f)
        self.logger.info(f'Recorded metadata to: {metadata_file_path}')

        self._client.start_recorder(self._cache_file_path)
        self.logger.info(f'Starting record, file: {self._cache_file_path}')

    def stop_record(self):
        if self._work_mode != self.WorkMode.RECORD:
            self.logger.critical(f'Program Logic Error: Recorder is not in RECORD mode')
            raise SystemExit(1)
        
        self._work_mode = self.WorkMode.NONE

        self._client.stop_recorder()
        self.logger.info(f'Stopping record, file {self._cache_file_path}')

    def start_replay(self, path_or_file_name: str, *, replay_sensors: bool = False):
        if self._work_mode != self.WorkMode.NONE:
            self.logger.critical(f'Program Logic Error: Recorder is already in {self._work_mode.name} mode')
            raise SystemExit(1)
        
        self._work_mode = self.WorkMode.REPLAY

        # 确定是文件还是路径
        is_full_path = len(path_or_file_name.split(os.path.sep)) > 1
        
        if is_full_path:
            if not path_or_file_name.lower().endswith(self.RECORDER_FILE_EXTENSION):
                self._cache_file_path = f'{path_or_file_name}{self.RECORDER_FILE_EXTENSION}'
            else:
                self._cache_file_path = path_or_file_name
        else:
            if not path_or_file_name.lower().endswith(self.RECORDER_FILE_EXTENSION):
                file_name = f'{path_or_file_name}{self.RECORDER_FILE_EXTENSION}'
            else:
                file_name = path_or_file_name
            self._cache_file_path = os.path.join(self._recorder_path, file_name)
        
        # 确定文件是否存在
        if not os.path.exists(self._cache_file_path):
            self.logger.critical(f'Recorder file does not exist: {self._cache_file_path}')
            raise SystemExit(1)
        
        self._client.replay_file(self._cache_file_path, 0.0, 0.0, 0, False) # 不使用CARLA的传感器回放
        for _ in range(2):
            self._client.get_world().tick()

        self._actor_manager.find_by_name('ACTOR_001')

        # 重建传感器
        metadata = None
        metadata_file_path = f'{self._cache_file_path}{self.METADATA_FILE_EXTENSION}'
        if not os.path.exists(metadata_file_path):
            self.logger.error(f'Metadata file does not exist: {metadata_file_path}')
            self.logger.error(f'Sensor reconstruction is ignored')
            return

        with open(metadata_file_path, 'r') as f:
            metadata = yaml.load(f, Loader=yaml.FullLoader)

        for actor_dump in metadata:
            if not actor_dump['_bp'].lower().startswith('sensor.'):
                continue

            sensor = self._actor_manager.create_sensor(
                bp=actor_dump['_bp'],
                name=actor_dump['_name'],
                tf=CarlaTransform.deserialize(actor_dump['_tf_init']).to_carla(),
                parent=self._actor_manager.find_by_name(actor_dump['_parent_name']),
                **actor_dump['_attributes'],
            )
            sensor.spawn(self._client.get_world())

        self._client.get_world().tick() # 执行一次 TICK(), 确保传感器对象被 SPAWN
        
        self.logger.info(f'Starting replay, file: {self._cache_file_path}') 
