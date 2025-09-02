from typing import List
from core.simulator import CarlaActor
from multiprocessing.shared_memory import SharedMemory


class DestroyRegister(object):

    def __init__(self):
        self._list_actor: List[CarlaActor] = list()
        self._list_shared_memory: List[SharedMemory] = list()

    def register(self, target: CarlaActor | SharedMemory):
        if isinstance(target, CarlaActor):
            self._list_actor.append(target)
        if isinstance(target, SharedMemory):
            self._list_shared_memory.append(target)
        raise TypeError(f"Given target is not a known type, given {type(target)}")

    def destroy(self):
        for shm in self._list_shared_memory:
            shm.close()
            shm.unlink()
        for actor in self._list_actor:
            actor.destroy()
