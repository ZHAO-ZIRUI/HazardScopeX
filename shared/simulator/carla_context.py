import os
import platform
import subprocess
import time
import random
import socket
import uuid
import carla
import threading
import gc
from pathlib import Path
from typing import Callable
from typing_extensions import Self
from logging import Logger
from contextlib import contextmanager

from shared.configs import ExternalConfigReader, ConfigManager
from shared.utils import Logging
from shared.simulator import CarlaTickBlocker, CarlaActorManager, CarlaMaps, CarlaIOManager


class CarlaContext:
    """
    CARLA 上下文, 管理仿真的生命周期和行为
    """

    def __init__(
        self,
        config: ExternalConfigReader | Path = Path('config.yaml'),
    ):
        self._logger = Logging().get_logger('Context')

        self._client: None | carla.Client = None
        self._thread_dead_detector: None | threading.Thread = None
        self._tick_blockers: list[CarlaTickBlocker] = []

        self._evnet_server_dead: threading.Event = threading.Event()
        self._event_shutdown: threading.Event = threading.Event()
        self._event_heavy_operation: threading.Event = threading.Event()

        self._service_config_manager = ConfigManager().load(config)
        self._service_actor_manager: CarlaActorManager = CarlaActorManager(self)
        self._service_io_manager: CarlaIOManager = CarlaIOManager(self)

        self._hook_on_tick: list[Callable[[carla.WorldSnapshot], None]] = []
        
        self.__post_init__()

    def __post_init__(self):
        self.logger.debug('Initialized')

    def __enter__(self) -> Self:
        self.bringup()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.teardown()

    @property
    def tick_blockers(self) -> list[CarlaTickBlocker]:
        return self._tick_blockers

    @property
    def logger(self) -> Logger:
        return self._logger

    @property
    def project_root(self) -> Path:
        """项目根目录"""
        return Path(__file__).parent.parent.parent

    @property
    def fps(self) -> float:
        """同步模式帧数, 单位: FPS"""
        return self.configs.context.runtime_sync_mode_fps

    @property
    def client(self) -> carla.Client:
        """carla.Client 实例别名"""
        if self._client is None:
            self._client = carla.Client(self.configs.context.server_host, self.configs.context.server_port)
            self._client.set_timeout(self.configs.context.runtime_timeout_seconds)
        return self._client

    @property
    def world(self) -> carla.World:
        """carla.World 实例别名"""
        return self.client.get_world()

    @property
    def map(self) -> carla.Map:
        """carla.Map 实例别名"""
        return self.world.get_map()

    @property
    def traffic(self) -> carla.TrafficManager:
        """carla.TrafficManager 实例别名"""
        return self.client.get_trafficmanager()

    @property
    def spawn_points(self) -> list[carla.Transform]:
        """carla.Transform 实例列表"""
        return self.world.get_map().get_spawn_points()

    @property
    def configs(self) -> ConfigManager:
        return self._service_config_manager

    @property
    def actors(self) -> CarlaActorManager:
        return self._service_actor_manager

    @property
    def io(self) -> CarlaIOManager:
        return self._service_io_manager

    @contextmanager
    def heavy_operation(self):
        """重操作, 该模式下会设置所有的 Timeout 为 heavy_operation_timeout_seconds, 并临时跳过死检"""
        self.client.set_timeout(self.configs.context.runtime_heavy_operation_timeout_seconds)
        self._event_heavy_operation.set()
        self.logger.debug('Entering heavy operation mode ...')
        yield
        self._event_heavy_operation.clear()
        self.client.set_timeout(self.configs.context.runtime_timeout_seconds)
        self.logger.debug('Exiting heavy operation mode')

    def bringup(self):
        """启动 CARLA 上下文"""
        if not self.configs.context.server_self_managed_enabled:
            self.logger.warning('Using external CARLA server')
        else:
            self.server_bringup()

        # 等待服务端可用
        self.wait_server_available()

        # 进入同步模式
        settings = self.world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 1/self.configs.context.runtime_sync_mode_fps
        self.world.apply_settings(settings)

        # 启动死检测线程
        self._thread_dead_detector = threading.Thread(target=self._threadfunc_dead_detector)
        self._thread_dead_detector.start()

    def teardown(self):
        """关闭 CARLA 上下文"""
        # 停止死检测线程
        self._event_shutdown.set()
        self._thread_dead_detector.join(timeout=1.0)

        # 销毁过程
        self.io.destroy_all()
        self.actors.destroy_all()
        self.traffic.shut_down()

        # 清理 hook
        self._hook_on_tick.clear()

        # 清理 tick blockers
        self._tick_blockers.clear()

        # 清理 client
        del self._client
        self._client = None

        # 强制垃圾回收
        gc.collect()

        # 停止服务端进程
        if not self.configs.context.server_self_managed_enabled:
            self.logger.warning('Using external CARLA server, server teardown is ignored')
        else:
            self.server_teardown()

    def server_bringup(self):
        # 二次阻止在未启用自管理模式时启动服务端进程
        if not self.configs.context.server_self_managed_enabled:
            return
        
        # 清理服务端进程, 防止残留
        if self._has_server_process():
            self._server_kill()
            wait_time = self.configs.context.server_bringup_after_kill_wait_seconds
            self.logger.info(f'CARLA server processes cleaned up, wait {wait_time} seconds before bringing up again ...')
            time.sleep(wait_time)

        # 启动服务端进程
        if self.configs.context.server_multi_gpu_enabled:
            # 启动主进程
            cmd_primary = [
                self.configs.context.server_self_managed_exe_path, 
                '-nullrhi', 
                f'-carla-rpc-port={self.configs.context.server_port}', 
                f'-carla-primary-port={self.configs.context.server_port + self.configs.context.server_multi_gpu_port_offset}',
            ]
            self._server_launch(cmd_primary)
            self.logger.info(f'CARLA server primary process started, port: {self.configs.context.server_port}')

            # 启动渲染进程
            for gpu_id in self.configs.context.server_multi_gpu_ids:
                rpc_port = self._get_random_free_port(20000, 30000)
                cmd_render = [
                    self.configs.context.server_self_managed_exe_path, 
                    '-RenderOffscreen', 
                    f'-carla-rpc-port={rpc_port}',
                    f'-carla-primary-port={self.configs.context.server_port + self.configs.context.server_multi_gpu_port_offset}',
                    f'-carla-primary-host={self.configs.context.server_host}',
                    f'-ini:[/Script/Engine.RendererSettings]:r.GraphicsAdapter={gpu_id}'
                ]
                self._server_launch(cmd_render)
                self.logger.info(f'CARLA server render process started, port: {rpc_port}, gpu: {gpu_id}')
        else:
            # 启动正常进程
            cmd_normal = [
                self.configs.context.server_self_managed_exe_path, 
                '-RenderOffscreen', 
                f'-carla-rpc-port={self.configs.context.server_port}'
            ]
            self._server_launch(cmd_normal)
            self.logger.info(f'CARLA server normal process started, port: {self.configs.context.server_port}')

    def server_teardown(self):
        """停止 CARLA 服务端"""
        self._server_kill()
        self.logger.info('CARLA server teared down')

    def wait_server_available(self):
        """等待服务端可用"""
        self.logger.info('Waiting for CARLA server available ...')

        # 初始等待
        if self.configs.context.server_self_managed_enabled:
            self.logger.debug(f'Waiting {self.configs.context.server_bringup_init_wait_seconds} seconds first ...')
            time.sleep(self.configs.context.server_bringup_init_wait_seconds)

        timeout = 1/self.configs.context.runtime_sync_mode_fps * 2  # 两个帧的周期
        client = carla.Client(self.configs.context.server_host, self.configs.context.server_port)
        client.set_timeout(timeout)

        frame = 0
        token = str(uuid.uuid4())  # 用于日志
        timer = time.perf_counter()
        while frame == 0:
            if time.perf_counter() - timer > self.configs.context.server_bringup_timeout_seconds:
                msg = f'CARLA server is not available until timeout, please check the if existing a server process'
                self.logger.critical(msg)
                raise RuntimeError(msg)
            try:
                world = client.get_world()
                world.tick()  # 这里强行进行 tick, 因为不清楚 server 是否处在同步模式
                frame = world.get_snapshot().frame
            except RuntimeError:
                Logging.interval(1, self.logger.debug, f'CARLA server is not available now, retrying ...', token)

                # 报告 RuntimeError 后, 客户端需要重建
                client = carla.Client(self.configs.context.server_host, self.configs.context.server_port)
                client.set_timeout(timeout)
                continue
        
        Logging.cancel_interval(token)
        self._client = client
        self._client.set_timeout(self.configs.context.runtime_timeout_seconds)
        self.logger.info('CARLA server is available now')

    def tick(self, *, force: bool = False):
        """手动 Tick 服务端, 在此处应用 TickBlocker """
        time_begin = time.perf_counter()

        # TickBlocker 阻塞
        try:
            while not force and not self._event_shutdown.is_set():
                all_passed = all(not blocker.is_set() for blocker in self._tick_blockers)
                if all_passed:
                    break
                if time.perf_counter() - time_begin > self.configs.context.runtime_blocker_timeout_seconds:
                    # 报告 TickBlocker 阻塞统计状态
                    count_blocked = len([blocker for blocker in self._tick_blockers if blocker.is_set()])
                    count_all = len(self._tick_blockers)
                    msg = f"Tick blocker timeout, status: {count_blocked} blocked, total: {count_all}"
                    Logging.interval(1, self.logger.warning, msg, 'tick_blocker_timeout_msg')

                    # 报告 TickBlocker 阻塞详情
                    blocker_status = 'Tick blocker details (blocked): '
                    for blocker in self._tick_blockers:
                        if blocker.is_set():
                            blocker_status += f"{str(blocker)}, "
                    Logging.interval(1, self.logger.warning, blocker_status, 'tick_blocker_details_blocked')
                
                # 等待防止过度 CPU 占用
                time.sleep(1/self.configs.context.runtime_sync_mode_fps)
        except KeyboardInterrupt:
            raise SystemExit(100)

        # 执行 TICK
        self.world.tick()

        # 自动设置 TickBlocker
        for blocker in self._tick_blockers:
            if blocker.auto_set_after_tick:
                blocker.set()

        # 执行钩子
        for hook in self._hook_on_tick:
            hook(self.world.get_snapshot())

    def spin(self):
        """自动 Tick 服务端"""
        self.logger.info('Context begin to spin ...')
        try:
            while not self._event_shutdown.is_set() and not self._evnet_server_dead.is_set():
                self.tick()
                time.sleep(1/self.configs.context.runtime_sync_mode_fps)
        except KeyboardInterrupt:
            self.logger.info('Spin stopped by manual interrupt')
            return

    def wait_seconds(self, seconds: float):
        """等待指定秒数"""
        self.logger.info(f'Waiting {seconds} seconds ...')
        begin = time.perf_counter()
        while time.perf_counter() - begin < seconds:
            self.tick()
            time.sleep(1/self.configs.context.runtime_sync_mode_fps)
        self.logger.debug(f'Waiting finished: {seconds} seconds')
        return self

    def wait_ticks(self, ticks: int):
        """等待指定帧数"""
        self.logger.info(f'Waiting {ticks} ticks ...')
        tick_counter = 0
        while tick_counter < ticks:
            self.tick()
            tick_counter += 1
            time.sleep(1/self.configs.context.runtime_sync_mode_fps)
        self.logger.debug(f'Waiting finished: {ticks} ticks')

    def change_map(self, map: str | CarlaMaps):
        with self.heavy_operation():
            if isinstance(map, CarlaMaps):
                map_name = map.value
            else:
                map_name = map
            self.client.load_world(map_name)
            self.world.tick()  # 这里使用 carla.world.tick()
            self.logger.info(f'Map changed to {map_name}, fullname: "{self.world.get_map().name}"')

    def _server_kill(self):
        """终止所有 CARLA 服务端进程, 该方法强制通过操作系统的进程管理器终止进程"""
        if platform.system() == 'Windows':
            cmd_kill_ue4 = ['taskkill', '/F', '/T', '/IM', 'CarlaUE4.exe']
            cmd_kill_shipping = ['taskkill', '/F', '/T', '/IM', 'CarlaUE4-Win64-Shipping.exe']
            subprocess.run(cmd_kill_ue4, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(cmd_kill_shipping, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif platform.system() == 'Linux':
            cmd_kill_ue4 = ['pkill', '-9', '-f', 'CarlaUE4']
            subprocess.run(cmd_kill_ue4, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            raise NotImplementedError(f"Unsupported platform: {platform.system()}")

    def _server_launch(self, cmd: list[str]):
        """启动服务端进程的辅助函数

        在 Linux 上使用 preexec_fn 隔离进程组, 避免 SIGINT 信号传播到子进程, 以处理无法收到数据的问题.
        
        Args:
            cmd (list[str]): 启动服务端进程的命令
        """
        cmd = ' '.join(cmd)
        preexec_fn = os.setsid if platform.system() == 'Linux' else None
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=preexec_fn)

    def _has_server_process(self) -> bool:
        """检查是否存在服务端进程"""
        if platform.system() == 'Windows':
            case1 = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq CarlaUE4.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
            case2 = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq CarlaUE4-Win64-Shipping.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
            return case1 or case2
        elif platform.system() == 'Linux':
            return subprocess.run(['pgrep', '-f', 'CarlaUE4'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        else:
            raise NotImplementedError(f"Unsupported platform: {platform.system()}")

    def _get_random_free_port(self, begin: int = 20000, end: int = 30000, max_attempts: int = 100):
        """获取一个随机可用的端口"""
        for _ in range(max_attempts):
            port = random.randint(begin, end)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                try:
                    sock.bind(('', port))
                    return port
                except OSError:
                    continue
        raise RuntimeError(f"No free port found in range {begin}-{end} after {max_attempts} attempts")

    def _threadfunc_dead_detector(self):
        """检测服务端是否存活的线程"""
        self.logger.debug('Server dead detector started')
        
        check_timeout = 1/self.configs.context.runtime_sync_mode_fps * 5  # 5个帧的周期
        detector_client = carla.Client(self.configs.context.server_host, self.configs.context.server_port)
        detector_client.set_timeout(check_timeout)
        
        try:
            while not self._evnet_server_dead.is_set() and not self._event_shutdown.is_set():
                try:
                    if not self._event_heavy_operation.is_set():
                        detector_client.get_server_version()
                    time.sleep(check_timeout)
                except Exception as e:
                    msg = f'CARLA server is DEAD, detected by detector thread: {type(e).__name__}'
                    self.logger.critical(msg)
                    self._evnet_server_dead.set()
                    raise RuntimeError(msg)
        finally:
            del detector_client
            self.logger.debug('Server dead detector stopped')

    @property
    def hook_on_tick(self) -> list[Callable[[carla.WorldSnapshot], None]]:
        return self._hook_on_tick