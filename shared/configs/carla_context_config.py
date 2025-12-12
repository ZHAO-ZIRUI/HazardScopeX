from dataclasses import dataclass, field

from shared.configs import AbstractConfig


@dataclass
class CarlaContextConfig(AbstractConfig):
    """
    CarlaContext 配置
    """
    # 启动时配置
    server_host: str = field(default='127.0.0.1', metadata={'route': 'context/server/host'})
    server_port: int = field(default=2000, metadata={'route': 'context/server/port'})

    server_self_managed_enabled: bool = field(default=False, metadata={'route': 'context/server/self_managed/enabled'})
    server_self_managed_exe_path: str = field(default='', metadata={'route': 'context/server/self_managed/exe_path'})

    server_multi_gpu_enabled: bool = field(default=False, metadata={'route': 'context/server/multi_gpu/enabled'})
    server_multi_gpu_ids: list[int] = field(default_factory=lambda: [0], metadata={'route': 'context/server/multi_gpu/gpu_ids'})
    server_multi_gpu_port_offset: int = field(default=2, metadata={'route': 'context/server/multi_gpu/port_offset'})

    server_bringup_init_wait_seconds: float = field(default=5.0, metadata={'route': 'context/server/self_managed/bringup_init_wait_seconds'})
    server_bringup_timeout_seconds: float = field(default=10.0, metadata={'route': 'context/server/self_managed/bringup_timeout_seconds'})
    server_bringup_after_kill_wait_seconds: float = field(default=2.0, metadata={'route': 'context/server/self_managed/bringup_after_kill_wait_seconds'})

    # 运行时配置
    runtime_sync_mode_fps: float = field(default=20.0, metadata={'route': 'context/server/runtime/sync_mode_fps'})
    runtime_timeout_seconds: float = field(default=10.0, metadata={'route': 'context/server/runtime/timeout_seconds'})
    runtime_heavy_operation_timeout_seconds: float = field(default=60.0, metadata={'route': 'context/server/runtime/heavy_operation_timeout_seconds'})
    runtime_blocker_timeout_seconds: float = field(default=1.0, metadata={'route': 'context/server/runtime/blocker_timeout_seconds'})