from shared.scenarios import Factor
from shared.simulator import *
from shared.data import Image, PointCloud, SimulatorOutput


class FactorSensorNoData(Factor):
    NAME = 'F_SensorNoData'

    def __init__(self, context: CarlaContext, sensor: CarlaSensor):
        super().__init__(context)
        self._sensor = sensor

    def setup(self) -> None:
        self._sensor.hook_sensor_data_recv.append(self.on_sensor_data_recv)
        return super().setup()

    def on_sensor_data_recv(self, data: SimulatorOutput) -> SimulatorOutput:
        if isinstance(data, Image):
            data._raw[:] = [0, 0, 0, 0]
        elif isinstance(data, PointCloud):
            if data.format == PointCloud.Format.XYZ:
                data._raw[:] = [0, 0, 0]
            elif data.format == PointCloud.Format.XYZ_Intensity:
                data._raw[:] = [0, 0, 0, 0]
            elif data.format == PointCloud.Format.XYZ_Intensity_Channel:
                data._raw[:] = [0, 0, 0, 0, 0]
            elif data.format == PointCloud.Format.XYZ_Channel_Agnle_Id_SemTag:
                data._raw[:] = [0, 0, 0, 0, 0, 0, 0]
            else:
                raise ValueError(f"Unsupported point cloud format: {data.format}")
        return data