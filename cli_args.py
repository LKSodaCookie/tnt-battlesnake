import argparse


def get_args():
    parser = argparse.ArgumentParser(description='Train a DQN for Battlesnake')

    parser.add_argument('--max_episodes', type=int, default=2000000, help='Number of episodes to run.')
    parser.add_argument('--random_steps', type=int, default=80000, help='Number of random steps to initialize the replay memory.')
    parser.add_argument('--report_interval', type=int, default=1000, help='Interval of the reports.')
    parser.add_argument('--gym_env', type=str, help='The OpenAI gym game to use.')

    parser.add_argument('--continue_experiment', type=str, default=None, help='Continue experiment at the given directory.')

    parser.add_argument('--width', type=int, default=20, help='Width of the board.')
    parser.add_argument('--height', type=int, default=20, help='Height of the board.')
    parser.add_argument('--snakes', type=int, default=1, help='Number of snakes on the board.')
    parser.add_argument('--fruits', type=int, default=3, help='Number of fruits on the board.')

    parser.add_argument('--multi_step_n', type=int, default=1, help='Evaluate n-step discounted returns.')
    parser.add_argument('--frames', type=int, default=2, help='Frames of the game to concatenate.')
    parser.add_argument('--num_quantiles', type=int, default=20, help='Number of quantiles for the distributional agent.')

    parser.add_argument('--gamma', type=float, default=0.99, help='Discount factor for Bellman update.')
    parser.add_argument('--lambda', type=float, default=5e-6)
    parser.add_argument('--batch_size', type=int, default=32, help='Batch size that the DQN is trained on.')
    parser.add_argument('--learning_rate', type=float, default=0.001, help='Learning rate of the optimizer.')
    parser.add_argument('--training_interval', type=int, default=4, help='Run a training epoch every n observations.')

    parser.add_argument('--target_update_freq', type=int, default=10000,
                        help='Double DQN target network parameter update frequency.')

    parser.add_argument('--replay_capacity', type=int, default=1000000, help='Capacity of the replay memory.')

    parser.add_argument('--replay_beta_min', type=float, default=0.4,
                        help='Degree of importance weighting that is used. This value is linearly increased to 1 during training.')
    parser.add_argument('--replay_alpha_prio', type=float, default=0.6,
                        help='Degree of prioritization for prioritized experience replay. 0 means all experiences have the same priority.')
    parser.add_argument('--replay_min_prio', type=float, default=0.01,
                        help='Minimum priority for prioritized experience replay.')
    parser.add_argument('--replay_max_prio', type=float, default=1.0,
                        help='Initial maximum priority for prioritized experience replay.')

    return parser.parse_args()
