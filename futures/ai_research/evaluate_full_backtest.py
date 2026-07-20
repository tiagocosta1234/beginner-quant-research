import os
import glob
import pandas as pd
import numpy as np
import pickle
import torch
from tqdm import tqdm
from sb3_contrib import RecurrentPPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from data_engine import load_ninjatrader_csv, engineer_features
from trading_env import TradingEnv

# Force PyTorch to use a single core to prevent CPU thread thrashing on batch_size=1
torch.set_num_threads(1)

def evaluate_full_backtest():
    print("--- Booting Full History Institutional Backtester ---")
    
    import glob
    import random
    # 1. Data Ingestion
    potential_files = glob.glob(os.path.join('raw_exports', 'MNQ *.txt'))
    if os.path.exists('MNQ 06-25.Last.txt'):
        potential_files.append('MNQ 06-25.Last.txt')
    
    if not potential_files:
        print(" Fatal: No 'MNQ' 1-Minute data files found.")
        return
        
    print(f" Ingesting {len(potential_files)} contract files chronologically...")
    
    df_list = []
    potential_files.sort()
    
    for data_file in potential_files:
        df_raw = load_ninjatrader_csv(data_file)
        if not df_raw.empty:
            df_list.append(df_raw)
            
    if not df_list:
        print(" Failed to parse any market data.")
        return
        
    df_combined = pd.concat(df_list)
    df_combined = df_combined[~df_combined.index.duplicated(keep='last')].sort_index()
    
    print(f"Stitched {len(df_combined)} raw minutes across all files. Engineering features...")
    df_engineered = engineer_features(df_combined)
    
    first_date = df_engineered.index[0]
    last_date = df_engineered.index[-1]
    
    max_start_date = last_date - pd.Timedelta(days=30)
    
    if max_start_date > first_date:
        valid_start_dates = df_engineered[df_engineered.index <= max_start_date].index
        random_start_date = random.choice(valid_start_dates)
        end_date = random_start_date + pd.Timedelta(days=30)
        df_engineered = df_engineered[(df_engineered.index >= random_start_date) & (df_engineered.index <= end_date)].copy()
    else:
        random_start_date = first_date
        end_date = last_date
        
    print(f" Total Backtest Range (RANDOM 30 DAYS): {random_start_date} to {end_date}")
    
    # Model Loading
    model_path = r"ai_research\ppo_mnq_sniper.zip"
    norm_path = r"ai_research\vec_normalize_sniper.pkl"
    checkpoint_file = r"ai_research\backtest_checkpoint.pkl"
    
    if not os.path.exists(model_path):
        print(f" Model file not found at: {model_path}")
        return
        
    print(f"\n---  Loading Trained Recurrent PPO Agent (LSTM) ---")
    model = RecurrentPPO.load(model_path)
    
    env = DummyVecEnv([lambda: TradingEnv(df=df_engineered, continuous_eval=True)])
    if os.path.exists(norm_path):
        env = VecNormalize.load(norm_path, env)
        env.training = False
        env.norm_reward = False
        
    # Safely extract the raw TradingEnv object
    base_venv = env.venv if hasattr(env, 'venv') else env
    raw_env = base_venv.envs[0]
        
    STARTING_BALANCE = 50000.0
    
    # Checkpoint Logic
    if os.path.exists(checkpoint_file):
        print("\n Found existing backtest checkpoint! Resuming progress...")
        with open(checkpoint_file, 'rb') as f:
            chk = pickle.load(f)
            
        current_balance = chk['current_balance']
        high_water_mark = chk['high_water_mark']
        overall_max_runup = chk['overall_max_runup']
        overall_max_drawdown = chk['overall_max_drawdown']
        lstm_states = chk['lstm_states']
        episode_starts = chk['episode_starts']
        
        # Force env to reset to initialize baseline values
        env.reset()
        
        # Inject Checkpoint State into raw environment
        raw_env.current_step = chk['current_step']
        raw_env.position = chk['position']
        raw_env.entry_price = chk['entry_price']
        raw_env.entry_time = chk['entry_time']
        raw_env.flat_steps = chk['flat_steps']
        raw_env.ticks_in_trade = chk['ticks_in_trade']
        raw_env.peak_trade_points = chk['peak_trade_points']
        raw_env.stop_loss_points = chk['stop_loss_points']
        raw_env.trade_history = chk['trade_history']
        raw_env.last_time = chk['last_time']
        raw_env.daily_pnl = chk['daily_pnl']
        raw_env.is_daily_paused = chk['is_daily_paused']
        raw_env.current_balance = chk['env_current_balance']
        raw_env.high_water_mark = chk['env_high_water_mark']
        
        # Regenerate observation array for the exact resumed minute
        obs_raw = raw_env._get_observation()
        obs = np.array([obs_raw])
        if hasattr(env, 'normalize_obs'):
            obs = env.normalize_obs(obs)
            
        start_tick = raw_env.current_step
    else:
        obs = env.reset()
        current_balance = STARTING_BALANCE
        high_water_mark = STARTING_BALANCE
        overall_max_drawdown = 0.0
        overall_max_runup = STARTING_BALANCE
        lstm_states = None
        episode_starts = np.ones((env.num_envs,), dtype=bool)
        start_tick = 0
    
    print(f"\n Commencing Tick-by-Tick Institutional Backtest from tick {start_tick}...\n")
    
    pbar = tqdm(total=len(df_engineered), initial=start_tick, desc="Simulating Ticks", unit="tick", mininterval=1.0, miniters=1000)
    
    while True:
        action, lstm_states = model.predict(obs, state=lstm_states, episode_start=episode_starts, deterministic=True)
        obs, rewards, dones, infos = env.step(action)
        episode_starts = dones
        pbar.update(1)
        
        current_balance = infos[0].get('unrealized_balance', current_balance)
        high_water_mark = infos[0].get('high_water_mark', high_water_mark)
        
        if current_balance > overall_max_runup:
            overall_max_runup = current_balance
            
        drawdown = high_water_mark - current_balance
        if drawdown > overall_max_drawdown:
            overall_max_drawdown = drawdown
            
        # Save Checkpoint every 5,000 ticks (approx every 30 seconds of processing)
        if raw_env.current_step % 5000 == 0:
            chk = {
                'current_step': raw_env.current_step,
                'current_balance': current_balance,
                'high_water_mark': high_water_mark,
                'overall_max_runup': overall_max_runup,
                'overall_max_drawdown': overall_max_drawdown,
                'position': raw_env.position,
                'entry_price': raw_env.entry_price,
                'entry_time': raw_env.entry_time,
                'flat_steps': raw_env.flat_steps,
                'ticks_in_trade': raw_env.ticks_in_trade,
                'peak_trade_points': raw_env.peak_trade_points,
                'stop_loss_points': raw_env.stop_loss_points,
                'trade_history': raw_env.trade_history,
                'last_time': raw_env.last_time,
                'daily_pnl': raw_env.daily_pnl,
                'is_daily_paused': raw_env.is_daily_paused,
                'env_current_balance': raw_env.current_balance,
                'env_high_water_mark': raw_env.high_water_mark,
                'lstm_states': lstm_states,
                'episode_starts': episode_starts
            }
            with open(checkpoint_file, 'wb') as f:
                pickle.dump(chk, f)
            tqdm.write(f" Checkpoint Saved at Tick {raw_env.current_step}...")
            
        if dones[0]:
            terminal_info = infos[0].get("terminal_info", infos[0])
            master_trade_list = terminal_info.get('trade_history', [])
            break
            
    pbar.close()
    
    # Backtest Complete -> Wipe Checkpoint so next run starts fresh
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
            
    final_net_profit = current_balance - STARTING_BALANCE
    total_days = (df_engineered.index[-1] - df_engineered.index[0]).days
    
    print("\n=============================================")
    print("       FULL HISTORY BACKTEST DASHBOARD")
    print("=============================================")
    print(f" Time in Market       : {total_days} Days")
    print(f" Starting Equity      : ${STARTING_BALANCE:,.2f}")
    print(f" Final Equity         : ${current_balance:,.2f}")
    print(f" Total Net Profit     : ${final_net_profit:,.2f}")
    print(f" Peak Equity (Run-up) : ${overall_max_runup:,.2f}")
    print(f" Maximum Drawdown     : ${overall_max_drawdown:,.2f}")
    
    if master_trade_list:
        df_trades = pd.DataFrame(master_trade_list)
        df_trades['entry_time'] = pd.to_datetime(df_trades['entry_time'])
        df_trades['exit_time'] = pd.to_datetime(df_trades['exit_time'])
        df_trades['duration'] = df_trades['exit_time'] - df_trades['entry_time']
        
        total_trades = len(df_trades)
        total_contracts = df_trades['size'].sum()
        
        avg_trades_per_day = total_trades / total_days if total_days > 0 else total_trades
        avg_contracts_per_day = total_contracts / total_days if total_days > 0 else total_contracts
        
        avg_duration_mins = df_trades['duration'].mean().total_seconds() / 60.0
        
        winning_trades = df_trades[df_trades['pnl'] > 0]
        losing_trades = df_trades[df_trades['pnl'] <= 0]
        
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0.0
        
        avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0.0
        avg_loss = abs(losing_trades['pnl'].mean()) if not losing_trades.empty else 0.0
        rr_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
        profit_factor = winning_trades['pnl'].sum() / abs(losing_trades['pnl'].sum()) if abs(losing_trades['pnl'].sum()) > 0 else float('inf')
        
        print("---------------------------------------------")
        print(f" Total Trades Taken   : {total_trades}")
        print(f" Avg Trades/Day       : {avg_trades_per_day:.1f}")
        print(f" Avg Contracts/Day    : {avg_contracts_per_day:.1f}")
        print(f" Win Rate             : {win_rate:.1f}%")
        print(f" Profit Factor        : {profit_factor:.2f}")
        print(f" Avg Win              : ${avg_win:,.2f}")
        print(f" Avg Loss             : ${avg_loss:,.2f}")
        print(f" Avg Risk:Reward Ratio: 1 : {rr_ratio:.2f}")
        print(f" Avg Hold Time        : {avg_duration_mins:.1f} Minutes")
        
        df_trades.to_csv("full_backtest_trades.csv", index=False)
        print("=============================================\n")
        print(f" Saved {total_trades} executed trades to 'full_backtest_trades.csv'\n")
    else:
        print("---------------------------------------------")
        print(" Total Trades Taken   : 0")
        print("=============================================\n")

if __name__ == "__main__":
    evaluate_full_backtest()
