import torch
from sb3_contrib import RecurrentPPO
import numpy as np

def export_onnx():
    model_path = r"ai_research\ppo_mnq_sniper.zip"
    onnx_path = r"ai_research\AI_Trading_Bot\ppo_mnq_sniper.onnx"
    
    print("Loading model...")
    model = RecurrentPPO.load(model_path, device='cpu')
    policy = model.policy
    
    # LSTM shapes
    # sb3_contrib RecurrentPPO uses a single LSTM layer usually.
    # We can inspect the policy to see the shapes.
    dummy_obs = torch.zeros(1, 1, 23) # (batch, seq, features) or (seq, batch, features)?
    
    # Let's just print the policy architecture to understand it.
    print(policy)

if __name__ == "__main__":
    export_onnx()
