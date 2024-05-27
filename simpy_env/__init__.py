import simpy
from simpy import Container

class Battery(Container):
    def __init__(
        self,
        env: simpy.Environment,
        capacity: float,
        initial_level: float,
        battery_id: int,
    ):
        super().__init__(env, capacity, initial_level)
        self.min_battery = 1000
        self.one_slot_battery = 0
        self.start_battery_level = 0
        self.mid_battery_level = 0
        self.end_battery_level = 0
        self.battery_id = battery_id
        self.state = None


class Queue(Container):
    def __init__(
        self,
        env: simpy.Environment,
        capacity: float,
        initial_level: float,
        queue_id: int,
    ):
        super().__init__(env, capacity, initial_level)
        self.total_excess = 0
        self.one_slot_data = 0
        self.start_queue_level = 0
        self.mid_queue_level = 0
        self.end_queue_level = 0
        self.queue_id = queue_id
        self.en_state = None
        self.de_state = None