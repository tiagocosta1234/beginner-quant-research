import os
import gc
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from data_engine import load_ninjatrader_csv, engineer_features
from trading_env import TradingEnv
from train_ppo import linear_schedule

def test_dry_run():
    print("--- 🧪 1,000 Step Dry Run (Elite Pass) ---")
    data_file = "raw_exports/MNQ_2025_Q3.txt"
    if not os.path.exists(data_file):
        data_file = "MNQ_2025_Q3.txt"
    
    if not os.path.exists(data_file):
        print("❌ Fatal: No MNQ 1-Minute data files found in the current directory or raw_exports.")
        return
        
    df_raw = load_ninjatrader_csv(data_file)
    print(f"Loaded {len(df_raw)} raw minutes. Engineering features...")
    df_engineered = engineer_features(df_raw).head(50000)
    
    env = DummyVecEnv([lambda: TradingEnv(df=df_engineered)])
    env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.)
    
    model = PPO('MlpPolicy', env, ent_coef=0.05, learning_rate=linear_schedule(0.0003), batch_size=1024, n_steps=4096, verbose=1)
    
    model.learn(total_timesteps=5000) # Ensure it takes at least one update step (n_steps=4096)
    
    print("✅ Dry run completed successfully! Engine is stable.")

if __name__ == "__main__":
    test_dry_run()
