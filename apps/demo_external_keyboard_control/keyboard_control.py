import textwrap
import time
import keyboard
import argparse
import logging
import yaml
from rich.logging import RichHandler
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from multiprocessing.shared_memory import SharedMemory

from core.data import VehicleDirectControl
from core.utils import RouteConfig


CLI_FPS = 30
CLI_PANEL_OFFSET =4
CLI_PROGRESS_DATAVIEWER_WIDTH = 6

CTRL_THROTTLE_RATE = 0.02   # 油门增加速率
CTRL_BRAKE_RATE = 0.02       # 刹车增加速率
CTRL_THROTTLE_RETURN_RATE = 0.005  # 油门回零速率
CTRL_BRAKE_RETURN_RATE = 0.005     # 刹车回零速率
CTRL_STEERING_RATE = 0.01    # 方向盘转向速率
CTRL_STEERING_RETURN_RATE = 0.005  # 方向盘回中速率
CTRL_STEERING_QUICK_RETURN_RATE = 0.02  # 快速回中速率


def handle_input(control: VehicleDirectControl) -> VehicleDirectControl:
    is_steering = False
    # 上一帧控制指令拆包
    throttle = control.throttle
    brake = control.brake
    steering = control.steering
    reverse = control.reverse

    # 油门控制
    if keyboard.is_pressed('w') or keyboard.is_pressed('up'):
        if brake > 0:
            brake = 0  
        throttle = min(1.0, throttle + CTRL_THROTTLE_RATE)
    else:
        if throttle > 0:
            throttle = max(0.0, throttle - CTRL_THROTTLE_RETURN_RATE)
    
    # 刹车控制 (S 或 ↓)
    if keyboard.is_pressed('s') or keyboard.is_pressed('down'):
        if throttle > 0:
            throttle = 0
        brake = min(1.0, brake + CTRL_BRAKE_RATE)
    else:
        if brake > 0:
            brake = max(0.0, brake - CTRL_BRAKE_RETURN_RATE)
    
    # 左转控制 (A 或 ←)
    if keyboard.is_pressed('a') or keyboard.is_pressed('left'):
        is_steering = True
        if steering > 0:
            steering = max(-1.0, steering - CTRL_STEERING_QUICK_RETURN_RATE)
        else:
            steering = max(-1.0, steering - CTRL_STEERING_RATE)

    # 右转控制 (D 或 →)
    if keyboard.is_pressed('d') or keyboard.is_pressed('right'):
        is_steering = True
        if steering < 0:
            steering = min(1.0, steering + CTRL_STEERING_QUICK_RETURN_RATE)
        else:
            steering = min(1.0, steering + CTRL_STEERING_RATE)

    # 方向盘自动回中
    if not is_steering:
        if steering > 0:
            steering = max(0.0, steering - CTRL_STEERING_RETURN_RATE)
        elif steering < 0:
            steering = min(0.0, steering + CTRL_STEERING_RETURN_RATE)

    # 倒挡控制
    if keyboard.is_pressed('+'):
        reverse = False
    elif keyboard.is_pressed('-'):
        reverse = True

    # 油门刹车快速归中
    if keyboard.is_pressed('space'):
        throttle = 0
        brake = 0

    # 方向盘快速归中
    if keyboard.is_pressed('space'):
        steering = 0

    return VehicleDirectControl(
        throttle=throttle,
        steering=steering,
        brake=brake,
        reverse=reverse
    )

def update_panel_help() -> Panel:
    content = f"""
    EXTERNAL KEYBOARD VEHICLE CONTROL
    
    CONTROLS:
     - W/↑:    Accelerator Pedal
     - S/↓:    Brake Padel
     - A/←:    Turn Left
     - D/→:    Turn Right
     - +:      Forward Gear
     - -:      Reverse Gear
     - SPACE:  Reset Throttle and Brake
     
     - Ctrl-C: Exit Program
    """
    content = textwrap.dedent(content).strip('\n')
    return Panel(content, title="HELPS", border_style="WHITE")

def update_panel_control(
        width: int,
        control: VehicleDirectControl,
) -> Panel:
    separator = ": "
    # 数据 - 渲染方法 映射
    data ={
        "Accelerator": (draw_progress_linear, control.throttle),
        "Brake": (draw_progress_linear, control.brake),
        "Steering": (draw_progress_bipolar, control.steering),
        "Reverse": (draw_progress_boolean, control.reverse),
    }

    # 宽度计算
    width = width - CLI_PANEL_OFFSET
    max_header_width = max([len(header) for header in data.keys()])
    bar_width = width - max_header_width - len(separator)

    # 内容绘制
    content = ""
    for header, func in data.items():
        content += header.upper().ljust(max_header_width, ' ')
        content += separator
        content += func[0](func[1], bar_width)
        content += '\n'*2
    content = textwrap.dedent(content).strip('\n')
    return Panel(content, title="CONTROLS", border_style="BLUE")

