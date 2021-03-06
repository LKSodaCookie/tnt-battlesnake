from typing import List, NamedTuple

import keras
import numpy as np

from common.models.transition import Transition
from common.replay_memory import PrioritizedMemory
from common.tensorflow.huber_loss import huber_loss
from common.utils.compute_multi_step_rewards import compute_multi_step_rewards
from dqn.exploration import ExplorationStrategy


class HyperParameters(NamedTuple):
    learning_rate: float
    discount_factor: float
    batch_size: int
    importance_weight_exponent: float
    multi_step_n: int
    batches: int


class DQNAgent:

    """
    Reinforcement Learning Agent that uses a DQN.

    See https://arxiv.org/abs/1312.5602
    """

    def __init__(
        self,
        dqn: keras.Model,
        replay_memory: PrioritizedMemory,
        exploration_strategy: ExplorationStrategy,
        hyper_parameters: HyperParameters,
        num_actions: int,
        output_dir: str,
    ):
        self.global_step = 0
        self.episode = 0
        self.hyper_parameters = hyper_parameters
        self.num_actions = num_actions
        self.output_dir = output_dir

        self.dqn = dqn
        self.optimizer = keras.optimizers.Adam(lr=hyper_parameters.learning_rate)
        self.dqn.compile(loss=huber_loss, optimizer=self.optimizer)
        # This is needed to compute the time difference errors during training
        self.dqn.metrics_tensors += [self.dqn.layers[-1].output]
        self.dqn.summary()
        self.replay_memory = replay_memory
        self.exploration_strategy = exploration_strategy

    def act(self, state):
        """
        Use the DQN to choose an action for the given state.

        Arguments:
            state {`np.ndarray`} -- Tensor representation of the state

        Returns:
            `int` -- Index of the chosen action
        """
        is_convolutional = len(self.dqn.input_shape[0]) == 4
        state = np.asarray(state)
        if is_convolutional:
            if len(state.shape) == 3:
                state = np.expand_dims(state, 0)
            state = state / 255.0
        else:
            if len(state.shape) == 1:
                state = np.expand_dims(state, 0)
        q_values = np.squeeze(
            self.dqn.predict([state, np.ones(shape=(state.shape[0], self.num_actions))])
        )
        self.global_step += state.shape[0]
        return np.squeeze(
            self.exploration_strategy.choose_action(q_values, self.episode)
        )

    def observe(self, transitions: List[Transition]):
        if self.hyper_parameters.multi_step_n > 1:
            transitions = compute_multi_step_rewards(
                transitions,
                self.hyper_parameters.multi_step_n,
                self.hyper_parameters.discount_factor,
            )
        for transition in transitions:
            self.replay_memory.add(transition)
        if len(transitions) != 1 or transitions[0].next_state is None:
            self.episode += len(transitions)

    def train(self):
        """
        Sample a batch of transitions and update the DQN using gradient descent.

        Returns:
            `float` -- Mean loss for the sampled training batch
        """
        if (
            self.replay_memory.size()
            < self.hyper_parameters.batch_size * self.hyper_parameters.batches
        ):
            return

        transitions, indices, weights = self.replay_memory.sample(
            self.hyper_parameters.batch_size * self.hyper_parameters.batches,
            self.hyper_parameters.importance_weight_exponent,
        )
        tensors = self._get_tensors(transitions)
        loss, time_difference_errors = self._compute_loss(
            *tensors, importance_weights=weights
        )

        self.replay_memory.update(indices, time_difference_errors)

        if self.global_step % 1000 == 0:
            try:
                self.dqn.save("/tmp/checkpoint-schubert-battlesnake-model.h5")
            except Exception:
                print("Could not save checkpoint")

        return loss

    def _compute_loss(
        self,
        state_tensor,
        action_tensor,
        reward_tensor,
        next_state_tensor,
        non_terminal_mask,
        importance_weights,
    ):
        """
        Compute the Q-Learning loss for the DQN.

        Arguments:
            state_tensor {`np.ndarray`} -- Tensor of states
            action_tensor {`np.ndarray`} -- Tensor of the chosen actions
            reward_tensor {`np.ndarray`} -- Tensor of the observed rewards
            next_state_tensor {`np.ndarray`} -- Tensor of the next states
            non_terminal_mask {`np.ndarray`} -- Tensor indicating the non-terminal states
            importance_weights {`np.ndarray`} -- Tensor of importance weights

        Returns:
            `float` -- Loss 
        """
        y = self._compute_targets(
            state_tensor,
            action_tensor,
            reward_tensor,
            next_state_tensor,
            non_terminal_mask,
        )
        actions_one_hot = np.eye(self.num_actions)[action_tensor]
        x = [state_tensor, actions_one_hot]
        return self._fit(x=x, y=y, importance_weights=importance_weights)

    def _compute_targets(
        self,
        state_tensor,
        action_tensor,
        reward_tensor,
        next_state_tensor,
        non_terminal_mask,
    ):
        batch_size = state_tensor.shape[0]
        q_values_next = self.dqn.predict(
            [next_state_tensor, np.ones(shape=(batch_size, self.num_actions))]
        )
        q_values_next_max = np.zeros(shape=(batch_size,))
        q_values_next_max[non_terminal_mask] = np.max(q_values_next, axis=-1)

        q_values_target = np.zeros(shape=(batch_size, self.num_actions))

        for i in range(batch_size):
            q_values_target[i, action_tensor[i]] = (
                reward_tensor[i]
                + (
                    self.hyper_parameters.discount_factor
                    ** self.hyper_parameters.multi_step_n
                )
                * q_values_next_max[i]
            )

        return q_values_target

    def _fit(self, x: np.ndarray, y: np.ndarray, importance_weights: np.ndarray):
        """
        Performs one epoch of supervised training of the DQN.
        
        Arguments:
            x {np.ndarray} -- input
            y {np.ndarray} -- target output
        
        Returns:
            `float` -- Loss
        """
        losses = []
        errors = []
        for (
            state_tensor_batch,
            actions_one_hot_batch,
            y_batch,
            importance_weight_batch,
        ) in zip(
            np.split(x[0], self.hyper_parameters.batches),
            np.split(x[1], self.hyper_parameters.batches),
            np.split(y, self.hyper_parameters.batches),
            np.split(importance_weights, self.hyper_parameters.batches),
        ):
            loss, outputs = self.dqn.train_on_batch(
                x=[state_tensor_batch, actions_one_hot_batch],
                y=y_batch,
                sample_weight=importance_weight_batch,
            )
            losses.append(loss)
            time_difference_errors = np.sum(np.abs(y_batch - outputs), axis=-1)
            errors.extend(time_difference_errors)
        return np.mean(losses), time_difference_errors

    def _get_tensors(self, transitions: List[Transition]):
        """
        Transform the transitions into Pytorch tensors for training.

        Arguments:
            transitions {`List[Transition]`} -- Sampled transition batch

        Returns:
            `Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]` -- Tensors to be used for training
        """
        is_convolutional = len(self.dqn.input_shape[0]) == 4
        state_tensor = np.asarray(
            [
                np.asarray(t.state) / 255.0 if is_convolutional else np.array(t.state)
                for t in transitions
            ]
        )
        action_tensor = np.asarray([t.action for t in transitions], dtype=np.int64)
        reward_tensor = np.asarray([t.reward for t in transitions])
        next_state_tensor = np.asarray(
            [
                np.asarray(t.next_state) / 255.0
                if is_convolutional
                else np.asarray(t.next_state)
                for t in transitions
                if t.next_state is not None
            ]
        )

        non_terminal_mask = np.asarray(
            [t.next_state is not None for t in transitions], dtype=np.uint8
        ).nonzero()
        return (
            state_tensor,
            action_tensor,
            reward_tensor,
            next_state_tensor,
            non_terminal_mask,
        )
