import os
from typing import List, Union

import gym
from gym import spaces
import numpy as np

from gym_battlesnake.envs.state import State
from gym_battlesnake.envs.constants import Reward

# from .game_renderer import GameRenderer


class BattlesnakeEnv(gym.Env):

    """
    Base class for different Battlesnake gym environments.
    """

    metadata = {"render.modes": ["human"]}

    def __init__(
        self,
        width: int,
        height: int,
        num_fruits: int = 1,
        sparse_rewards: bool = False,
        window_width: int = 18,
        window_height: int = 18,
    ):

        self.width = width
        self.height = height

        self.window_width = window_width
        self.window_height = window_height

        self.sparse_rewards = sparse_rewards
        self.num_fruits = num_fruits
        self.num_snakes = 1
        # if "DISPLAY" in os.environ:
        #     self.game_renderer = GameRenderer(width, height, self.num_snakes)
        self.state = State(
            width=self.width,
            height=self.height,
            num_snakes=self.num_snakes,
            num_fruits=self.num_fruits,
            window_width=self.window_width,
            window_height=self.window_height,
        )
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(
            low=0,
            high=255,
            shape=(1, self.window_width, self.window_height),
            dtype=np.uint8,
        )

    def reset(self):
        self.state = State(
            width=self.width,
            height=self.height,
            num_snakes=self.num_snakes,
            num_fruits=self.num_fruits,
            window_width=self.window_width,
            window_height=self.window_height,
        )
        return self.state.observe()

    def step(self, action: Union[List[int], int]):

        fruit_eaten, collided, starved, won = self.state.move_snakes(action)

        reward, terminal = self._evaluate_reward(fruit_eaten, collided, starved, won)

        terminal = terminal or won

        if terminal:
            next_state = None
        else:
            next_state = self.state.observe()

        return next_state, reward, terminal, {}

    def render(self, mode="human"):
        # if "DISPLAY" in os.environ:
        #     self.game_renderer.display(self.state)
        print(self.state.observe())

    def _evaluate_reward(
        self, fruit_eaten: bool, collided: bool, starved: bool, won: bool
    ):
        terminal = False
        reward = Reward.nothing.value
        if self.sparse_rewards:
            if collided or starved:
                reward = Reward.lost.value
                terminal = True
            elif won:
                reward = Reward.won.value
                terminal = True
        else:
            if collided:
                terminal = True
                reward = Reward.collision.value
            else:
                if won:
                    reward = Reward.won.value
                elif fruit_eaten:
                    reward = Reward.fruit.value
                elif starved:
                    terminal = True
                    reward = Reward.starve.value
        return reward, terminal
