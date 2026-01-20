import carla
import math
from typing import TYPE_CHECKING, Dict, Any
from typing_extensions import Unpack

from shared.data import TimestampSource
from shared.prefabs.nuscenes_vehicle import NuScenesVehicle
from shared.simulator import CarlaContext, CarlaTransform, CarlaBlueprints, CarlaSensor


if TYPE_CHECKING:
    from shared.simulator import CarlaContext
    from std_msgs.msg import Header
    # 引入 Autoware 消息类型, 可能无法被 IDE 正确识别
    # 需要在启动程序前先编译 Autoware 消息, 并完成 ROS 的 source 操作
    from autoware_vehicle_msgs.msg import VelocityReport, SteeringReport, GearReport, ControlModeReport
    from tier4_vehicle_msgs.msg import ActuationStatusStamped, ActuationStatus


class AutowareVehicle(NuScenesVehicle):

    GNSS_NAME = 'GNSS'
    GNSS_TF = CarlaTransform(x=0.0, y=0.0, z=0.0)

    IMU_NAME = 'IMU'
    IMU_TF = CarlaTransform(x=0.0, y=0.0, z=0.0)

    
    def __init__(
        self,
        context: 'CarlaContext',
        tf: CarlaTransform | carla.Transform,
        bp: carla.ActorBlueprint | str | CarlaBlueprints = CarlaBlueprints.VEHICLE_TESLA_MODEL3,
        name: str = 'NuScenesVehicle',
        **attributes: Unpack[Dict[str, Any]],
    ):
        super().__init__(context, tf, bp, name, **attributes)


    def __post_init__(self):
        super().__post_init__()
        self._gnss = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_OTHER_GNSS,
            name=self.name + '_' + self.GNSS_NAME,
            tf=self.GNSS_TF,
            parent=self,
        )
        self._imu = self._context.actors.create_sensor(
            bp=CarlaBlueprints.SENSOR_OTHER_IMU,
            name=self.name + '_' + self.IMU_NAME,
            tf=self.IMU_TF,
            parent=self,
        )

    @property
    def gnss(self) -> CarlaSensor:
        return self._gnss

    @property
    def imu(self) -> CarlaSensor:
        return self._imu

    def get_header_msg(self, frame_id: str = 'UNDEFINED', timestamp_source: TimestampSource = TimestampSource.OS) -> Header:
        from std_msgs.msg import Header
        return Header(
            stamp=self._context.clock.to_ros2_stamp(timestamp_source),
            frame_id=frame_id,
        )

    def get_velocity_report_msg(self, frame_id: str = 'UNDEFINED', timestamp_source: TimestampSource = TimestampSource.OS) -> 'VelocityReport':
        from autoware_vehicle_msgs.msg import VelocityReport
        return VelocityReport(
            header=self.get_header_msg(frame_id, timestamp_source),
            longitudinal_velocity=self.velocity_self.x,
            lateral_velocity=self.velocity_self.y,
            heading_rate=math.radians(self.angular_velocity.z),  # deg/s -> rad/s
        )

    def get_steering_report_msg(self, frame_id: str = 'UNDEFINED', timestamp_source: TimestampSource = TimestampSource.OS) -> 'SteeringReport':
        from autoware_vehicle_msgs.msg import SteeringReport
        return SteeringReport(
            header=self.get_header_msg(frame_id, timestamp_source),
            steering_tire_angle=math.radians(self.actor.get_control().steering),
        )

    def get_control_mode_report_msg(self, frame_id: str = 'UNDEFINED', timestamp_source: TimestampSource = TimestampSource.OS) -> 'ControlModeReport':
        from autoware_vehicle_msgs.msg import ControlModeReport
        remapping = {
            self.ControlMode.NONE: ControlModeReport.NO_COMMAND,
            self.ControlMode.CARLA_AUTOPILOT: ControlModeReport.NO_COMMAND,
            self.ControlMode.EXTERNAL_AUTOPILOT: ControlModeReport.AUTONOMOUS,
            self.ControlMode.MANUAL: ControlModeReport.MANUAL,
        }
        return ControlModeReport(
            header=self.get_header_msg(frame_id, timestamp_source),
            control_mode=remapping[self.control_mode],
        )

    def get_gear_report_msg(self, frame_id: str = 'UNDEFINED', timestamp_source: TimestampSource = TimestampSource.OS) -> 'GearReport':
        from autoware_vehicle_msgs.msg import GearReport
        gear = self.actor.get_control().gear
        reverse = self.actor.get_control().reverse
        gear_report = GearReport.NONE
        if gear == 0:
            gear_report = GearReport.NEUTRAL
        elif gear == 1:
            gear_report = GearReport.DRIVE
        if reverse:
            gear_report = GearReport.REVERSE
        return GearReport(
            header=self.get_header_msg(frame_id, timestamp_source),
            gear_report=gear_report,
        )

    def get_actuation_status_stamped_msg(self, frame_id: str = 'UNDEFINED', timestamp_source: TimestampSource = TimestampSource.OS) -> 'ActuationStatusStamped':
        from tier4_vehicle_msgs.msg import ActuationStatusStamped, ActuationStatus
        return ActuationStatusStamped(
            header=self.get_header_msg(frame_id, timestamp_source),
            control = 
            status=ActuationStatus(
                accel_status=self.control.throttle,
                brake_status=self.control.brake,
                steer_status=math.radians(self.control.steer),
            ),
        )
