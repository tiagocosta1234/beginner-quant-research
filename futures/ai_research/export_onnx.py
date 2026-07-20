import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import json
import torch
import numpy as np
from sb3_contrib import RecurrentPPO
from stable_baselines3.common.vec_env import VecNormalize, DummyVecEnv
import gymnasium as gym
from gymnasium import spaces

class DummyEnv(gym.Env):
    def __init__(self):
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(23,), dtype=np.float32)
        self.action_space = spaces.Discrete(21)
    def step(self, action): return np.zeros(23), 0, False, False, {}
    def reset(self, seed=None, options=None): return np.zeros(23), {}

# To export ONNX for RecurrentPPO, we need a wrapper around the policy to handle the tuple inputs.
class OnnxableRecurrentPolicy(torch.nn.Module):
    def __init__(self, policy):
        super().__init__()
        self.policy = policy

    def forward(self, obs, lstm_states_pi_hidden, lstm_states_pi_cell):
        # In deployment, we run 1 tick at a time, so seq_len = 1.
        # SB3 LSTM uses batch_first=False by default: (seq_len, batch_size, input_dim)
        
        # 1. Extract features
        features = self.policy.extract_features(obs)
        
        # 2. Add sequence dimension: (1, batch_size, 23)
        features_seq = features.unsqueeze(0)
        
        # 3. Reconstruct LSTM tuple
        lstm_states_pi = (lstm_states_pi_hidden, lstm_states_pi_cell)
        
        # 4. Pass through LSTM
        lstm_out, lstm_states_pi_out = self.policy.lstm_actor(features_seq, lstm_states_pi)
        
        # 5. Remove sequence dimension: (batch_size, 256)
        latent_pi = lstm_out.squeeze(0)
        
        # 6. Pass through MLP Extractor
        latent_pi = self.policy.mlp_extractor.forward_actor(latent_pi)
        
        # 7. Action Logits
        logits = self.policy.action_net(latent_pi)
        action = torch.argmax(logits, dim=1)
        
        return action, lstm_states_pi_out[0], lstm_states_pi_out[1]

def export_model_and_stats():
    model_path = r"ai_research\ppo_mnq_sniper.zip"
    norm_path = r"ai_research\vec_normalize_sniper.pkl"
    
    print("Loading VecNormalize...")
    venv = DummyVecEnv([lambda: DummyEnv()])
    vec_env = VecNormalize.load(norm_path, venv)
    
    mean = vec_env.obs_rms.mean.tolist()
    var = vec_env.obs_rms.var.tolist()
    epsilon = vec_env.epsilon
    
    norm_stats = {
        "mean": mean,
        "var": var,
        "epsilon": epsilon
    }
    
    with open("norm_stats.json", "w") as f:
        json.dump(norm_stats, f, indent=4)
        
    print("Exported norm_stats.json")
    
    print("Loading PyTorch model...")
    model = RecurrentPPO.load(model_path, device='cpu')
    onnxable_policy = OnnxableRecurrentPolicy(model.policy)
    
    # Create dummy inputs for ONNX trace
    # obs: (batch_size, features) -> (1, 23)
    dummy_obs = torch.zeros(1, 23)
    
    # lstm_states: hidden and cell, shape (n_layers, batch_size, hidden_dim) -> (1, 1, 256)
    dummy_hidden = torch.zeros(1, 1, 256)
    dummy_cell = torch.zeros(1, 1, 256)
    
    print("Tracing to ONNX...")
    torch.onnx.export(
        onnxable_policy,
        (dummy_obs, dummy_hidden, dummy_cell),
        "ppo_mnq_sniper.onnx",
        opset_version=14,
        input_names=["obs", "lstm_hidden", "lstm_cell"],
        output_names=["action", "lstm_hidden_out", "lstm_cell_out"],
        dynamic_axes={
            "obs": {0: "batch_size"},
            "lstm_hidden": {1: "batch_size"},
            "lstm_cell": {1: "batch_size"},
            "action": {0: "batch_size"},
            "lstm_hidden_out": {1: "batch_size"},
            "lstm_cell_out": {1: "batch_size"},
        }
    )
    
    # Downgrade IR Version for NinjaTrader 8 Compatibility
    import onnx
    onnx_model = onnx.load("ppo_mnq_sniper.onnx")
    onnx_model.ir_version = 9
    onnx.save(onnx_model, "ppo_mnq_sniper.onnx")
    
    print("Successfully exported ppo_mnq_sniper.onnx (IR Version 9)")

if __name__ == "__main__":
    export_model_and_stats()
