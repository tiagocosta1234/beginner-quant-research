import os
import glob
import gc
from sb3_contrib import RecurrentPPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
import multiprocessing
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback, CallbackList
from typing import Callable

def linear_schedule(initial_value: float) -> Callable[[float], float]:
    """
    Linear learning rate schedule.
    :param initial_value: Initial learning rate.
    :return: schedule that computes current learning rate depending on remaining progress
    """
    def func(progress_remaining: float) -> float:
        # progress_remaining starts at 1.0 and decays to 0.0
        return progress_remaining * (initial_value - 0.00001) + 0.00001
    return func

from data_engine import load_ninjatrader_csv, engineer_features
from trading_env import TradingEnv

def make_env(data_file, rank, seed=0):
    """
    Utility function for multiprocessed env. 
    Each subprocess loads its own DataFrame independently to avoid massive RAM pickling spikes on Windows.
    """
    def _init():
        df_raw = load_ninjatrader_csv(data_file)
        df_engineered = engineer_features(df_raw)
        
        # FAST TRAINING: Slice first 2 weeks (~20,160 ticks)
        df_engineered = df_engineered.head(20160)
        
        env = TradingEnv(df=df_engineered)
        env.reset(seed=seed + rank)
        return env
    return _init

class SaveAlertCallback(BaseCallback):
    """Custom callback to aggressively overwrite the Master Model every X ticks."""
    def __init__(self, save_freq: int, model_path: str, norm_path: str, env: VecNormalize, verbose=1):
        super(SaveAlertCallback, self).__init__(verbose)
        self.save_freq = save_freq
        self.model_path = model_path
        self.norm_path = norm_path
        self.venv_to_save = env

    def _on_step(self) -> bool:
        if self.n_calls > 0 and self.n_calls % self.save_freq == 0:
            self.model.save(self.model_path)
            self.venv_to_save.save(self.norm_path)
            print(f"\n🚨 [ALERT] Reached {self.n_calls:,} ticks! Master Model successfully overwritten & saved to disk! 🚨\n")
        return True

def run_training():
    print("--- ⚡ Booting FAST Multi-Contract Continual Learning Pipeline ⚡ ---")
    
    # 1. Data Ingestion: ONLY scan raw_exports to avoid contaminating the test sample (06-25)
    potential_files = [os.path.join('raw_exports', 'MNQ 06-26.Last.txt')]
    
    # Deduplicate and sort
    potential_files = sorted(list(set(potential_files)))
    
    if not potential_files:
        print("❌ Fatal: No 'MNQ' tick data files found in the current directory or raw_exports/.")
        return
        
    print(f"📂 Found {len(potential_files)} contract files. Initiating sequential training loop.")
    
    save_path = r"ai_research\ppo_mnq_sniper"
    norm_path = r"ai_research\vec_normalize_sniper.pkl"
    model_file = save_path + ".zip"
    
    for file_idx, data_file in enumerate(potential_files):
        print(f"\n==================================================")
        print(f"🔄 [{file_idx+1}/{len(potential_files)}] Ingesting market data from: {data_file}")
        print(f"==================================================")
        
        df_raw = load_ninjatrader_csv(data_file)
        if df_raw.empty:
            print(f"❌ Failed to parse {data_file}. Skipping...")
            continue
            
        print(f"Loaded {len(df_raw)} raw ticks. Engineering features...")
        df_engineered = engineer_features(df_raw)
        
        # FAST TRAINING: Slice first 2 weeks
        df_engineered = df_engineered.head(20160)
        total_rows = len(df_engineered)
        print(f"Dataset sliced to {total_rows:,} rows (First 2 Weeks).")
            
        final_rows = len(df_engineered)
            
        print("\n--- 🏟️ Initializing Parallel Trading Environments ---")
        num_cpus = max(1, multiprocessing.cpu_count() - 2)
        print(f"⚡ Spawning {num_cpus} parallel universes across your CPU cores...")
        
        env_fns = [make_env(data_file, i) for i in range(num_cpus)]
        env = SubprocVecEnv(env_fns)
        
        if os.path.exists(model_file) and os.path.exists(norm_path):
            print(f"\n♻️ Existing Master Model found! Loading weights and scaler for Continual Learning...")
            env = VecNormalize.load(norm_path, env)
            env.training = True
            model = RecurrentPPO.load(model_file, env=env)
            model.learning_rate = 0.0001
        else:
            print("\n--- 🤖 Spawning Fresh Recurrent PPO Agent (MlpLstmPolicy) ---")
            env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.)
            model = RecurrentPPO(
                "MlpLstmPolicy", 
                env, 
                learning_rate=0.0003, 
                n_steps=2048,      # Reduced from 4096 (faster turnaround)
                batch_size=1024,   # Increased from 256 (vectorized CPU math)
                n_epochs=3,        # Reduced from 10 (cuts math time by 70%)
                gamma=0.999, 
                gae_lambda=0.95, 
                clip_range=0.2, 
                ent_coef=0.01, 
                verbose=1, 
                tensorboard_log="./ppo_tensorboard/"
            )
            
        # Callbacks (Overwrite Master Model and Alert every 20k for fast train)
        alert_callback = SaveAlertCallback(
            save_freq=20000, 
            model_path=model_file, 
            norm_path=norm_path, 
            env=env
        )
        callback = CallbackList([alert_callback])
            
        # FAST TRAINING: 100,000 Timesteps (10x faster than 1M)
        print(f"\n🚀 Commencing FAST 100,000 Timestep Run on {data_file}...")
        model.learn(total_timesteps=100000, callback=callback, progress_bar=True)
        
        # Save the Alpha
        print(f"\n💾 Training Complete for {data_file}. Saving Master Model...")
        model.save(save_path)
        env.save(norm_path)
        
        # CRITICAL: Memory Management
        print(f"🧹 Wiping RAM to prepare for the next contract...")
        del df_raw
        del df_engineered
        del env
        del model
        gc.collect()

    print("\n✅ FAST Multi-Contract Continual Learning Loop Finished Successfully!")

if __name__ == "__main__":
    run_training()
