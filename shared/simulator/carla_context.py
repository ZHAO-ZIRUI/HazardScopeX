import carla
import random
import socket
import subprocess
import platform
import time
import uuid
import threading
from typing_extensions import Self


from shared.utils import Config, Logging


class CarlaContext:
    """
    CARLA 上下文, 管理仿真的生命周期和行为
    """

    MULTI_GPU_PORT_OFFSET = 2
    RESTART_INTERVAL = 3
    CLIENT_CONNECTION_CHECK_TIMEOUT_OFFSET = 0.1

    def __init__(
        self,
        host: str,
        port: int,
        timeout: float,
        *,
        exe_path: str,
        use_external_server: bool = False,
        restart_on_failure: bool = True,
        sync_mode_fps: float = 20,
        gpus: list[int] = [],
        server_start_wait_time: float = 5,
        server_start_timeout: float = 10,
    ):
        self.logger = Logging().get_logger('CarlaContext')

        self._host = host
        self._port = port
        self._timeout = timeout
        self._exe_path = exe_path
        self._use_external_server = use_external_server
        self._restart_on_failure = restart_on_failure
        self._sync_mode_fps = sync_mode_fps
        self._gpus = gpus
        self._server_start_wait_time = server_start_wait_time
        self._server_start_timeout = server_start_timeout

        self._client: None | carla.Client = None
        self._thread_dead_detector: None | threading.Thread = None
        self._thread_restarter: None | threading.Thread = None
        self._event_server_dead: threading.Event = threading.Event()
        self._event_manual_restart: threading.Event = threading.Event()

        # 执行初始化后处理
        self._post_init()

    def __enter__(self) -> Self:
        self.bringup()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.shutdown()

    def _post_init(self):
        self.logger.info('Initlialized')
        if self._use_external_server:
            self.logger.warning('Using external CARLA server')

    @property
    def client(self) -> carla.Client:
        if self._client is None:
            self._client = carla.Client(self._host, self._port)
            self._client.set_timeout(self._timeout)
        return self._client

    @property
    def world(self) -> carla.World:
        return self.client.get_world()

    @property
    def traffic_manager(self) -> carla.TrafficManager:
        return self.client.get_trafficmanager()

    @property
    def blueprint_library(self) -> carla.BlueprintLibrary:
        return self.world.get_blueprint_library()

    def tick(self):
        self.world.tick()

    def bringup(self):
        if not self._use_external_server:
            self.server_start()
        self.wait_server_available()
        self.start_dead_detector_thread()
        if self._restart_on_failure and not self._use_external_server:
            self.start_restarter_thread()

    def shutdown(self):
        self._event_server_dead.set()
        self.server_stop()
        self.logger.info('Shutdown')

    def server_start(self):
        """启动 CARLA 服务端"""
        self._server_start_primary()
        for gpu_id in self._gpus:
            self._server_start_render(gpu_id)
    
    def server_stop(self):
        """停止 CARLA 服务端"""
        del self._client
        self._client = None
        self._server_kill()
        self.logger.info('CARLA server killed')

    def server_restart(self):
        """重启 CARLA 服务端"""
        self.server_stop()
        self._event_manual_restart.set()
        time.sleep(self.RESTART_INTERVAL)
        self.bringup()
        self.logger.info('CARLA server restart completed')
        self._event_manual_restart.clear()

    def wait_server_available(self):
        """等待服务端可用"""
        self.logger.debug(f'Waiting {self._server_start_wait_time} seconds first ...')
        time.sleep(self._server_start_wait_time)

        self.logger.info('Waiting for CARLA server available ...')
        timeout = 1/self._sync_mode_fps + self.CLIENT_CONNECTION_CHECK_TIMEOUT_OFFSET
        client = carla.Client(self._host, self._port)
        client.set_timeout(timeout)

        frame = 0
        token = str(uuid.uuid4())
        timer = time.perf_counter()
        while frame == 0:
            if time.perf_counter() - timer > self._server_start_timeout:
                self.logger.critical('CARLA server is not available until timeout, please check the if existing a server process')
                exit(1)
            try:
                world = client.get_world()
                world.tick()
                frame = world.get_snapshot().frame
            except Exception as e:
                time.sleep(timeout)
                Logging.interval(1, self.logger.debug, f'CARLA server is not available now, retrying ...', token)
                continue
        
        Logging.cancel_interval(token)
        self._client = client
        self._client.set_timeout(self._timeout)
        self.logger.info('CARLA server is available now')

    def start_dead_detector_thread(self):
        """启动服务端死亡检测线程"""
        # 等待旧进程退出
        self._event_server_dead.set()
        if self._thread_dead_detector is not None and self._thread_dead_detector.is_alive():
            self.logger.debug('Waiting for old detector thread to stop...')
            self._thread_dead_detector.join(timeout=1.0)
        
        # 清除事件，启动新线程
        self._event_server_dead.clear()
        self._thread_dead_detector = threading.Thread(target=self._thread_func_dead_detector, daemon=True)
        self._thread_dead_detector.start()

    def start_restarter_thread(self):
        """启动服务端重启线程"""
        if self._thread_restarter is None:
            self._thread_restarter = threading.Thread(target=self._thread_func_restarter, daemon=True)
            self._thread_restarter.start()

    def _server_start_primary(self):
        """以 nullrhi 模式启动 CARLA 服务端的主进程, 该进程不进行任何渲染"""
        cmd = [self._exe_path]
        cmd.append('-nullrhi')
        cmd.append(f'-carla-rpc-port={self._port}')
        cmd.append(f'-carla-primary-port={self._port + self.MULTI_GPU_PORT_OFFSET}')
        cmd = ' '.join(cmd)

        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.logger.info(f'CARLA server primary process started, port: {self._port}, primary port: {self._port + self.MULTI_GPU_PORT_OFFSET}')

    def _server_start_render(self, gpu_id: int = 0):
        """CARLA 服务端的渲染进程
        
        Args:
            gpu_id (int): 使用的 GPU 编号, 通过 nvidia-smi 命令查看
        """
        rpc_port = self._get_random_free_port(20000, 30000)
        cmd = [self._exe_path]
        cmd.append('-RenderOffscreen')  # 即便不添加该参数, 其主画面也会为空
        cmd.append(f'-carla-rpc-port={rpc_port}')
        cmd.append(f'-carla-primary-port={self._port + self.MULTI_GPU_PORT_OFFSET}')
        cmd.append(f'-carla-primary-host=127.0.0.1')
        cmd.append(f'-ini:[/Script/Engine.RendererSettings]:r.GraphicsAdapter={gpu_id}')
        cmd = ' '.join(cmd)

        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.logger.info(f'CARLA server render process started, port: {rpc_port}, primary port: {self._port + self.MULTI_GPU_PORT_OFFSET}, gpu: {gpu_id}')

    def _server_kill(self):
        """终止所有 CARLA 服务端进程（批量终止）"""
        if platform.system() == 'Windows':
            subprocess.run(['taskkill', '/F', '/T', '/IM', 'CarlaUE4.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['taskkill', '/F', '/T', '/IM', 'CarlaUE4-Win64-Shipping.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif platform.system() == 'Linux':
            subprocess.run(['pkill', '-9', '-f', 'CarlaUE4'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

    def _thread_func_dead_detector(self):
        """检测服务端是否存活的线程"""
        self.logger.debug('Thread dead detector started')
        
        check_timeout = 1/self._sync_mode_fps + self.CLIENT_CONNECTION_CHECK_TIMEOUT_OFFSET
        detector_client = carla.Client(self._host, self._port)
        detector_client.set_timeout(check_timeout)
        
        try:
            while not self._event_server_dead.is_set():
                try:
                    detector_client.get_server_version()
                    time.sleep(check_timeout)
                except Exception as e:
                    self.logger.error(f'CARLA server is DEAD, detected by detector thread: {type(e).__name__}')
                    self._event_server_dead.set()
                    break
        finally:
            del detector_client
            self.logger.debug('Thread dead detector stopped')

    def _thread_func_restarter(self):
        """自动重启线程"""
        self.logger.debug('Thread restarter started waiting for server dead event')
        while True:
            self._event_server_dead.wait()
            if not self._event_manual_restart.is_set():
                self.logger.warning('Server dead event received, auto-restarting server')
                self.server_restart()
            else:
                self.logger.debug('Manual restart in progress, waiting...')
                while self._event_manual_restart.is_set():
                    time.sleep(0.5)

    @classmethod
    def from_config(cls, config: Config) -> Self:
        return cls(
            host=config.get("context/server/host"),
            port=config.get("context/server/port"),
            timeout=config.get("context/server/timeout"),
            exe_path=config.get("context/server/exe_path"),
            use_external_server=config.get("context/server/use_external_server", default=False),
            restart_on_failure=config.get("context/server/restart_on_failure", default=False),
            sync_mode_fps=config.get("context/server/sync_mode_fps", default=20),
            gpus=config.get("context/server/gpus", default=[0]),
            server_start_wait_time=config.get("context/server/server_start_wait_time", default=5),
            server_start_timeout=config.get("context/server/server_start_timeout", default=10),
        )