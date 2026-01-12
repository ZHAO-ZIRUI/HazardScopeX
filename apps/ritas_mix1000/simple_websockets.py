# ----------------------------------------------------
# 输出图像和风险评估指标结果通过 WebSocket 广播
# ----------------------------------------------------

import asyncio
import websockets
import json
import base64
import cv2

from shared.data.image import Image
from shared.data.simulator_output import SimulatorOutput
from shared.scenarios.evaluator import SimpleRiskEvaluator
from shared.scenarios.factor import Factor
from shared.simulator import *
from shared.utils import Logging
from shared.configs import ConfigManager, ExternalConfigReader
from shared.prefabs import PlayerVehicle
from shared.scenarios import Injector

from factors import *
from pathlib import Path


# ----------------------------------------------------
# 1. 配置和常量
# ----------------------------------------------------
# 场景配置
MAP_NAME = 'Town10HD' # 'Town03

# 俯视图摄像头配置
IMG_WIDTH = 400
IMG_HEIGHT = 400
CAMERA_Z = 15.0 # 摄像头高度，俯视
CAMERA_FOV = 90

# 网络服务配置
WEBSOCKET_PORT = 8001

# ----------------------------------------------------
# 2. 图像处理和 Base64 编码
# ----------------------------------------------------
# 全局变量用于存储最新的图像数据
latest_bev_image_base64 = None

# ----------------------------------------------------
# 4. WebSocket 服务器和广播
# ----------------------------------------------------
connections = set()

async def register(websocket: websockets.ServerConnection):
    """
    客户端注册到服务端
    """
    connections.add(websocket)
    try:
        # 保持连接开放，直到客户端断开
        await websocket.wait_closed()
    finally:
        # 移除断开的连接
        connections.remove(websocket)


async def broadcast_data(data):
    """
    服务端广播数据
    """
    if connections:
        json_data = json.dumps(data)
        # 使用 asyncio.gather 并行发送，以防某个客户端阻塞
        await asyncio.gather(*[ws.send(json_data) for ws in connections], return_exceptions=True)
        # logger.debug(f"广播帧 {data['time_s']} 到 {len(connections)} 个客户端")


# ----------------------------------------------------
# 5. CARLA 配置与主循环 (集成用户逻辑)
# ----------------------------------------------------

async def carla_tick_loop(configReader: ExternalConfigReader, logger):
    """
    同步 CARLA 仿真主循环，负责推进仿真、路径同步和数据广播。
    """
    global latest_bev_image_base64

    def carla_image_callback(image: SimulatorOutput):
        """
        接受carla传输图像并处理
        """

        if image is None or not isinstance(image, Image):
            logger.error("收到的图像数据无效")
            return
        global latest_bev_image_base64
        try:
            raw = image.raw
            # 2. 编码为 JPEG 格式的字节流
            is_success, buffer = cv2.imencode(".jpg", raw, [cv2.IMWRITE_JPEG_QUALITY, 70]) # 降低质量以提高传输速度
            if not is_success:
                logger.error("JPEG 编码失败")
                latest_bev_image_base64 = None
                return
            
            # 3. 转换为 Base64 字符串
            latest_bev_image_base64 = base64.b64encode(buffer).decode('utf-8') # type: ignore
            
        except Exception as e:
            logger.error(f"处理图像时发生错误: {e}")
            latest_bev_image_base64 = None

    await asyncio.sleep(1)  # 等待系统稳定

    with CarlaContext(configReader) as context:
        context.change_map(MAP_NAME)

        vehicle = PlayerVehicle(context, context.spawn_points[0])
        vehicle.cam_game.hook_sensor_data_ready.append(carla_image_callback)

        context.actors.spawn_all()
        context.actors.wait_stable(vehicle)

        evaluator = SimpleRiskEvaluator(context)
        evaluator.bind_evaluate_actor('hero', vehicle)

        # 绑定传感器输出到内存
        # context.io.create_shm(topic='cam_game').bind_sensor_output(vehicle.cam_game)

        f1 = FactorCaseVehicleFollow(context, vehicle)

        factors = [f1]

        with Injector(context, *factors) as injector:
            # 注入循环
            while any(factor.stage != Factor.FactorStage.COMPLETED for factor in factors):
                try:
                    evaluator.evaluate()
                    
                    if latest_bev_image_base64:
                        # 准备 JSON 数据包
                        data_package = evaluator.dump_data_package()
                        data_package['bev_image_base64'] = latest_bev_image_base64    
                        # 广播给所有连接的客户端
                        await broadcast_data(data_package)
                        logger.debug(f"广播帧 {data_package['frame_id']} 到 {len(connections)} 个客户端")

                    await asyncio.to_thread(context.wait_ticks, 1)
                    
                    # context.wait_ticks(1, no_log=True, raise_interrupted=True)
                except KeyboardInterrupt:
                    logger.warning(f'Spin until finished interrupted by user')
                    raise SystemExit(441)

            logger.info(f'All {len(factors)} factors finished')
            

async def main():
    import traceback
    try:
        # 基础组件初始化
        configReader = ExternalConfigReader(dict()).load(Path("config.yaml"))
        config = ConfigManager().load(configReader)    # 加载配置到配置管理器
        print("config:",config.context," ",config.actor_manager," ",config.io_manager)
        logger = Logging.load(configReader).get_logger('Main') # 设置日志记录器

        server_task = websockets.serve(register, "0.0.0.0", WEBSOCKET_PORT)
        loop_task = asyncio.create_task(carla_tick_loop(configReader, logger))
        
        # 同时运行
        await server_task
        await loop_task
        
    except Exception as e:
        # 这里能捕获到 carla_tick_loop 抛出的任何异常
        logger.error("捕获到主程序崩溃:")
        logger.error(traceback.format_exc())
    finally:
        logger.info("主程序正在清理并退出...")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务器已手动关闭。")
    except Exception as e:
        print(f"程序退出错误: {e}")