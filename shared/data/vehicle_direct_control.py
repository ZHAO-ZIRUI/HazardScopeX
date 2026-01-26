import carla
from typing import Any
from pathlib import Path
from dataclasses import dataclass
from typing_extensions import Self

from shared.data import SimulatorInput


@dataclass
class VehicleDirectControl(SimulatorInput):
    throttle: float = 0.0       # [CARLA DEFINED] Range: 0.0 to 1.0 (normalized)
    steer: float = 0.0          # [CARLA DEFINED] Range: -1.0 to 1.0 (normalized)
    brake: float = 0.0          # [CARLA DEFINED] Range: 0.0 to 1.0 (normalized)
    hand_brake: bool = False    # [CARLA DEFINED]
    reverse: bool = False       # [CARLA DEFINED]

    def to_carla(self) -> carla.VehicleControl:
        return carla.VehicleControl(
            throttle=self.throttle,
            steer=self.steer,
            brake=self.brake,
            hand_brake=self.hand_brake,
            reverse=self.reverse,
        )

    @classmethod
    def from_ros2(cls, msg: Any) -> Self:
        if msg.__class__.__name__ == 'ActuationCommand' or msg.__class__.__name__ == 'ActuationCommandStamped':
            return cls._from_autoware_actuation_command(msg)
        else:
            raise ValueError(f"Unsupported ROS message type: {msg.__class__.__name__}")

    @classmethod
    def _from_autoware_actuation_command(cls, msg: Any) -> Self:
        from tier4_vehicle_msgs.msg import ActuationCommand, ActuationCommandStamped
        cmd = msg if isinstance(msg, ActuationCommand) else msg.actuation

        return cls(
            throttle=cmd.accel_cmd,
            steer=cmd.steer_cmd,
            brake=cmd.brake_cmd,
            hand_brake=False,
            reverse=False,
        )

    def to_file(self, file_path: str | Path) -> Self:
        raise NotImplementedError