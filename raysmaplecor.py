import gymnasium as gym
from gymnasium.spaces import Discrete, Box
import numpy as np
import random

from typing import Optional
from ray.rllib.algorithms.ppo import PPOConfig
from ray.rllib.utils.test_utils import (
    add_rllib_example_script_args,
    run_rllib_example_script_experiment,
)
from ray.tune.registry import get_trainable_cls, register_env  # noqa



class SimpleCorridor(gym.Env):
    def __init__(self, config: Optional[dict] = None):
        config = config or {}
        self.end_pos = config.get("corridor_length", 7)
        self.cur_pos = 0
        self.action_space = Discrete(2)
        self.observation_space = Box(0.0, self.end_pos, shape=(1,), dtype=np.float32)

    def reset(self, *, seed=None, options=None):
        random.seed(seed)
        self.cur_pos = 0
        # Return obs and (empty) info dict.
        return np.array([self.cur_pos], np.float32), {}

    def step(self, action):
        assert action in [0, 1], action
        # Move left.
        if action == 0 and self.cur_pos > 0:
            self.cur_pos -= 1
        # Move right.
        elif action == 1:
            self.cur_pos += 1

        # The environment only ever terminates when we reach the goal state.
        terminated = self.cur_pos >= self.end_pos
        truncated = False
        # Produce a random reward from [0.5, 1.5] when we reach the goal.
        reward = random.uniform(0.5, 1.5) if terminated else -0.01
        infos = {}
        return (
            np.array([self.cur_pos], np.float32),
            reward,
            terminated,
            truncated,
            infos,
        )
CORRIDOR_LENGTH = 10

# 注册环境
register_env("corridor-env", lambda config: SimpleCorridor(config))

# 创建 PPO 配置
ppo_config = (
    PPOConfig()
    .environment("corridor-env", env_config={"corridor_length": CORRIDOR_LENGTH})
    # 其他配置参数可以在这里设置
)

# 创建 PPO 训练器
trainer = ppo_config.build()

# 运行训练
for i in range(10):  # 假设我们想要训练 50 个迭代周期
    print(trainer.train())  # 训练一步并打印结果


# 保存模型
checkpoint_path = trainer.save("path_to_checkpoint")

# 清理资源
trainer.stop()

