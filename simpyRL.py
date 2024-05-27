import random
import csv
import simpy
import gymnasium as gym
from gymnasium.spaces import Tuple, Box, Discrete
import numpy as np
from ray.rllib.algorithms.ppo import PPOConfig
from simpy_env import Battery
from simpy_env import Queue
from simpy_env.simpy_Controller import Controller
from simpy_env.simpy_charge import WirelessCharger
from simpy_env.simpy_produce import DataProducer
from simpy_env.simpy_process import ProcessingUnit
from ray.tune.registry import get_trainable_cls, register_env  # noqa

class ChargeEnv(gym.Env):
    def __init__(self, config):
        config = config or {}
        self.gamma = 0
        self.tau = 0
        self.alpha = 0
        self.beta = 0
        self.env = simpy.Environment()
        self.Battery = Battery(self.env, 100000, 0, 0)
        self.Queue = Queue(self.env, 500000, 0, 0)
        self.DataProducer = [DataProducer(env=self.env, queue=self.Queue, data_source='?', data_producer_id=0)]
        self.ProcessingUnit = [ProcessingUnit(env=self.env, battery=self.Battery, queue=self.Queue, processing_unit_id=0)]
        self.WirelessCharger = [WirelessCharger(self.env, battery=self.Battery, battery_id=0)]
        self.controller = Controller(self.env, wireless_chargers=self.WirelessCharger,processing_units=self.ProcessingUnit,data_producers=self.DataProducer)
        self.end_time = 565200  # 数据集内内最后的end_time为565083.288
        self.cur_time_slot = 0
        self.end_time_slot = self.end_time/1200
        self.prev_queue_level = 0
        self.prev_battery_level = 0
        self.pre_drop_packets = 0
        self.queue_ratio = 0
        self.battery_ratio = 0
        self.drop_packets = 0
        self.queue_delta = 0
        self.battery_delta = 0
        self.drop_packets_delta = 0
        self.total_one_slot_data = 0
        self.process_computing_power = 1000
        self.action_space = Box(low=0, high=1, shape=(4,), dtype=np.float32)
        self.observation_space = Box(-10000.0, 1000000, shape=(7,), dtype=np.float32)#7个元素
        self.read_data()


    def read_data(self):#读数据
        file_path = 'dataset/finial_data.csv'
        with open(file_path, mode='r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if int(row['num_id']) == 1:
                    # print(f"id: {row['id']}, start_time: {row['start_time']}, end_time: {row['end_time']}, rate: {row['rate']}, duration: {row['duration']}, total: {row['total']}")
                    self.controller.notify_produce(
                        at_time=float(row['start_time']),
                        data_producer_id=int(row['num_id']) - 1,
                        q_in=float(row["rate"]),
                        duration=float(row['duration']),
                    )

    def get_state(self):
        now_level = self.Queue.level
        # 1、经过一个time_slot后队列剩余的数据量除以队列总容量
        self.queue_ratio = now_level / self.Queue.capacity
        print(f"self.queue_ratio:{self.queue_ratio}")
        # 2、经过一个time_slot后电池剩余的电量除以电池总容量
        self.battery_ratio = self.Battery.level / self.Battery.capacity
        # 3、每个time_slot内的丢包数量
        self.drop_packets = self.Queue.total_excess
        print(f"每个time_slot内的丢包数量drop_packets:{self.Queue.total_excess}")
        # 4、一个time_slot结束后的的队列长度减去上一个time_slot结束后剩余的队列长度
        self.queue_delta = now_level - self.prev_queue_level
        # 5、一个time_slot结束后的的电池余量减去上一个time_slot结束后剩余的电池余量
        self.battery_delta = self.Battery.level - self.prev_battery_level
        # 6、一个time_slot结束后的的丢包数量减去上一个time_slot结束后剩余的丢包数量
        self.drop_packets_delta = self.drop_packets - self.pre_drop_packets
        print(f"两时刻的丢包数量相减：{self.drop_packets_delta}")
        # 7外部数据的RNN特征，暂时不写(暂时先用每个time_slot中传入的data总数代替)
        self.total_one_slot_data = self.Queue.one_slot_data
        print(f"每个time_slot内的入队数量total_one_slot_data:{self.total_one_slot_data}")
        self.prev_queue_level = now_level
        self.prev_battery_level = self.Battery.level
        self.pre_drop_packets = self.drop_packets
        print(f"pre_drop_packets:{self.pre_drop_packets}")
        return [self.queue_ratio, self.battery_ratio, self.drop_packets, self.queue_delta, self.battery_delta,
                self.drop_packets_delta, self.total_one_slot_data]

    def reset(self,*,seed = None,options = None):#回到初始状态
        random.seed(seed)
        if self.Queue.level != 0:
            self.Queue.get(self.Queue.level)
        if self.Battery.level != 0:
            self.Battery.get(self.Battery.level)
        self.cur_time_slot = 0
        self.prev_queue_level = 0
        self.prev_battery_level = 0
        self.pre_drop_packets = 0
        self.queue_ratio = 0
        self.battery_ratio = 0
        self.drop_packets = 0
        self.queue_delta = 0
        self.battery_delta = 0
        self.drop_packets_delta = 0
        self.total_one_slot_data = 0
        self.read_data()
        # Return obs and (empty) info dict.
        return np.array(self.get_state(), np.float32), {}


    def step(self, action):
        self.alpha = action[0]
        self.beta = action[1]
        self.tau = action[2]
        self.gamma = action[3]
        reward = 0
        truncated = False
        if self.cur_time_slot < self.end_time_slot:
            self.controller.notify_charge(
                at_time=0,
                p_in=250,
                duration=(self.alpha * 1200),
                battery_id=0,
            )
            process_time_at = self.alpha * 1200
            # 注册处理事件
            self.controller.notify_process(
                at_time=process_time_at,
                processing_unit_id=0,
                q_out=self.gamma * self.process_computing_power,
                duration=((1 - self.alpha) * 1200 * self.tau),
            )
            self.env.run(until=self.cur_time_slot * 1200 + 1200)
            state = self.get_state()
            reward = random.uniform(0.5, 1.5)#reward:能胜利走完一个T就random一点,basic是0
            if self.alpha < 0.15:#比如说最少充电，也就是alpha<0.15
                truncated = True
            if self.drop_packets/self.total_one_slot_data > 0.3:#丢包率大于30
                truncated = True
            self.cur_time_slot += 1

        terminated = self.end_time_slot >= self.cur_time_slot
        infos = {}
        return (
            np.array(state, np.float32),
            reward,
            terminated,#自然结束
            truncated,#人为中断
            infos,
        )

    def render(self):
        pass


if __name__ == "__main__":
    # 注册环境
    register_env("charge-env", lambda config: ChargeEnv(config))

    # 设置环境配置
    ppoConfig = PPOConfig()
    config = ppoConfig.environment(
        "charge-env", env_config={"corridor_length": 10}
    ).framework(
        "torch"
    ).resources(
        num_gpus=0 #不使用GPU
    ).rollouts(
        num_rollout_workers=1  # 设置 rollout workers 的数量
    )

    # 设置模型配置
    config.model["fcnet_hiddens"] = [64, 64]
    config.model["fcnet_activation"] = "relu"
    config.training(gamma=0.9, lr=0.0005,train_batch_size=128, clip_param=0.2)

    # 创建 PPO 训练器
    trainer = config.build()

    # 运行训练
    for i in range(3):  # 假设我们想要训练 50 个迭代周期
        print(trainer.train())  # 训练一步并打印结果


    # 保存模型
    checkpoint_path = trainer.save("path_to_checkpoint")

    # 清理资源
    trainer.stop()