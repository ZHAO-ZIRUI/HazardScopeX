import carla


class CarlaUtils(object):

    @staticmethod
    def short_tf(tf: carla.Transform) -> str:
        """
        返回一个 Transform 的短字符串, 用于输出日志
        :param tf: ``carla.Transform`` 实例
        :return: 简化字符串
        """
        return (f"TF("
                f"xyz:{tf.location.x:.2f}/{tf.location.y:.2f}/{tf.location.z:.2f}; "
                f"ypr:{tf.rotation.yaw:.2f}/{tf.rotation.pitch:.2f}/{tf.rotation.roll:.2f}"
                f")")

    @staticmethod
    def short_direct_control(control: carla.VehicleControl) -> str:
        """
        :param control: ``carla.VehicleControl`` 对象
        :return: 返回一个 ``carla.VehicleControl`` 的短字符串, 用于输出日志
        """
        long = control.throttle if control.throttle > 0 else -control.throttle
        lat = control.steer
        return (f"VehicleControl("
                f"LONG/LAT: {long:.2f}/{lat:.2f}; "
                f"REV: {control.reverse})")
