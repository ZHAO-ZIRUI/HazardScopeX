import time
import os
import psutil
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from typing import Callable
from typing_extensions import Self

from shared.simulator import CarlaContext, CarlaTickBlocker, CarlaSensor
from shared.data import BaseData
from shared.utils import Logging, PostInitMeta


class DatasetDumper(metaclass=PostInitMeta):

    DATASET_TYPE = 'Standard'

    @dataclass
    class NamingPolicy:
        extension: str
        zfill_length: int = 6
        zfill_char: str = '0'
    
    def __init__(
        self,
        context: CarlaContext,
        *,
        name: str | None = None,
        path: str | Path | None = None,
    ):
        """数据集导出器

        当 name 和 path 都被指定时, 将会输出到 path/name 文件夹中.

        Args:
            context (CarlaContext): 仿真上下文
            name (str | None, optional): 数据集名称. 默认为 None, 将根据时间自动生成.
            path (str | Path, optional): 数据集保存路径. 默认为 None, 将根据配置文件自动确定.
        """
        self._context = context
        self._logger = Logging().get_logger('DatasetDumper')
        self._path = self._resolve_path(name, path)

        self._tick_blocker = CarlaTickBlocker(name='DatasetDumper')
        self._frame_counter = 0
        self._data_buffer: dict[str, BaseData] = {}

        self._cached_sensor_hooks: dict[CarlaSensor, Callable] = {}

        self._hook_after_final_flush: list[Callable[[], None]] = []

    def __post_init__(self) -> Self:
        # 处理路径
        os.makedirs(self._path, exist_ok=True)
        self.logger.info(f'Dataset folder set to: {self._path}')

        # 检查路径是否合法: 存在且为空文件夹
        if not self._path.exists() or not self._path.is_dir() or len(list(self._path.iterdir())) > 0:
            self.logger.critical(f'Dataset folder is not a valid empty directory: {self._path}')
            raise SystemExit(421)

        # 注册 TickBlocker
        self._context.tick_blockers.append(self._tick_blocker)

        # 注册钩子
        self._context.hook_on_tick.append(self._update_frame_counter)
        self._context.hook_on_tick.append(self._log_on_tick)
        self._context.hook_on_tick.append(self._flash_on_memory_usage_high)
        
        # self._hook_after_final_flush.append(self._log_result)
        return self

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
        return None

    @property
    def logger(self) -> Logger:
        return self._logger

    @property
    def tick_blocker(self) -> CarlaTickBlocker:
        return self._tick_blocker

    @property
    def is_memory_safe(self) -> bool:
        """
        Returns:
            bool: 当前系统的内存使用量是否低于安全阈值
        """
        memory_usage = psutil.virtual_memory().percent / 100.0  
        return memory_usage < self._context.configs.dataset.safe_memory_usage_threshold

    def close(self) -> None:
        # 执行最终写入
        self.flush(final=True)

        # 移除 TickBlocker
        self._tick_blocker.clear()
        self._context.tick_blockers.remove(self._tick_blocker)

        # 移除钩子
        self._context.hook_on_tick.remove(self._update_frame_counter)
        self._context.hook_on_tick.remove(self._log_on_tick)
        self._context.hook_on_tick.remove(self._flash_on_memory_usage_high)

        # 移除传感器钩子
        for sensor, hook in self._cached_sensor_hooks.items():
            sensor.hook_sensor_data_ready.remove(hook)
        self._cached_sensor_hooks.clear()

        # 移除自身钩子
        self._hook_after_final_flush.clear()

        return None

    def bind_sensor_output(
        self, 
        sensor: CarlaSensor,
        path: str | Path | None = None,
        naming_policy: NamingPolicy | None = None,
    ) -> Self:
        """绑定来自传感器的输入

        Args:
            sensor (CarlaSensor): 传感器
            path (str | Path | None, optional): 文件夹路径. 默认为 None, 将根据传感器名称自动确定.
            naming_policy (NamingPolicy | None, optional): 命名策略. 默认为 None, 将根据传感器类型自动确定.

        Returns:
            Self: 返回自身
        """
        self.logger.info(f'Bind sensor output: {sensor}')

        # 解析路径
        resolved_path = (self._path / (sensor.name if path is None else path)).resolve()
        os.makedirs(resolved_path, exist_ok=True)
        self.logger.debug(f'Sensor data path set to: {resolved_path}')

        # 解析命名策略
        resolved_naming_policy = self._resolve_naming_policy(sensor, naming_policy)
        self.logger.debug(f'Sensor data naming policy set to: {resolved_naming_policy}')

        # 绑定传感器数据接收钩子
        def hook_func(data: BaseData) -> None:
            self._cache_sensor_data_to_buffer(data, resolved_path, resolved_naming_policy)
        sensor.hook_sensor_data_ready.append(hook_func)
        self._cached_sensor_hooks[sensor] = hook_func

        return self

    def flush(self, *, final: bool = False) -> None:
        """将数据集写入到磁盘"""
        self.tick_blocker.set()
        with self._context.heavy_operation():
            pass
        self.tick_blocker.clear()

        self.logger.info(f'Flushed dataset to disk ... Count: {len(self._data_buffer)} files')

        # 执行写入
        count = 0
        total = len(self._data_buffer)
        for file_path, data in self._data_buffer.items():
            self._flush_data(data, file_path)
            count += 1
            percentage = count / total * 100
            msg = f'Flushed {percentage:.2f}%: {count}/{total} files'
            Logging().interval(self._context.configs.dataset.log_interval_seconds, self.logger.info, msg, 'dataset_dumper_flush')

        Logging().cancel_interval('dataset_dumper_flush')
        self._data_buffer.clear()
        self.logger.info(f'Flushed dataset to disk completed')

        if final:
            self._data_buffer.clear()
            for hook in self._hook_after_final_flush:
                hook()
        else:
            self.logger.info(f'Memory usage is safe, continue')
        
        return None

    def _cache_sensor_data_to_buffer(self, data: BaseData, path: Path, naming_policy: NamingPolicy) -> None:
        """缓存传感器数据到内存缓存
        
        Args:
            data (BaseData): 传感器数据
            path (Path): 文件路径
            naming_policy (NamingPolicy): 命名策略

        Returns:
            None
        """
        counter_str = str(self._frame_counter).rjust(naming_policy.zfill_length, naming_policy.zfill_char)
        file_path = path / f"{counter_str}.{naming_policy.extension}"
        file_path = file_path.resolve()
        self._data_buffer[file_path] = data
        return None

    def _resolve_path(self, name: str | None, path: str | Path | None) -> Path:
        # 确定 path
        if path is None:
            path = self._context.project_root / self._context.configs.dataset.path
        else:
            path = Path(path) if isinstance(path, str) else path
            if not path.is_absolute():
                path = self._context.project_root / path
        path = path.resolve()

        # 确定 name
        if name is None:
            name = self.DATASET_TYPE + '_' + time.strftime('%Y%m%d_%H%M%S')

        return (path / name).resolve()

    def _resolve_naming_policy(self, sensor: CarlaSensor, naming_policy: NamingPolicy | None) -> NamingPolicy:
        if naming_policy is None:
            if sensor.is_camera:
                return self.NamingPolicy(extension='png')
            elif sensor.is_lidar:
                return self.NamingPolicy(extension='pcd')
            else:
                raise ValueError(f'Unsupported sensor type: {sensor.bp.id}')
        return naming_policy

    def _update_frame_counter(self, _) -> Self:
        self._frame_counter += 1
        return self

    def _log_on_tick(self, _) -> Self:
        msg = f'Frame counter: {self._frame_counter}, Memory (now/threshold): {psutil.virtual_memory().percent:.2f}/{self._context.configs.dataset.safe_memory_usage_threshold * 100:.0f}%'
        Logging().interval(self._context.configs.dataset.log_interval_seconds, self.logger.info, msg, 'dataset_dumper_log')
        return self

    def _log_result(self) -> None:
        """记录数据集导出结果"""
        # 检查主文件夹是否存在
        if not self._path.exists():
            self.logger.error(f'Dataset export result check: False')
            self.logger.error(f'Main folder does not exist: "{self._path}"')
            return
        
        # 获取所有子文件夹
        subfolders = []
        for item in self._path.iterdir():
            if item.is_dir():
                subfolders.append(item)
        
        # 统计每个子文件夹中的文件数量
        file_counts = {}
        for subfolder in subfolders:
            folder_name = subfolder.name
            files = [f for f in subfolder.iterdir() if f.is_file()]
            file_counts[folder_name] = len(files)
        
        # 检查文件数量是否一致
        counts = list(file_counts.values())
        is_consistent = len(set(counts)) == 1 if counts else False
        
        # 打印结果
        if is_consistent:
            self.logger.info(f'Dataset export result check: True')
        else:
            self.logger.error(f'Dataset export result check: False')
        
        for folder_name, count in file_counts.items():
            self.logger.debug(f'Folder "{folder_name}": {count} file(s)')
        
        return None

    def _flush_data(self, data: BaseData, file_path: Path) -> None:
        """将传感器数据导出到磁盘
        
        Args:
            data (BaseData): 传感器数据
            file_path (Path): 文件路径

        Returns:
            None
        """
        data.to_file(file_path)
        return None

    def _flash_on_memory_usage_high(self, _) -> Self:
        """当内存使用率过高时, 将数据集写入到磁盘"""
        if not self.is_memory_safe:
            self.logger.warning(f'Memory usage is too high: {psutil.virtual_memory().percent:.2f}%, flushing dataset to disk immediately')
            self.flush()
        return self

    @property
    def hook_after_final_flush(self) -> list[Callable[[], None]]:
        """在数据集写入完成后执行的钩子"""
        return self._hook_after_final_flush