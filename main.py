import ray
import ray.tune as tune
import gym

import gym_battlesnake
from gym_battlesnake.wrappers import FrameStack


def env_creator(config):
    env = gym.make(config["name"])
    if config["frame_stack"] > 1:
        env = FrameStack(env, num_stacked_frames=config["frame_stack"])
    return env


def main():

    ray.init(redis_address="130.75.31.53:6379")
    ray.tune.register_env("battlesnake", env_creator)
    tune.run_experiments(
        {
            "battlesnake": {
                "run": "IMPALA",
                "env": "battlesnake",
                "stop": {"episode_reward_mean": 200},
                "config": {
                    "model": {
                        "use_lstm": True,
                        "conv_filters": [
                            [16, [2, 2], 1],
                            [32, [2, 2], 2],
                            [256, [9, 9], 1],
                        ],
                    },
                    "env_config": {
                        "frame_stack": 2,
                        "name": "battlesnake-18x18-easy-v0",
                    },
                    "num_data_loader_buffers": 4,
                    "sample_batch_size": 500,
                    "train_batch_size": 500,
                    "num_workers": 32,
                    "num_envs_per_worker": 10,
                    "max_sample_requests_in_flight_per_worker": 5
                },
            }
        }
    )


if __name__ == "__main__":
    main()
