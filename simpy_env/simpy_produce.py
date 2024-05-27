from simpy_env import Queue


class DataProducer:
    def __init__(self, env, queue: Queue, data_source: str, data_producer_id: int):
        self.env = env
        self.queue = queue
        self.data_source = (
            data_source  # 从某个文件读取数据作为数据源,比如data_source = './trace.csv'
        )
        self.data_producer_id = data_producer_id
        self.produce_event = env.event()
        self.produce_proc = env.process(self.produce())
    def produce(self):
        """生产过程。"""
        while True:
            (q_in, duration) = yield self.produce_event
            self.queue.start_queue_level = self.queue.level
            print(f"队列开始level:{self.queue.start_queue_level}")
            produce_data = q_in * duration
            now_capacity = self.queue.capacity - self.queue.level#剩余可用容量
            print(f"在时间: {self.env.now:.4f},(PU：{self.data_producer_id})的剩余队列空间: {now_capacity:.4f}")
            if now_capacity <= 0:#当前队列里已经没有空位了
                excess = produce_data
                print(f"{self.data_producer_id}, 1total_excess:{self.queue.total_excess:.4f}, 丢包{excess:.4f}")
                self.queue.total_excess = self.queue.total_excess + excess
                print(f"{self.data_producer_id}, 2total_excess:{self.queue.total_excess:.4f}")
                yield self.env.timeout(duration)
                self.queue.state = None  # 标记为非入队状态
                print(
                    f"在时间: {self.env.now:.4f} ，对(PU：{self.data_producer_id})的，喂入阶段完成，喂入量: {now_capacity:.4f}，共丢包为：{excess:.4f}"
                )
                continue
            if produce_data > now_capacity:  # 如果传进来数据大于可用容量
                excess = (self.queue.level + produce_data) - self.queue.capacity  # 丢包
                print(f"{self.data_producer_id}, 3total_excess:{self.queue.total_excess:.4f}, 丢包{excess:.4f}")
                self.queue.total_excess = self.queue.total_excess + excess
                print(f"4total_excess:{self.queue.total_excess:.4f}")
                in_data = produce_data - excess
                actual_duration = in_data / q_in
                self.queue.state = (
                    "enqueue",
                    self.env.now,
                    q_in,
                    actual_duration,
                )  # 标记为入队状态
                print(
                    f"(PU：{self.data_producer_id})实际进来的数据量:{in_data:.4f},总共被传输的数据:{produce_data:.4f},丢包: {excess:.4f}"
                )
                time = self.env.now + actual_duration
                if in_data > 0:
                    while self.env.now < time:
                        if time -self.env.now > 1:
                            self.queue.put(in_data/actual_duration)
                            self.queue.one_slot_data = self.queue.one_slot_data + in_data/actual_duration
#                             print(in_data/actual_duration)
                            yield self.env.timeout(1)
                        else:
                            #  399入不进去的原因为，我们进行的是除法运算，
                            # 有些四舍五入会导致数据实际有出入，399.xxxx + self.queue.level > self.queue.capacity，所以put无法入，无限399
                            step_in_data = (produce_data/duration)*(time-self.env.now)
                            total_level_wucha = self.queue.level + step_in_data - self.queue.capacity
                            # 判断误差小于一定程度时直接按照queue的容量put
                            if total_level_wucha <= 0.0001:
                                self.queue.put(self.queue.capacity - self.queue.level)
                                self.queue.one_slot_data = self.queue.one_slot_data + self.queue.capacity - self.queue.level
                            else:
                                self.queue.put((produce_data/duration)*(time-self.env.now))
                                self.queue.one_slot_data = self.queue.one_slot_data + ((produce_data/duration)*(time-self.env.now))
                            yield self.env.timeout(time-self.env.now)
                self.queue.state = None  # 标记为非入队状态
                print(
                    f"在时间: {self.env.now:.4f} ，对(PU：{self.data_producer_id})的，喂入阶段完成，喂入量: {in_data:.4f}，数据队列已满，队列现有数据量为：{self.queue.level:.4f}"
                )
                idle = duration - actual_duration
                yield self.env.timeout(idle)
                print(
                    f"在时间: {self.env.now:.4f} 喂入全过程完成，空等时间: {idle:.4f}，丢包：{excess:.4f}"
                )
            else:
                self.queue.state = (
                    "enqueue",
                    self.env.now,
                    q_in,
                    duration,
                )  # 标记为入队状态
                time = self.env.now + duration
                while self.env.now < time:
                    if time -self.env.now > 1:
                        self.queue.put(produce_data/duration)
                        self.queue.one_slot_data = self.queue.one_slot_data + produce_data/duration
#                         print(produce_data/duration)
                        yield self.env.timeout(1)
                    else:
                        self.queue.put((produce_data/duration)*(time-self.env.now))
                        self.queue.one_slot_data = self.queue.one_slot_data + (produce_data/duration)*(time-self.env.now)
#                         print((produce_data/duration)*(time-self.env.now))
                        yield self.env.timeout(time-self.env.now)
                self.queue.state = None  # 标记为非入队状态
                print(
                    f"在时间: {self.env.now:.4f} ，对(PU：{self.data_producer_id})的，喂入阶段完成，喂入量: {produce_data:.4f}，队列现有数据量为：{self.queue.level:.4f}，队列剩余空间：{self.queue.capacity-self.queue.level}"
                )