import time
import carla

from core.simulator import CarlaContext, CarlaActor


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
        return (f"VehicleControl("
                f"throttle:{control.throttle:.2f}; "
                f"steer:{control.steer:.2f}; "
                f"brake:{control.brake:.2f}; ")

    @staticmethod
    def wait_all_actors_stable(
            context: CarlaContext,
            *actors: CarlaActor
    ):
        """
        等待全部的 Actor 达到稳定状态
        :param context: ``CarlaContext`` 实例, 仿真上下文
        :param actors: 不限定长度的 ``CarlaActor`` 实例
        :return:
        """
        generators = [actor.wait_stable_no_block() for actor in actors]

        while True:
            flags = [next(gen) for gen in generators]
            if all(flags):
                break

            # 进行 tick 操作
            if context.is_sync_mode:
                context.world.tick()
                time.sleep(context.sync_mode_delta_seconds)
            else:
                context.world.wait_for_tick()

        # 清理迭代器残留
        for gen in generators:
            gen.close()
        del generators