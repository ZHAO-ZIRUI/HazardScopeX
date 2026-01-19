import os
import signal
import time
from typing_extensions import Self
from typing import TYPE_CHECKING
from multiprocessing import Process

from shared.io import AbstractIOAdapter
from shared.data import TimestampSource, BaseData, Clock
from shared.utils import Logging, IdGenerator
from shared.io import SharedMemoryAdapter

if TYPE_CHECKING:
    from shared.simulator import CarlaSensor


class ROS2PublishAdapter(AbstractIOAdapter):
    """
    ROS2 适配器, 用于将仿真器的数据转换为 ROS2 数据

    高性能适配器将使用共享内存和多进程的方式来实现 ROS2 信息的发布, 以避免因 Python GIL 锁导致的性能瓶颈
    """

    DEFAULT_ROS_NODE_NAME = "HarzedScopeROS2Node"

    def __init__(
        self,
        shm_adapter: SharedMemoryAdapter,
        ros_message_type: type,
        ros_topic_name: str, 
        ros_node_name: str = DEFAULT_ROS_NODE_NAME,
        ros_qos: int = 10, 
        ros_frame_id: str = 'world',
        timestamp_source: TimestampSource = TimestampSource.OS,
    ):
        super().__init__()
        self.logger = Logging().get_logger('IOManager')

        self._shm_adapter = shm_adapter
        self._shm_topic = shm_adapter.topic
        self._ros_topic_name = ros_topic_name
        self._ros_node_name = self._resolve_ros_node_name(ros_node_name)
        self._ros_qos = ros_qos
        self._ros_frame_id = ros_frame_id
        self._timestamp_source = timestamp_source

        self._ros_message_type = ros_message_type
        self._ros_node = None
        self._ros_publisher = None

        self._data_type: BaseData | None = None
        self._data_cache = None

        self._worker_process: None | Process = None
        self._sensor_type: str | None = None

    def bind_sensor(self, sensor: 'CarlaSensor') -> Self:
        # Bind SHM, 令其开始工作
        self._shm_adapter.bind_sensor_output(sensor)

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

        # 启动 Worker
        self.start_worker()
        
        return self

    def bind_clock_output(self, clock: Clock) -> Self:
        return self

    def start_worker(self) -> Self:
        """启动 Worker 进程"""
        worker_args = (
            self._shm_topic,
            self._ros_topic_name,
            self._ros_node_name,
            self._ros_qos,
            self._ros_frame_id,
            self._ros_message_type,
            self._timestamp_source,
            self._sensor_type,
        )
        
        self._worker_process = Process(
            target=ROS2PublishAdapter._worker_process,
            args=worker_args,
            daemon=True
        )
        self._worker_process.start()
        
        # 等待进程启动并检查状态
        time.sleep(0.1)
        
        if self._worker_process.is_alive():
            self.logger.info(f"Started worker process for '{self._ros_topic_name}' (PID: {self._worker_process.pid})")
        else:
            self.logger.error(f"Failed to start worker process for '{self._ros_topic_name}'")
            if self._worker_process.exitcode is not None:
                self.logger.error(f"Worker exit code: {self._worker_process.exitcode}")
        
        return self

    def stop_worker(self) -> Self:
        """停止 Worker 进程"""
        if self._worker_process is not None:
            if self._worker_process.is_alive():
                pid = self._worker_process.pid
                self.logger.debug(f"Stopping worker process for '/{self._ros_topic_name}' (PID: {pid})")
                try:
                    os.kill(pid, signal.SIGINT)
                except ProcessLookupError:
                    pass
                self._worker_process.join(timeout=1.0)
                if self._worker_process.is_alive():
                    self._worker_process.terminate()
                    self._worker_process.join(timeout=1.0)
                if self._worker_process.is_alive():
                    self.logger.warning(f"Worker process for '/{self._ros_topic_name}' did not terminate in time, forcing shutdown")
                    self._worker_process.kill()
                    self._worker_process.join()
            try:
                self._worker_process.close()
            except AttributeError:
                pass
            finally:
                self._worker_process = None
        return self
    
    @staticmethod
    def _worker_process(
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
        logger.debug(f"Starting worker for shm to ros2: '{shm_topic}' -> '/{ros_topic_name}'")

        # 连接到共享内存
        try:
            shm = SharedMemory(name=shm_topic)
            logger.debug(f"Connected to shared memory '{shm_topic}'")
        except FileNotFoundError:
            logger.error(f"Shared memory '{shm_topic}' not found")
            return

        try:
            if not rclpy.ok():
                rclpy.init()
            
            ros_node = rclpy.create_node(ros_node_name, enable_rosout=False)
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
                                if rclpy.ok():
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
                if rclpy.ok():
                    rclpy.shutdown()
        finally:
            # 关闭共享内存连接
            try:
                shm.close()
            except Exception as e:
                logger.debug(f"Error closing shared memory: {e}")

        logger.debug(f"Worker for shm to ros2: '{shm_topic}' -> '{ros_topic_name}' stopped")

    def _resolve_ros_node_name(self, name: str) -> str:
        """解析 ROS2 节点名称, 如果名称未指定或为空, 则生成一个默认名称, 其他情况则直接用户输入
        
        Args:
            name (str): ROS2 节点名称
        
        Returns:
            str: ROS2 节点名称
        """
        if name is None or name == '' or name == self.DEFAULT_ROS_NODE_NAME:
            id_gen = IdGenerator(header=self.DEFAULT_ROS_NODE_NAME)
            return next(id_gen)
        return name
