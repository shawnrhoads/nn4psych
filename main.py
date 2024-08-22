# code to run model
# Ganesh, Adam

#%%
import jax
import jax.numpy as jnp
import numpy as np
import optax
import matplotlib.pyplot as plt
from jax import grad, jit, vmap, random
from jax.nn import softmax, relu, tanh
from jax.nn.initializers import glorot_uniform, normal
from copy import deepcopy

# Define constants
num_trials = 1000
num_contexts = 3
num_actions = 2
hidden_units = 64
gamma = 0.95

# Define reward probabilities for each context and each arm
reward_probs = jnp.array([
    [0.9, 0.1],  # Context 1
    [0.2, 0.8],  # Context 2
    [0.6, 0.4],  # Context 3
])

# Initialize model parameters
def initialize_params(key):
    k1, k2, k3, k4 = jax.random.split(key, 4)
    Wxh =random.normal(k1, (3, hidden_units)) /jnp.sqrt(hidden_units)
    Whh = random.normal(k2, (hidden_units, hidden_units)) /jnp.sqrt(hidden_units)
    Wha = random.normal(k3, (hidden_units, num_actions)) *1e-3
    Whc = random.normal(k4, (hidden_units, 1)) * 1e-3
    return Wxh, Whh, Wha, Whc

params = initialize_params(jax.random.PRNGKey(0))
initparams = deepcopy(params)

# Recurrent Neural Network forward pass
def rnn_forward(params, inputs, h):
    Wxh, Whh, Wha, Whc = params
    h = tanh(jnp.dot(inputs, Wxh) + jnp.dot(h, Whh))
    return h

# Define policy (actor) and value (critic) functions
def policy_and_value(params, h):
    Wxh, Whh, Wha, Whc = params
    policy = jnp.dot(h, Wha)
    value = jnp.dot(h, Whc) # Critic
    policy_prob = softmax(policy)  # Actor
    return policy_prob, value

def get_onehot_action(policy_prob):
    A = np.random.choice(a=np.arange(num_actions), p=np.array(policy_prob))
    onehotg = np.zeros(num_actions)
    onehotg[A] = 1
    return onehotg

def np_softmax(x):
    e_x = np.exp(x - np.max(x))  # Subtract max(x) for numerical stability
    return e_x / e_x.sum(axis=-1, keepdims=True)

# Loss function
def loss_fn(params, inputs, pasth, action, reward, next_value):
    h = rnn_forward(params, inputs, pasth)
    policy_prob, value = policy_and_value(params, h)

    td_errors = reward + gamma * next_value - value
    policy_losses = -jnp.log(policy_prob) * action * td_errors

    value_losses = td_errors ** 2
    loss = jnp.mean(policy_losses) + 0.5 * jnp.mean(value_losses)
    return loss

def moving_average(signal, window_size):
    # Pad the signal to handle edges properly
    padded_signal = np.pad(signal, (window_size//2, window_size//2), mode='edge')
    
    # Apply the moving average filter
    weights = np.ones(window_size) / window_size
    smoothed_signal = np.convolve(padded_signal, weights, mode='valid')
    
    return smoothed_signal


# Optimizer
optimizer = optax.adam(1e-3)

# Training loop
def train(params, context, reward_prob):
    
    past_h = random.normal(jax.random.PRNGKey(0), (hidden_units,))*0.1
    opt_state = optimizer.init(params)

    loss_history = []
    reward_history = []
    inputs = np.zeros_like(context)

    for trial in range(num_trials):

        policy, _ = policy_and_value(params, past_h)
        action = get_onehot_action(policy)

        rprob = reward_prob[np.argmax(action)]
        reward = np.random.choice([0, 1], p=np_softmax([1 - rprob, rprob]))

        h = rnn_forward(params, inputs, past_h)
        _, next_value = policy_and_value(params, h)

        loss, grads = jax.value_and_grad(loss_fn)(params, inputs, past_h,action, reward, next_value)
        
        updates, opt_state = optimizer.update(grads, opt_state, params)
        params = optax.apply_updates(params, updates)

        # print(trial, inputs, past_h, policy, action, reward, h, next_value, loss, grads)
        # print(loss, grads[3])
        past_h = h

        loss_history.append(loss)
        reward_history.append(reward)

        print(trial, np.round(policy,1), reward,loss, grads[1][0,0])

    return params, loss_history, reward_history

# Generate synthetic data (context, action, reward tuples)
np.random.seed(0)
context = np.eye(num_contexts)[0]
reward_prob = reward_probs[0]

# Train the model
params, loss_history, reward_history = train(params, context, reward_prob)

#%%
# Plot the reward over trials
f,ax = plt.subplots(2,2)
ax[0,0].plot(moving_average(reward_history, window_size=int(num_trials*0.1)), label='MA Reward')
ax[0,0].set_xlabel('Trial')
ax[0,0].set_ylabel('Reward')
ax[0,0].set_title('Reward over Trials')

ax[0,1].plot(loss_history, label='TD error', color='tab:orange')
ax[0,1].set_xlabel('Trial')
ax[0,1].set_ylabel('Loss')
ax[0,1].set_title('Actor-Critic Loss over Trials')


im = ax[1,0].imshow(params[2].T,aspect='auto')
plt.colorbar(im,ax=ax[1,0])
ax[1,0].set_xlabel('Action')
ax[1,0].set_ylabel('Hidden units')

ax[1,1].plot(params[3])
ax[1,1].set_xlabel('Hidden units')
ax[1,1].set_ylabel('Value')
f.tight_layout()
# %%