def draw_progress_linear(value: float, width: int = 20) -> str:
    width = _draw_progress_confirm_width(width, CLI_PROGRESS_DATAVIEWER_WIDTH)

    # 如果 value 不在可靠范围内, 显示错误的 Bar
    if not isinstance(value, float | int) or value < 0 or value > 1:
        return f"[red]{'---%'.ljust(CLI_PROGRESS_DATAVIEWER_WIDTH, ' ')}{'░' * width}[/red]"

    # 正常处理
    filled = int(value * width)
    data_viewer = f"{int(value * 100):3d}%"
    content = ""
    content += data_viewer.ljust(CLI_PROGRESS_DATAVIEWER_WIDTH, ' ')
    content += f"{'█' * filled}{'░' * (width - filled)}"
    return content

def draw_progress_bipolar(value: float, width: int = 20) -> str:
    width = _draw_progress_confirm_width(width, CLI_PROGRESS_DATAVIEWER_WIDTH)

    # 如果 value 不在可靠范围内, 显示错误的 Bar
    if not isinstance(value, float | int) or value < -1 or value > 1:
        return f"[red]{'---%'.ljust(CLI_PROGRESS_DATAVIEWER_WIDTH, ' ')}{'░' * width}[/red]"

    # 进度条底纹
    center = width // 2
    bar = ['░'] * width
    bar[center] = '│'

    # 绘制实体
    if abs(value) > 0.01:
        if value > 0:
            fill_count = int(value * (width // 2))
            for i in range(center + 1, min(center + 1 + fill_count, width)):
                bar[i] = '█'
        else:
            fill_count = int(abs(value) * (width // 2))
            for i in range(max(0, center - fill_count), center):
                bar[i] = '█'

    data_viewer = f"{int(value * 100):3d}%"
    content = ""
    content += data_viewer.ljust(CLI_PROGRESS_DATAVIEWER_WIDTH, ' ')
    content += ''.join(bar)
    return content

def draw_progress_boolean(value: bool, width: int = 20) -> str:
    width = _draw_progress_confirm_width(width, CLI_PROGRESS_DATAVIEWER_WIDTH)

    if value:
        return (f"[bold green]{'TRUE'.ljust(CLI_PROGRESS_DATAVIEWER_WIDTH, ' ')}[/bold green]"
                f"[green]{'░'*width}[/green]")
    else:
        return (f"[bold red]{'FALSE'.ljust(CLI_PROGRESS_DATAVIEWER_WIDTH, ' ')}[/bold red]"
                f"[red]{'░'*width}[/red]")

def _draw_progress_confirm_width(max_width: int, reserve: int) -> int:
    width = max_width - reserve
    # 确保 width 是奇数
    if width % 2 == 0:
        width = width - 1
    return max(width, reserve + 3)  # 最小的进度条大小为 3


def main(vehicle_name: str):
    # 配置文件
    config: RouteConfig = RouteConfig(yaml.load(open("config.yaml", "r"), Loader=yaml.FullLoader))

    # 日志系统
    logging.basicConfig(
        level=config.get("logging/level", 20),
        format="[%(name)s] %(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_time=True, markup=True)]
    )
    logger = logging.getLogger("KeyboardControl")
    logger.info("Program started")

    # 等待共享内存完成初始化
    shm_direct_control = None
    while True:
        try:
            shm_direct_control = SharedMemory(name=f"{vehicle_name}_DIRECT_CONTROL")
            break
        except FileNotFoundError:
            time.sleep(1)
            logger.warning(f"Trying connect to {vehicle_name}_DIRECT_CONTROL, retrying ...")
            continue

    # CLI 布局
    layout = Layout()
    layout.split_row(
        Layout(name="HELP", ratio=1),
        Layout(name="MAIN", ratio=2),
    )
    layout["MAIN"].split_column(
        Layout(name="CONTROL", ratio=1),
        Layout(name="STATUS", ratio=1),
    )

    # 宽度初始值
    is_first_frame = True
    width_panel_control = 20

    # 外发数据
    control = VehicleDirectControl()

    # 主循环
    try:
        with Live(layout, refresh_per_second=CLI_FPS, screen=True):
            while True:
                # 更新画面
                layout["HELP"].update(update_panel_help())
                layout["CONTROL"].update(update_panel_control(width_panel_control, control))

                # 首帧直接在 Layout 渲染后跳过, 确保宽度能够基于首帧正确获取
                if is_first_frame:
                    is_first_frame = False
                    time.sleep(1/CLI_FPS)
                    continue
                    
                # 处理输入并组装为控制指令
                control = handle_input(control)
                control.serialize_to_shm(shm_direct_control)

                # 更新宽度
                width_panel_control = layout.map[layout["CONTROL"]].region.width

                # 结束循环
                time.sleep(1/CLI_FPS)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name", type=str)
    args = parser.parse_args()
    main(args.name)
