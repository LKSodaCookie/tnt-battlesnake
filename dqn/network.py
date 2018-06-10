from keras import Model, Input
from keras.layers import Conv2D, Flatten, Lambda, Add, Dense
from keras.optimizers import RMSprop
import tensorflow as tf
import numpy as np


class DQN:

    def __init__(self, input_shape, num_actions, learning_rate):
        self.input_shape = input_shape
        self.num_actions = num_actions
        self.learning_rate = learning_rate
        self.online_model = self._create_model()
        self.target_model = self._create_model()
        self.callbacks = []

    def predict(self, state, target=False):
        if len(state.shape) == 3:
            # Single state
            state = np.expand_dims(state, 0)
        if target:
            return self.target_model.predict(state)
        else:
            return self.online_model.predict(state)

    def create_targets(self, observations, gamma, batch_size):

        q_values, q_values_next = self._compute_q_values(observations)

        x = np.zeros((batch_size, ) + self.input_shape)
        y = np.zeros((batch_size, self.num_actions))
        errors = np.zeros(batch_size)

        for idx, o in enumerate(observations):
            target = q_values[idx]
            target_old = np.copy(target)
            if o.next_state is None:
                target[o.action] = o.reward
            else:
                target[o.action] = o.reward + gamma * np.amax(q_values_next[idx])
            x[idx] = o.state
            y[idx] = target
            errors[idx] = np.abs(target[o.action] - target_old[o.action])
        return x, y, errors

    def train(self, x, y, batch_size, weights):
        history = self.online_model.fit(
            x=x,
            y=y,
            batch_size=batch_size,
            verbose=0,
            sample_weight=weights,
            callbacks=self.callbacks)
        return history.history['loss'][0]

    def update_target_model(self):
        self.target_model.set_weights(self.online_model.get_weights())

    def _compute_q_values(self, observations):
        no_state = np.zeros(self.input_shape)
        next_states = np.array([(no_state if o.next_state is None else o.next_state) for o in observations])
        states = np.array([o.state for o in observations])

        q_values = np.array(self.target_model.predict(states))
        q_values_next = np.array(self.target_model.predict(next_states))

        return q_values, q_values_next

    def _create_model(self):
        inputs = Input(shape=self.input_shape)
        net = Conv2D(32, 4, strides=1, activation='relu')(inputs)
        net = Conv2D(64, 4, strides=2, activation='relu')(net)
        net = Conv2D(64, 3, strides=1, activation='relu')(net)
        net = Flatten()(net)
        advt = Dense(512, activation='relu')(net)
        advt = Dense(self.num_actions)(advt)
        value = Dense(512, activation='relu')(net)
        value = Dense(1)(value)
        # now to combine the two streams
        advt = Lambda(lambda advt: advt - tf.reduce_mean(advt, axis=-1, keepdims=True))(advt)
        value = Lambda(lambda value: tf.tile(value, [1, self.num_actions]))(value)
        final = Add()([value, advt])
        model = Model(inputs=inputs, outputs=final)

        model.compile(loss='mse', optimizer=RMSprop(lr=self.learning_rate, decay=0.95, epsilon=1.5e-7))
        return model