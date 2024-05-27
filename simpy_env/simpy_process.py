from simpy_env import Battery
from simpy_env import Queue

class ProcessingUnit():
    def __init__(self, env, processing_unit_id: int, battery: Battery, queue: Queue):
        self.env = env
        self.battery = battery
        self.queue = queue
        self.processing_unit_id = processing_unit_id
        self.process_event = env.event()
        self.process_proc = env.process(self.process())
        self.actual_process_data = 0

    def compute_energy(self, process_rate, duration):  # ke*算力*运行时间
        """
        计算处理过程消耗的能量。
        """
        k = 0.4
        w = 1
        return k * (process_rate ** w) * duration

    def actual_compute_duration(self, actual_consumed_energy, process_rate):
        k = 0.4
        w = 1
        actual_consumed_energy = actual_consumed_energy / k
        actual_consumed_energy = pow(actual_consumed_energy, 1)
        return actual_consumed_energy / process_rate

    def process_data(self, time, consumed_energy, level, duration):  # 处理过程
        print("??????????????????????????????????????????????????????????")
        sum = 0
        while self.env.now < time:
            if time - self.env.now > 1:
                sum = sum + level / duration
                self.queue.get(level / duration)
                self.battery.get(consumed_energy / duration)
                yield self.env.timeout(1)
            else:
                if (level / duration) * (time - self.env.now) - self.queue.level > 0 and (level / duration) * (
                        time - self.env.now) - self.queue.level < 0.1:
                    self.queue.get(self.queue.level)
                else:
                    print(f"1队列的的大小：{self.queue.level}")
                    self.queue.get((level / duration) * (time - self.env.now))
                    if self.queue.level < 0.1:
                        self.queue.get(self.queue.level)
                self.battery.get((consumed_energy / duration) * (time - self.env.now))
                print(f"2队列的的大小：{self.queue.level}")
                yield self.env.timeout(time - self.env.now)
        print("??????????????????????????????????????????????????????????")

    def process(self):
        """处理过程。"""
        while True:
            (q_out, duration) = yield self.process_event
            self.battery.mid_battery_level = self.battery.level
            print(f"充电完成level:{self.battery.mid_battery_level}")
            self.queue.mid_queue_level = self.queue.level
            print(f"队列开始level:{self.queue.mid_queue_level}")
            print(f"q_out = {q_out}")
            print(f"duration = {duration}")
            processed_data = q_out * duration
            print(f"processed_data = {processed_data}")
            level = self.queue.level  # 当前队列的长度
            print(f"在时间:{self.env.now},当前队列{self.queue.queue_id}的长度: {level:.4f}")
            if level <= 0:
                continue
            if processed_data >= self.queue.level:  # 当需要处理的数据 > 队列中存在的值
                process_duration = level / q_out  # 只取队列中存在的值，计算出一个大概的处理时间
                print(f"process_duration = {process_duration}")
                consumed_energy = self.compute_energy(q_out, process_duration)
                print(f"consumed_energy = {consumed_energy}")
                if consumed_energy > self.battery.level - self.battery.min_battery:  # 当消耗的电 > 可用电——电池最小安全值
                    print("1当需要处理的数据 > 队列中存在的值：当消耗的电 > 可用电——电池最小安全值")
                    actual_consumed_energy = self.battery.level - self.battery.min_battery
                    print(f"actual_consumed_energy = {actual_consumed_energy}")
                    actual_process_duration = self.actual_compute_duration(actual_consumed_energy, q_out)
                    print(f"actual_process_duration = {actual_process_duration}")
                    actual_process_data = actual_process_duration * q_out
                    print(f"actual_process_data = {actual_process_data}")
                    self.actual_process_data = actual_process_data
                    time = self.env.now + actual_process_duration
                    print(f"time = {time}")
                    # 修改状态
                    self.queue.state = (
                        "dequeue",
                        self.env.now,
                        q_out,
                        actual_process_duration,
                    )  # 标记出队状态
                    self.battery.state = (
                        "decharge",
                        self.env.now,
                        0.4 * (q_out ** 1) * actual_process_duration,
                        actual_process_duration,
                    )
                    yield self.env.process(
                        self.process_data(time, actual_consumed_energy, actual_process_data, actual_process_duration))
                    self.queue.state = None  # 标记为非出队状态
                    print(
                        f"在时间: {self.env.now:.4f} 处理阶段完成，处理量: {actual_process_data:.4f}, 消耗电池{self.battery.battery_id} 能量 {actual_consumed_energy:.4f} J, 电池剩余电量{self.battery.level}"
                    )
                    idle = duration - actual_process_duration
                    yield self.env.timeout(idle)
                    print(f"在时间: {self.env.now:.4f} 处理全过程完成，空等时间: {idle:.4f}")
                else:
                    print("2当需要处理的数据 > 队列中存在的值：当消耗的电 < 可用电——电池最小安全值")
                    time = self.env.now + process_duration
                    # 修改状态
                    self.queue.state = (
                        "dequeue",
                        self.env.now,
                        q_out,
                        process_duration,
                    )  # 标记出队状态
                    self.battery.state = (
                        "decharge",
                        self.env.now,
                        0.4 * (q_out ** 1) * process_duration,
                        process_duration,
                    )
                    yield self.env.process(self.process_data(time, consumed_energy, level, process_duration))
                    self.queue.state = None  # 标记为非出队状态
                    print(
                        f"在时间: {self.env.now:.4f} 处理阶段完成，处理量: {level:.4f}, 消耗电池{self.battery.battery_id} 能量 {consumed_energy:.4f} J, 电池剩余电量{self.battery.level}"
                    )
                    idle = duration - process_duration
                    yield self.env.timeout(idle)
                    print(f"在时间: {self.env.now:.4f} 处理全过程完成，空等时间: {idle:.4f}")
            else:
                consumed_energy = self.compute_energy(q_out, duration)
                print(f"consumed_energy = {consumed_energy}")
                if consumed_energy > self.battery.level - self.battery.min_battery:  # 当消耗的电 > 可用电——电池最小安全值
                    print("3当需要处理的数据 < 队列中存在的值：当消耗的电 > 可用电——电池最小安全值")
                    actual_consumed_energy = self.battery.level - self.battery.min_battery
                    print(f"actual_consumed_energy = {actual_consumed_energy}")
                    actual_process_duration = self.actual_compute_duration(actual_consumed_energy, q_out)
                    print(f"actual_process_duration = {actual_process_duration}")
                    actual_process_data = actual_process_duration * q_out
                    print(f"actual_process_data = {actual_process_data}")
                    self.actual_process_data = actual_process_data
                    time = self.env.now + actual_process_duration
                    # 修改状态
                    self.queue.state = (
                        "dequeue",
                        self.env.now,
                        q_out,
                        actual_process_duration,
                    )  # 标记出队状态
                    self.battery.state = (
                        "decharge",
                        self.env.now,
                        0.4 * (q_out ** 1) * actual_process_duration,
                        actual_process_duration,
                    )
                    yield self.env.process(
                        self.process_data(time, actual_consumed_energy, actual_process_data, actual_process_duration))
                    self.queue.state = None  # 标记为非出队状态
                    print(
                        f"在时间: {self.env.now:.4f} 处理阶段完成，处理量: {actual_process_data:.4f}, 消耗电池{self.battery.battery_id} 能量 {actual_consumed_energy:.4f} J, 电池剩余电量{self.battery.level}"
                    )
                    print(f"队列剩余未处理数据量为：{self.queue.level}")
                    idle = duration - actual_process_duration
                    yield self.env.timeout(idle)
                    print(f"在时间: {self.env.now:.4f} 处理全过程完成，空等时间: {idle:.4f}")
                else:
                    print("4当需要处理的数据 < 队列中存在的值：当消耗的电 < 可用电——电池最小安全值")
                    time = self.env.now + duration
                    self.queue.state = (
                        "dequeue",
                        self.env.now,
                        q_out,
                        duration,
                    )  # 标记出队状态
                    self.battery.state = (
                        "decharge",
                        self.env.now,
                        0.4 * (q_out ** 1) * duration,
                        duration,
                    )
                    yield self.env.process(self.process_data(time, consumed_energy, processed_data, duration))

                    self.queue.state = None  # 标记为非出队状态
                    print(
                        f"在时间: {self.env.now:.4f} 处理过程完成，处理量: {processed_data:.4f}, 消耗第{self.battery.battery_id}电池的能量 {consumed_energy:.4f} J, 电池剩余电量为 {self.battery.level}")
            self.battery.end_battery_level = self.battery.level
            print(f"耗电结束level:{self.battery.end_battery_level}")
            self.queue.end_queue_level = self.queue.level
            print(f"队列开始level:{self.queue.end_queue_level}")