import carla


class CarlaUtils(object):

    @staticmethod
    def print_short_tf(tf: carla.Transform) -> str:
        """
        返回一个 Transform 的短字符串, 用于输出日志
        :param tf: ``carla.Transform`` 实例
        :return: 简化字符串
        """
        return (f"TF("
                f"xyz:{tf.location.x:.2f}/{tf.location.y:.2f}/{tf.location.z:.2f}; "
                f"ypr:{tf.rotation.yaw:.2f}/{tf.rotation.pitch:.2f}/{tf.rotation.roll:.2f}"
                f")")