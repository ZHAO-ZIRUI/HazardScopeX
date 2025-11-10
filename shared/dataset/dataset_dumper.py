import psutil
import threading
import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict
from typing_extensions import Self

from shared.utils import Logging
from shared.data import BaseData
from shared.simulator import CarlaSensor

if TYPE_CHECKING:
    from shared.simulator import CarlaContext


class DatasetDumper:
    """
    导出数据/数据集工具的基类
    """

    DATASET_CLASS = 'Basic'
    SAFE_MEMORY_USAGE_THRESHOLD = 0.95

    @dataclass
    class NamingPolicy:
        extension: str
        zfill_length: int = 6
        zfill_char: str = '0'

    def __init__(
        self,
        context: 'CarlaContext',
        folder_path: str,
        *,
        name: str = None,
        safe_memory_usage_threshold: float = SAFE_MEMORY_USAGE_THRESHOLD,
        create_folder: bool = True
    ):
        """初始化数据集导出器

        Args:
            context (CarlaContext): 仿真上下文
            folder_path (str): 数据集保存路径
            name (str, optional): 数据集名称. 默认为 None, 将根据时间自动生成.
            safe_memory_usage_threshold (float, optional): 安全内存使用阈值, 当内存使用率超过该阈值时, 将自动导出数据集到磁盘. 默认为 SAFE_MEMORY_USAGE_THRESHOLD.
            create_folder (bool, optional): 是否创建数据集文件夹, 如果为 False, 则需要确保数据集文件夹存在. 默认为 True.
        """
        self.logger = Logging().get_logger(self.DATASET_CLASS)
        
        self._context = context
        self._safe_memory_usage_threshold = safe_memory_usage_threshold
        self._folder_path = folder_path
        self._name = name
        self._create_folder = create_folder

        self._tick_blocker = threading.Event()
        self._dataset: Dict[str, BaseData] = {}
        self._frame_counter = 1

        self.logger.info(f'Initialized {self.DATASET_CLASS} exporter')
        self._post_init()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.flush()
        return

    @property
    def tick_blocker(self) -> threading.Event:
        """TICK 阻塞器, 用于阻塞 TICK 过程, 直到 IO 或 内存 操作完成

        Returns:
            threading.Event: TICK 阻塞器
        """
        return self._tick_blocker

    def _post_init(self) -> Self:
        self._context.bind_tick_blocker(self.DATASET_CLASS, self._tick_blocker)
        self._context.hook_on_tick.append(self._update_frame_counter)
        self._context.hook_on_tick.append(self._flash_on_memory_usage_high)
        
        # 确定路径
        base_folder = os.path.join(self._context.project_root, self._folder_path)
        base_folder = os.path.abspath(base_folder)
        if self._name is None:
            self._name = self.DATASET_CLASS + '_' + time.strftime('%Y%m%d_%H%M%S')
        base_folder = os.path.join(base_folder, self._name)
        self._folder_path = base_folder

        if self._create_folder:
            os.makedirs(self._folder_path, exist_ok=True)
            self.logger.info(f'Dataset folder set to: {self._folder_path}')
        elif not os.path.exists(self._folder_path):
            self.logger.critical(f'Dataset folder does not exist: {self._folder_path}')
            raise SystemExit(201)

        return Self

    def _get_memory_usage(self) -> float:
        """获取操作系统内存使用情况

        Returns:
            float: 内存占用百分比, 0.0 ~ 1.0
        """
        return psutil.virtual_memory().percent / 100.0

    def _is_memory_usage_safe(self) -> bool:
        """检查内存使用情况是否安全

        Returns:
            bool: 是否安全
        """
        return self._get_memory_usage() < self._safe_memory_usage_threshold

    def flush(self) -> Self:
        """将内存中的数据导出到磁盘"""
        self.tick_blocker.set()
        self.logger.info(f'Flushing dataset to disk ... ({len(self._dataset)} files)')

        total = len(self._dataset)
        count = 0
        log_token = 'flush_dataset'

        for file_path, data in self._dataset.items():
            data.to_file(file_path)
            count += 1
            percentage = count / total * 100
            Logging().interval(2, self.logger.info, f'Flushed {percentage:.2f}%: {count}/{total} files', log_token)
        
        Logging().cancel_interval(log_token)
        self._dataset.clear()
        self._frame_counter = 0
        self.tick_blocker.clear()

        self.logger.info(f'Flushed dataset to disk completed')
        return self

    def bind_sensor_output(self, sensor: CarlaSensor, folder_path: str, naming_policy: NamingPolicy = None) -> Self:
        """绑定传感器数据输出到内存缓存

        Args:
            sensor (CarlaSensor): 传感器
            folder_path (str): 文件夹路径
            naming_policy (NamingPolicy, optional): 命名策略. 默认为 None, 将根据传感器类型自动确定.

        Raises:
            ValueError: 不支持的传感器类型
            FileExistsError: 文件已存在

        Returns:
            Self: 返回自身
        """
        # 确定默认命名策略
        if naming_policy is None:
            if sensor.bp.id.lower().startswith('sensor.camera.'):
                naming_policy = self.NamingPolicy(extension='jpg')
            elif sensor.bp.id.lower().startswith('sensor.lidar.'):
                naming_policy = self.NamingPolicy(extension='pcd')
            else:
                raise ValueError(f"Unsupported sensor type: {sensor.bp.id}")
        
        # 建立子文件夹
        folder_path = os.path.join(self._folder_path, folder_path)
        folder_path = os.path.abspath(folder_path)
        os.makedirs(folder_path, exist_ok=True)
        self.logger.debug(f'Created data set sub folder: {folder_path}')
    
        # 绑定传感器数据接收钩子
        sensor.hook_sensor_data_ready.append(
            lambda data: self._store_sensor_data(data, folder_path, naming_policy)
        )
        return self

    def _store_sensor_data(self, data: BaseData, folder_path: str, naming_policy: NamingPolicy) -> Self:
        """存储传感器数据到内存缓存
        
        Args:
            data (BaseData): 传感器数据
            folder_path (str): 文件夹路径
            naming_policy (NamingPolicy): 命名策略

        Returns:
            Self: 返回自身
        """
        counter_str = str(self._frame_counter).rjust(naming_policy.zfill_length, naming_policy.zfill_char)
        file_path = os.path.join(folder_path, f"{counter_str}.{naming_policy.extension}")
        file_path = os.path.abspath(file_path)
        if os.path.exists(file_path):
            raise FileExistsError(f"File already exists: {file_path}")

        self._dataset[file_path] = data
        return self

    def _update_frame_counter(self, _) -> Self:
        self._frame_counter += 1
        return self

    def _flash_on_memory_usage_high(self) -> Self:
        """当内存使用率过高时, 将数据导出到磁盘"""
        if not self._is_memory_usage_safe():
            self.logger.warning(f'Memory usage is too high: {self._get_memory_usage():.2f}%, flushing dataset to disk immediately')
            self.flush()
        return self