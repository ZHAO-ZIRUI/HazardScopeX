import carla
import psutil
import time
import platform
from logging import getLogger
from typing import List, Callable
from subprocess import Popen, DEVNULL
from threading import Thread


class CarlaContext(object):
    """
    CARLA 仿真器的上下文, 管理仿真的生命周期和行为

    该类提供两种模式, 以是否向 cmd 传递具体启动命令分类:

    - 主动模式 (launch mode): Daemon 管理 CARLA Server 的生命周期
    - 被动模式 (passive mode): 由外部程序或用户手动管理 CARLA Server 的生命周期
    """

    def __init__(
            self,
            cmd: List[str] | str = None,
            host: str = 'localhost',
            port: int = 2000,
            timeout: int = 30,
            fixed_delta_seconds: int = 0.1,
    ) -> None:
        """
        :param cmd: CARLA Server 的启动命令, ``None`` 时进入被动模式 (Passive Mode)
        :param host: CARLA Server 的 FQDN
        :param port: CARLA Server 的端口号
        :param timeout: CARLA Client 连接 Server 的超时时间, 单位: 秒
        :param fixed_delta_seconds: CARLA Server 进入同步模式时的固定时间步, 单位: 秒
        """
        # 日志
        self.logger = getLogger(self.__class__.__name__)

        # 验证
        if fixed_delta_seconds <= 0:
            raise ValueError('fixed_delta_seconds must be a positive number, '
                             'even you will not use sync mode forever.')

        # 实参
        self._cmd = cmd
        self._server: Popen | None = None
        self._client: carla.Client | None = None
        self._host = host
        self._port = port
        self._timeout = timeout
        self._fixed_delta_seconds = fixed_delta_seconds

        # 钩子
        self._hook_before_server_exit: List[Callable] = list()
        self._hook_after_server_exit: List[Callable] = list()
        self._hook_after_server_unexpected_exit: List[Callable] = list()

        # 监听线程
        self._thread_trigger_flag = True
        self._thread_trigger: Thread | None = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._kill_server()

    @property
    def world(self) -> carla.World:
        return self._client.get_world()

    @property
    def traffic_manager(self) -> carla.TrafficManager:
        return self._client.get_trafficmanager()

    @property
    def is_sync_mode(self) -> bool:
        """
        :return: CARLA 服务端是否处于同步模式(synchronous_mode)
        """
        return self.world.get_settings().synchronous_mode

    @property
    def sync_mode_delta_seconds(self) -> float:
        """
        :return: CARLA 服务端同步模式的间隔秒, 如果不在同步模式则返回 0
        """
        if self.is_sync_mode:
            return self.world.get_settings().fixed_delta_seconds
        return 0.0

    def launch_server(self, force = True) -> None:
        """
        启动仿真器进程
        :param force: 是否在启动前强制退出系统中的残留 CARLA 进程, 默认为 ``True``
        :raises AttributeError: 在被动模式下尝试启动仿真器
        :raises RuntimeError: 尝试重复启动服务端
        :raises TimeoutError: 尝试启动服务端超时
        """
        if self._cmd is None:
            msg = "Trying to launch CARLA in passive mode. Set cmd to enable launch mode."
            self.logger.warning(msg)
            raise AttributeError(msg)
        if isinstance(self._cmd, str):
            self._cmd = [self._cmd]
        if self._server:
            msg = "CARLA server already running."
            self.logger.warning(msg)
            raise RuntimeError(msg)

        # 执行强制关闭
        if force:
            self._kill_server(force=True)

        self._server = Popen(self._cmd, shell=True)
        self.logger.debug("CARLA server begin to launch.")
        self.logger.debug("Waiting 10 seconds for CARLA server ready ... ")
        time.sleep(10)

        # 建立一个临时 Client 等待 Server 可用
        temp_client = carla.Client(self._host, self._port)
        temp_client.set_timeout(1)
        timer = 0
        while timer < self._timeout:
            try:
                temp_client.get_server_version()
                break
            except RuntimeError:
                timer += 1
                self.logger.debug(f'Waiting for CARLA server ready ... ({timer}/{self._timeout:.0f})')
        else:
            # 达到最大超时时间
            msg = f"CARLA server still not ready in {self._timeout:.0f} seconds."
            self.logger.error(msg)
            raise TimeoutError(msg)

        # 设置主客户端
        self._client = carla.Client(self._host, self._port)
        self._client.set_timeout(self._timeout)

        # 完成启动
        self._thread_trigger_flag = True
        self._thread_trigger = Thread(target=self._thread_trigger_func, daemon=True)
        self._thread_trigger.start()
        self.logger.debug("CARLA server launched and ready")

    def terminate_server(self) -> None:
        """
        结束仿真器进程
        :raises AttributeError: 在被动模式下尝试关闭仿真器
        """
        if self._cmd is None:
            msg = "Trying to terminate CARLA in passive mode. Set cmd to enable launch mode."
            self.logger.warning(msg)
            raise AttributeError(msg)
        if self._server is None:
            self.logger.warning("CARLA server already stopped.")
            return

        # 退出触发线程
        self._thread_trigger_flag = False
        if self._thread_trigger:
            self._thread_trigger.join()

        # 执行钩子: before_server_exit
        for func in self._hook_before_server_exit:
            func()

        # 退出
        self._kill_server()

        # 执行钩子: after_server_exit
        for func in self._hook_after_server_exit:
            func()

        self.logger.debug(f"CARLA Server stopped.")

    def enter_sync_mode(self, *, fixed_delta_seconds: float | None  = None) -> None:
        """
        进入同步模式
        :param fixed_delta_seconds: Tick 之间的仿真时间步, 此参数覆写实例化时提供的参数
        """
        if self.is_sync_mode:
            self.logger.warning("Attempted to enter sync mode but it is already active.")
            return

        setting = self.world.get_settings()
        setting.synchronous_mode = True
        setting.fixed_delta_seconds = fixed_delta_seconds if fixed_delta_seconds else self._fixed_delta_seconds
        self.world.apply_settings(setting)
        self.world.tick()   # 执行一次 Tick 避免卡死
        self.logger.debug("Enter sync mode")

    def exit_sync_mode(self) -> None:
        """离开同步模式"""
        if not self.is_sync_mode:
            self.logger.warning("Attempted to exit sync mode but it is already active.")
            return
        setting = self.world.get_settings()
        setting.synchronous_mode = False
        setting.fixed_delta_seconds = 0
        self.world.apply_settings(setting)
        self.world.tick()   # 执行一次 Tick 避免卡死
        self.logger.debug("Exit sync mode")

    def tick(self):
        if not self.is_sync_mode:
            self.logger.warning("Operation tick() can only called under sync mode.")
        self.world.tick()

    def is_connected(self, *, timeout: float | None = None) -> bool:
        """
        :param timeout: 覆盖类设置的 timeout 值, 用于快速连接检查. 取 0 时使用 2倍的 ``fixed_delta_seconds``
        :return: CARLA 客户端与服务器之间的通信是否正常
        """
        try:
            # 设置 timeout 覆盖
            if timeout is not None:
                temp_timeout = timeout if timeout > 0 else self._fixed_delta_seconds * 2
                self._client.set_timeout(temp_timeout)

            # 进行连接检查
            self._client.get_server_version()

            # 恢复原有 timeout 设置
            if timeout is not None:
                self._client.set_timeout(self._timeout)

            return True
        except RuntimeError as e:
            # 无法连接服务器时报 RuntimeError
            self.logger.error(e)
            return False

    def _thread_trigger_func(self) -> None:
        """服务端的事件触发线程"""
        self.logger.debug("Event trigger thread started.")

        while self._thread_trigger_flag:
            time.sleep(0.5 * self._fixed_delta_seconds)

            # 当 服务端应该处于运行状态下 但 测试连接失败时, 认为发生意外退出
            if self._server is not None and not self.is_connected(timeout=0.5):
                self.logger.warning("CARLA server unexpected stop.")
                self._thread_trigger_flag = False

                # 执行钩子: after_server_unexpected_exit
                for func in self._hook_after_server_unexpected_exit:
                    func()

    def _kill_server(self, force = False) -> None:
        """
        立刻杀死所有的 CARLA Server 进程
        :param force: 是否使用系统级命令强行杀死服务进程, 使用改方法时会绕过对服务状态的检查. 在 Windows 下使用 ``taskkill``,
        在 ``Linux`` 下使用 ``pkill``
        """
        if force and platform.system() == 'Windows':
            cmd_base = ['taskkill', '/F', '/T', '/IM']
            cmd_kill_main = [*cmd_base, 'CarlaUE4.exe']
            cmd_kill_shipping = [*cmd_base, 'CarlaUE4-Win64-Shipping.exe']
            Popen(cmd_kill_main, shell=True, stdout=DEVNULL, stderr=DEVNULL).wait()
            Popen(cmd_kill_shipping, shell=True, stdout=DEVNULL, stderr=DEVNULL).wait()
            return
        if force and platform.system() == 'Linux':
            cmd_base = ['pkill', '-f']
            cmd_kill_carla = [*cmd_base, 'CarlaUE4']
            cmd_kill_shipping = [*cmd_base, 'CarlaUE4-Linux-Shipping']
            Popen(cmd_kill_carla, shell=True, stdout=DEVNULL, stderr=DEVNULL).wait()
            Popen(cmd_kill_shipping, shell=True, stdout=DEVNULL, stderr=DEVNULL).wait()
            return

        if self._server is None:
            return

        # 尝试找到启动的父进程, 如果服务端意外退出, 会出现 NoSuchProcess
        try:
            parent = psutil.Process(self._server.pid)
        except psutil.NoSuchProcess:
            return

        # 杀死来自 UE 启动后的全部子进程
        parent.kill()
        for child in parent.children(recursive=True):
            child.kill()

        # 等待杀死完成并进行后处理
        time.sleep(1)
        self._server = None

    @property
    def hook_before_server_exit(self) -> List[Callable]:
        return self._hook_before_server_exit

    @property
    def hook_after_server_exit(self) -> List[Callable]:
        return self._hook_after_server_exit

    @property
    def hook_after_server_unexpected_exit(self) -> List[Callable]:
        return self._hook_after_server_unexpected_exit