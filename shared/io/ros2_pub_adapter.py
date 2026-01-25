from re import T
import carla
import os
import signal
import time
from multiprocessing import Process, get_context
from typing import TYPE_CHECKING, TypeVar, Generic, Callable
from typing_extensions import Self

from shared.utils import Logging
from shared.define import TimestampSource
from shared.data import *
from shared.simulator import CarlaSensor
from shared.io import SharedMemoryAdapter

MsgT = TypeVar('MsgT')

if TYPE_CHECKING:
    from shared.simulator import CarlaContext
    from rclpy.publisher import Publisher

class ROS2PubAdapter(Generic[MsgT]):
    
    def __init__(
        self,
        context: 'CarlaContext',
        ros2_pub: 'Publisher',
        topic: str,
        message_type: type[MsgT],
        frame_id: str,
        timestamp_source: TimestampSource,
        qos: int = 10,
    ):
        self._logger = Logging().get_logger('IOManager')
        self._context = context
        self._topic = topic
        self._frame_id = frame_id
        self._message_type = message_type
        self._timestamp_source = timestamp_source
        self._ros2_pub = ros2_pub
        self._qos = qos

        self._is_hook_registered_clock = False
        self._is_hook_registered_other = False
        self._is_sensor_worker_running = False

        # SENSOR ONLY
        self._sensor_shm_adapter: None | SharedMemoryAdapter = None
        self._sensor_type: str | None = None
        self._sensor_id_local: str | None = None
        self._sensor_worker_process: None | Process = None

        self._callback = None

    def destroy(self) -> Self:
        if self._is_hook_registered_clock:
            self._context.hook_befre_next_tick.remove(self._hookfunc_pub_clock_on_tick)
            self._is_hook_registered_clock = False
        if self._is_hook_registered_other:
            self._context.hook_befre_next_tick.remove(self._hookfunc_pub_other_on_tick)
            self._is_hook_registered_other = False
        if self._is_sensor_worker_running:
            self._stop_sensor_worker()
            self._is_sensor_worker_running = False
        return self

    def bind_sensor(self, sensor: CarlaSensor) -> Self:
        self._ros2_pub = None

        self._sensor_id_local = sensor.id_local

        # 创建传感器的 SHM 适配器, 令其开始工作
        self._sensor_shm_adapter = self._context.io.create_shm('ros2_pub_adapter_' + sensor.id_local)
        self._sensor_shm_adapter.bind_sensor(sensor)

        # 确定传感器类型
        if sensor.bp.id.lower().startswith('sensor.camera.'):
            self._sensor_type = 'camera'
        elif sensor.bp.id.lower().startswith('sensor.lidar.'):
            self._sensor_type = 'lidar'
        elif sensor.bp.id.lower().startswith('sensor.other.gnss'):
            self._sensor_type = 'gnss'
        elif sensor.bp.id.lower().startswith('sensor.other.imu'):
            self._sensor_type = 'imu'
        else:
            raise ValueError(f"Unsupported sensor type: {sensor.bp.id}")

        # 启动传感器 Worker
        self._start_sensor_worker()
        return self

    def bind_clock(self) -> Self:
        self._context.hook_befre_next_tick.append(self._hookfunc_pub_clock_on_tick)
        self._is_hook_registered_clock = True
        return self

    def bind_other(self, callback: Callable[[], MsgT]) -> Self:
        self._callback = callback
        self._context.hook_befre_next_tick.append(self._hookfunc_pub_other_on_tick)
        self._is_hook_registered_other = True
        return self
        
    def _hookfunc_pub_clock_on_tick(self, _: carla.WorldSnapshot) -> None:
        import rclpy
        msg = self._context.clock.to_ros2(timestamp_source=self._timestamp_source)
        if rclpy.ok():
            self._ros2_pub.publish(msg)

    def _hookfunc_pub_other_on_tick(self, _: carla.WorldSnapshot) -> None:
        import rclpy
        msg = self._callback()
        if rclpy.ok():
            self._ros2_pub.publish(msg)

    def _start_sensor_worker(self) -> Self:
        """启动 Worker 进程"""
        node_name = self._context.io._config.ros2_node_name + '_' + self._sensor_id_local.lower()
        worker_args = (
            self._sensor_shm_adapter.topic,
            self._topic,
            node_name,
            self._qos,
            self._frame_id,
            self._message_type,
            self._timestamp_source,
            self._sensor_type,
        )
        
        mp_context = get_context('spawn')
        self._sensor_worker_process = mp_context.Process(
            target=ROS2PubAdapter._sensor_worker_process,
            args=worker_args,
            daemon=True
        )
        self._sensor_worker_process.start()
        self._is_sensor_worker_running = True

        # 等待进程启动并检查状态
        time.sleep(0.1)
        
        if self._sensor_worker_process.is_alive():
            self._logger.info(f"Started worker process for '{self._topic}' (PID: {self._sensor_worker_process.pid})")
        else:
            self._logger.error(f"Failed to start worker process for '{self._topic}'")
            if self._sensor_worker_process.exitcode is not None:
                self._logger.error(f"Worker exit code: {self._sensor_worker_process.exitcode}")
        
        return self

    def _stop_sensor_worker(self) -> Self:
        """停止 sensor_worker 进程"""
        if self._sensor_worker_process is not None:
            if self._sensor_worker_process.is_alive():
                pid = self._sensor_worker_process.pid
                self._logger.debug(f"Stopping sensor worker for '{self._topic}' (PID: {pid})")
                try:
                    os.kill(pid, signal.SIGINT)
                except ProcessLookupError:
                    pass
                self._sensor_worker_process.join(timeout=1.0)
                if self._sensor_worker_process.is_alive():
                    self._sensor_worker_process.terminate()
                    self._sensor_worker_process.join(timeout=1.0)
                if self._sensor_worker_process.is_alive():
                    self._logger.warning(f"Sensor worker for '{self._topic}' did not terminate in time, forcing shutdown")
                    self._sensor_worker_process.kill()
                    self._sensor_worker_process.join()
            try:
                self._sensor_worker_process.close()
            except AttributeError:
                pass
            finally:
                self._sensor_worker_process = None
        return self

    @staticmethod
    def _sensor_worker_process(
        shm_topic: str,
        ros_topic_name: str,
        ros_node_name: str,
        ros_qos: int,
        ros_frame_id: str,
        ros_message_type: type,
        timestamp_source: TimestampSource,
        sensor_type: str,
    ) -> None:
        """共享内存到 ROS2 的高性能适配器的工作进程函数, 用于在子进程中运行 ROS2 发布器

        Args:
            shm_topic (str): 共享内存的名称
            ros_topic_name (str): ROS2 的 topic 名称
            ros_node_name (str): ROS2 的节点名称
            ros_qos (int): ROS2 的 QoS
            ros_frame_id (str): ROS2 的 frame_id
            timestamp_source (TimestampSource): 时间戳来源
            sensor_type (str): 传感器类型
        """
        import rclpy
        from multiprocessing.shared_memory import SharedMemory
        from sensor_msgs.msg import Image, PointCloud2, NavSatFix, Imu
        from shared.data import Image as SharedImage, PointCloud as SharedPointCloud
        from shared.data import Gnss as SharedGnss, Imu as SharedImu
        
        logger = Logging().get_logger('IOManager')
        logger.debug(f"Starting worker for shm to ros2: '{shm_topic}' -> '{ros_topic_name}'")

        # 连接到共享内存
        try:
            shm = SharedMemory(name=shm_topic)
            logger.debug(f"Connected to shared memory '{shm_topic}'")
        except FileNotFoundError:
            logger.error(f"Shared memory '{shm_topic}' not found")
            return

        ros_context = None
        ros_node = None
        try:
            ros_context = rclpy.Context()
            rclpy.init(context=ros_context)
            
            ros_node = rclpy.create_node(ros_node_name, enable_rosout=False, context=ros_context)
            logger.debug(f"Created ROS2 node '{ros_node_name}'")
            
            # 根据传感器类型确定数据类和消息类型
            if sensor_type == 'camera':
                data_type = SharedImage
                ros_message_type = Image if ros_message_type is None else ros_message_type
            elif sensor_type == 'lidar':
                data_type = SharedPointCloud
                ros_message_type = PointCloud2 if ros_message_type is None else ros_message_type
            elif sensor_type == 'gnss':
                data_type = SharedGnss
                ros_message_type = NavSatFix if ros_message_type is None else ros_message_type
            elif sensor_type == 'imu':
                data_type = SharedImu
                ros_message_type = Imu if ros_message_type is None else ros_message_type
            else:
                raise ValueError(f"Unsupported sensor type: {sensor_type}")
            
            # 创建 Publisher
            ros_publisher = ros_node.create_publisher(ros_message_type, ros_topic_name, ros_qos)
            logger.debug(f"Created ROS2 publisher for '{ros_topic_name}'")

            # 主工作循环
            last_frame = None
            try:
                while True:
                    # 首先只读取帧号，避免反序列化大数据
                    current_frame = data_type.try_from_shm_frame_only(shm, default=None)

                    # 如果没有数据或帧号未变化，跳过
                    if current_frame is None:
                        time.sleep(0.01)
                        continue
                    
                    # 只有帧号变化时才处理
                    if last_frame is None or current_frame != last_frame:
                        data = data_type.try_from_shm(shm, default=None)
                        if data is not None:
                            if hasattr(data, 'sim_frame') and data.sim_frame == current_frame:
                                # 将数据转换为 ROS2 消息
                                ros2_data = data.to_ros2(frame_id=ros_frame_id, ros_message_type=ros_message_type, timestamp_source=timestamp_source)
                                if ros_context.ok():
                                    ros_publisher.publish(ros2_data)
                                else:
                                    break
                                last_frame = current_frame
                            else:
                                time.sleep(0.001)
                                continue
                    else:
                        time.sleep(0.01)
                        continue

            except KeyboardInterrupt:
                logger.info("Worker received interrupt signal")
            except Exception as e:
                logger.error(f"Worker error: {e}")
            finally:
                # 销毁 ROS2 资源
                if ros_node is not None:
                    ros_node.destroy_node()
                if ros_context is not None and ros_context.ok():
                    rclpy.shutdown(context=ros_context)
        finally:
            # 关闭共享内存连接
            try:
                shm.close()
            except Exception as e:
                logger.debug(f"Error closing shared memory: {e}")

        logger.debug(f"Sensor worker for shm to ros2: '{shm_topic}' -> '{ros_topic_name}' stopped")