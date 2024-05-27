import random
import gymnasium as gym
from gymnasium.spaces import Discrete, Box
import numpy as np
from ray.rllib.algorithms.ppo import PPOConfig
from ray.tune.registry import get_trainable_cls, register_env  # noqa


class SimpleCorridor(gym.Env):
    def __init__(self, config):
        config = config or {}
        self.length = config["corridor_length"]
        self.start_pos = 0
        self.end_pos = self.length - 1
        self.action_space = Discrete(2)
        self.observation_space = Box(0.0, self.length, shape=(2,), dtype='int32')

    def reset(self, *, seed=None, options=None):
        random.seed(seed)
        self.cur_pos = self.start_pos
        return np.array([self.cur_pos, self.end_pos]),{}

    def step(self, action):
        if action == 0 and self.cur_pos > 0:  # walk left
            self.cur_pos -= 1
        if action == 1 and self.cur_pos < self.length - 1:
            self.cur_pos += 1

        # The environment only ever terminates when we reach the goal state.
        terminated = self.cur_pos >= self.end_pos
        truncated = False
        if self.cur_pos == self.end_pos:
            truncated = True
        # Produce a random reward from [0.5, 1.5] when we reach the goal.
        reward = random.uniform(0.5, 1.5) if terminated else -0.01
        infos = {}
        return (
            np.array([self.cur_pos, self.end_pos], np.float32),
            reward,
            terminated,
            truncated,
            infos
        )

register_env("corridor-env", lambda config: SimpleCorridor(config))

# 设置环境配置
ppoConfig = PPOConfig()
config = ppoConfig.environment("corridor-env", env_config={"corridor_length": 10}
).framework(
    "torch"  # 使用 PyTorch 框架
).resources(
    num_gpus=0  # 不使用 GPU
).rollouts(
    num_rollout_workers=4  # 设置 rollout workers 的数量
)

# 设置模型配置
config.model["fcnet_hiddens"] = [64, 64]
config.model["fcnet_activation"] = "relu"

# 构建训练器
trainer = config.build()

# 开始训练
for _ in range(10):  # 例如，运行 10 次训练迭代
    print(trainer.train())

# 清理资源
trainer.stop()