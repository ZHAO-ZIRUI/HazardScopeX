import carla
import logging
import yaml
import time
from rich.logging import RichHandler

from core.simulator import *
from core.utils import RouteConfig
from core.data import Image, PointCloud, VehicleDirectControl


def main():
    # 配置文件
    config: RouteConfig = RouteConfig(yaml.load(open("config.yaml", "r"), Loader=yaml.FullLoader))

    # 日志系统
    logging.basicConfig(
        level=config.get("logging/level", 20),
        format="[%(name)s] %(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_time=True, markup=True)]
    )
    logger = logging.getLogger("Main")
    logger.info("Program started")

    # CARLA 服务端初始化
    context = CarlaContext(
        config.get("context/carla_exe_dir"),
        fixed_delta_seconds=config.get("context/fixed_delta_seconds", 0.05),
        render_offscreen=config.get("context/carla_render_offscreen", False)
    )
    context.launch_server()

    # CARLA 对象定义
    tf_vehicle = context.get_spawn_point(0)
    tf_camera_game = carla.Transform(carla.Location(x=-5.5, z=2.8),carla.Rotation(pitch=-15))
    tf_camera_front = carla.Transform(carla.Location(x=1.6, z=1.7))
    tf_lidar = carla.Transform(carla.Location(x=0.0, z=2.4))

    camera_game = CarlaSensor(context, CarlaBlueprints.SENSOR_CAMERA_RGB, tf=tf_camera_game, name="CAM_GAME")
    camera_front = CarlaSensor(context, CarlaBlueprints.SENSOR_CAMERA_RGB, tf=tf_camera_front, name="CAM_FRONT")
    lidar = CarlaSensor(context, CarlaBlueprints.SENSOR_LIDAR_RAY_CAST, tf=tf_lidar, name="LIDAR")

    vehicle = CarlaVehicle(context, CarlaBlueprints.VEHICLE_TESLA_MODEL3, tf=tf_vehicle, name="EGO")
    vehicle.add_sensor(camera_game)
    vehicle.add_sensor(camera_front)
    vehicle.add_sensor(lidar)

    # CARLA 对象生成
    vehicle.spawn(z=3)
    CarlaActor.wait_all_actors_stable(context, vehicle)
    logger.info("Simulation scenario ready")

    # 外部通信
    shm_camera_game = context.create_shared_memory("CAM_GAME", 10)
    shm_lidar = context.create_shared_memory("LIDAR", 10)
    shm_direct_control = context.create_shared_memory(f"{vehicle.name}_DIRECT_CONTROL")

    # 注册传感器事件
    def send_image_data(image: Image):
        image.serialize_to_shm(shm_camera_game)

    def send_lidar_data(point_cloud: PointCloud):
        point_cloud.serialize_to_shm(shm_lidar)

    camera_game.hook_after_senser_data_ready.append(send_image_data)
    lidar.hook_after_senser_data_ready.append(send_lidar_data)

    # 主仿真循环
    context.enter_sync_mode()

    try:
        while True:
            time.sleep(context.sync_mode_delta_seconds)

            # 获取并应用外部控制指令
            direct_control = VehicleDirectControl.try_deserialize_from_shm(shm_direct_control, VehicleDirectControl())
            vehicle.apply_carla_direct_control(direct_control, silence=True)

            context.tick()
    except KeyboardInterrupt:
        logger.info("Program interrupted")
    finally:
        context.terminate_server()


if __name__ == '__main__':
    main()