import carla
import time
import os
import re
import yaml
from pathlib import Path
from enum import Enum
from typing import Callable, List, TYPE_CHECKING
from contextlib import contextmanager

from shared.utils import Logging
from shared.simulator import CarlaTransform

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


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
        context: 'CarlaContext',
    ):
        self.logger = Logging().get_logger('Recorder')

        self._work_mode = self.WorkMode.NONE
        self._recorder_path = context.project_root / Path(context.configs.recorder.path)
        self._context = context

        self._cache_file_path: str = None
        self._cache_total_frames: int = 0
        self._cache_replay_frames: int = 0
        self._record_tick_handler = None

        self._hook_on_replay_finished: List[Callable] = []

    @property
    def recorder_path(self) -> str:
        return self._recorder_path

    @property
    def work_mode(self) -> WorkMode:
        return self._work_mode

    @contextmanager
    def record(self, path_or_file_name: str = None):
        self.start_record(path_or_file_name=path_or_file_name)
        try:
            yield
        finally:
            self.stop_record()

    @contextmanager
    def replay(self, path_or_file_name: str, *, fps: float = 20, log_interval: float = 3.0):
        self.start_replay(path_or_file_name=path_or_file_name)
        try:
            yield
        finally:
            self.spin_replay(fps=fps, log_interval=log_interval)

    def start_record(self, *, path_or_file_name: str = None):
        if self._work_mode != self.WorkMode.NONE:
            self.logger.critical(f'Program Logic Error: Recorder is already in {self._work_mode.name} mode')
            raise SystemExit(419)
        
        self._work_mode = self.WorkMode.RECORD

        # 确定文件路径
        if path_or_file_name is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            file_name = f'{timestamp}{self.RECORDER_FILE_EXTENSION}'
            file_path = os.path.join(self._recorder_path, file_name)
        else:
            file_path = path_or_file_name
            if not file_path.lower().endswith(self.RECORDER_FILE_EXTENSION):
                file_path = f'{file_path}{self.RECORDER_FILE_EXTENSION}'
            if not os.path.isabs(file_path):
                file_path = os.path.join(self._recorder_path, file_path)

            if os.path.exists(file_path):
                self.logger.critical(f'Recorder file already exists: {file_path}')
                raise SystemExit(419)

        self._cache_file_path = file_path
        self._cache_total_frames = 0

        # 程序问题警告
        self.logger.warning(f'PLEASE MAKE SURE THAT THE SENSORS ARE ALL SPAWNED BEFORE RECORDING')

        # 记录元数据
        metadata_file_path = f'{self._cache_file_path}{self.METADATA_FILE_EXTENSION}'
        with open(metadata_file_path, 'w') as f:
            yaml.dump(self._context.actors.serialize_all(), f)
        self.logger.info(f'Recorded metadata to: {metadata_file_path}')

        self._record_tick_handler = self._tick_handler
        self._context.hook_on_tick.append(self._record_tick_handler)

        self._context.client.start_recorder(self._cache_file_path)
        self.logger.info(f'Starting record, file: {self._cache_file_path}')

    def stop_record(self):
        if self._work_mode != self.WorkMode.RECORD:
            self.logger.critical(f'Program Logic Error: Recorder is not in RECORD mode')
            raise SystemExit(419)
        
        self._work_mode = self.WorkMode.NONE

        self._context.client.stop_recorder()

        if self._record_tick_handler is not None:
            try:
                self._context.hook_on_tick.remove(self._record_tick_handler)
            except Exception as e:
                self.logger.warning(f'Failed to remove tick handler: {e}')
            self._record_tick_handler = None

        file_frame_count = self._get_replay_file_frame_count(self._cache_file_path)
        self.logger.info(f'Stopping record, program frame: {self._cache_total_frames}, file frame: {file_frame_count}, file: {self._cache_file_path}')

    def start_replay(self, path_or_file_name: str):
        if self._work_mode != self.WorkMode.NONE:
            self.logger.critical(f'Program Logic Error: Recorder is already in {self._work_mode.name} mode')
            raise SystemExit(419)
        
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
            raise SystemExit(419)

        # 确定总回放帧数
        self._cache_total_frames = self._get_replay_file_frame_count(self._cache_file_path)
        if self._cache_total_frames == 0:
            self.logger.warning(f'Failed to obtain total frames from recorder file: {self._cache_file_path}')

        self._context.client.replay_file(self._cache_file_path, 0.0, 0.0, 0, False) # 不使用CARLA的传感器回放
        for _ in range(2):
            self._context.tick()
            self._cache_replay_frames += 1

        self._context.actors.find_by_name('ACTOR_001')

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

            sensor = self._context.actors.create_sensor(
                bp=actor_dump['_bp'],
                name=actor_dump['_name'],
                tf=CarlaTransform.deserialize(actor_dump['_tf_init']).to_carla(),
                parent=self._context.actors.find_by_name(actor_dump['_parent_name']),
                **actor_dump['_attributes'],
            )
            sensor.spawn()

        self._context.tick() # 执行一次 TICK(), 确保传感器对象被 SPAWN
        self._cache_replay_frames += 1

        self.logger.info(f'Starting replay, file: {self._cache_file_path}')

    def stop_replay(self):
        if self._work_mode != self.WorkMode.REPLAY:
            self.logger.critical(f'Program Logic Error: Recorder is not in REPLAY mode')
            raise SystemExit(419)
        
        self._work_mode = self.WorkMode.NONE
        self._context.client.stop_replayer(True)
        self.logger.info(f'Stopping replay')

    def spin_replay(self, *, fps: float = 20, log_interval: float = 3.0):
        if self._work_mode != self.WorkMode.REPLAY:
            self.logger.critical(f'Program Logic Error: Recorder is not in REPLAY mode')
            raise SystemExit(419)

        if fps != self._context.fps:
            self.logger.warning(f'FPS is overridden, original: {self._context.fps}, new: {fps}')
        
        try:
            while self._work_mode == self.WorkMode.REPLAY:
                self._context.tick()
                time.sleep(1/fps)
                self._cache_replay_frames += 1
                percentage = self._cache_replay_frames / self._cache_total_frames * 100
                Logging.interval(log_interval, self.logger.info, f'Replaying {percentage:.2f}%: frame: {self._cache_replay_frames}/{self._cache_total_frames}', 'replay_frame_count')

                if self._cache_replay_frames >= self._cache_total_frames:
                    self.logger.info(f'Replaying finished, frame: {self._cache_replay_frames}/{self._cache_total_frames}')
                    break
        except KeyboardInterrupt:
            self.logger.info(f'Spin replay stopped by manual interrupt')
            return

        self._work_mode = self.WorkMode.NONE
        for hook in self._hook_on_replay_finished:
            hook()

    def _get_replay_file_frame_count(self, path: str) -> int:
        """
        读取 CARLA 回放文件的总帧数
        
        Args:
            path (str): 回放文件路径

        Returns:
            int: 总帧数
        """
        try:
            info = self._context.client.show_recorder_file_info(path, False)
        except RuntimeError as e:
            self.logger.error(f'Failed to read recorder file info: {e}')
            return 0

        if not info:
            return 0

        # 解析输出中的帧数
        patterns = [
            r'total\s+frames\s*[:=]\s*(\d+)',
            r'frames?\s*[:=]\s*(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, info, re.IGNORECASE)
            if match:
                return int(match.group(1))

        self.logger.warning(f'Unable to parse frame count from recorder info: {info}')
        return 0

    def _tick_handler(self, _: carla.WorldSnapshot):
        self._cache_total_frames += 1

    @property
    def hook_on_replay_finished(self) -> List[Callable]:
        return self._hook_on_replay_finished