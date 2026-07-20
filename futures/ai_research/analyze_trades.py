import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def analyze_trades():
    csv_path = r"ai_research\AI_Trading_Bot\full_backtest_trades.csv"
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return
        
    df = pd.read_csv(csv_path)
    
    # 1. Verify Reality of the Math
    # In trading_env.py: point_value = 2.0, commission = 1.20, slippage = 0.50
    # Net PNL = Gross PNL - Commission - Slippage
    
    df['direction_mult'] = df['direction'].apply(lambda x: 1 if x == 'Long' else -1)
    df['points_captured'] = (df['exit_price'] - df['entry_price']) * df['direction_mult']
    df['gross_pnl'] = df['points_captured'] * 2.00 * df['size']
    df['commission_paid'] = (1.20 + 0.50) * df['size'] # $1.70 per contract closed
    df['recalculated_net_pnl'] = df['gross_pnl'] - df['commission_paid']
    
    # Check if recalculated matches the environment's stated PNL
    pnl_diff = np.abs(df['recalculated_net_pnl'] - df['pnl']).sum()
    print(f"Total Discrepancy between Environment PNL and Recalculated PNL: ${pnl_diff:.2f}")
    
    # 2. Build Statistics
    total_trades = len(df)
    total_net = df['recalculated_net_pnl'].sum()
    win_rate = len(df[df['recalculated_net_pnl'] > 0]) / total_trades * 100
    
    df['cumulative_pnl'] = df['recalculated_net_pnl'].cumsum() + 50000
    df['peak'] = df['cumulative_pnl'].cummax()
    df['drawdown'] = df['peak'] - df['cumulative_pnl']
    max_drawdown = df['drawdown'].max()
    
    print(f"Verified Net Profit: ${total_net:.2f}")
    print(f"Verified Max Drawdown: ${max_drawdown:.2f}")
    
    # 3. Generate Graphs
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('V7 AI Sniper - Realistic Trade Analysis (Commissions & Slippage Included)', fontsize=16, color='white')
    
    # A. Equity Curve
    ax1 = axes[0, 0]
    ax1.plot(df.index, df['cumulative_pnl'], color='#00ffcc', linewidth=2)
    ax1.fill_between(df.index, 50000, df['cumulative_pnl'], where=(df['cumulative_pnl'] >= 50000), color='#00ffcc', alpha=0.1)
    ax1.fill_between(df.index, 50000, df['cumulative_pnl'], where=(df['cumulative_pnl'] < 50000), color='#ff3333', alpha=0.1)
    ax1.axhline(50000, color='gray', linestyle='--', alpha=0.5)
    ax1.set_title('Verified Equity Curve ($)')
    ax1.set_xlabel('Trade Number')
    ax1.set_ylabel('Account Balance ($)')
    ax1.grid(alpha=0.2)
    
    # B. Drawdown Curve
    ax2 = axes[0, 1]
    ax2.plot(df.index, -df['drawdown'], color='#ff3333', linewidth=1.5)
    ax2.fill_between(df.index, -df['drawdown'], 0, color='#ff3333', alpha=0.3)
    ax2.set_title('Drawdown Profile ($)')
    ax2.set_xlabel('Trade Number')
    ax2.set_ylabel('Drawdown from Peak ($)')
    ax2.grid(alpha=0.2)
    
    # C. Trade PNL Distribution
    ax3 = axes[1, 0]
    ax3.hist(df['recalculated_net_pnl'], bins=50, color='#bb86fc', alpha=0.7)
    ax3.axvline(0, color='white', linestyle='--', linewidth=1)
    ax3.set_title('Distribution of Net PNL per Trade')
    ax3.set_xlabel('Net Profit/Loss ($)')
    ax3.grid(alpha=0.2)
    
    # D. Duration vs PNL
    ax4 = axes[1, 1]
    df['duration_mins'] = pd.to_timedelta(df['duration']).dt.total_seconds() / 60.0
    colors = ['#00ffcc' if pnl > 0 else '#ff3333' for pnl in df['recalculated_net_pnl']]
    ax4.scatter(df['duration_mins'], df['recalculated_net_pnl'], c=colors, alpha=0.5, s=20)
    ax4.axhline(0, color='white', linestyle='--', linewidth=1)
    ax4.set_title('Trade Duration vs PNL')
    ax4.set_xlabel('Hold Time (Minutes)')
    ax4.set_ylabel('Net PNL ($)')
    ax4.grid(alpha=0.2)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    # Save to artifacts directory
    save_path = r"C:\Users\author\.gemini\antigravity\brain\cceadb02-8bcc-471d-af28-3811ab1892a8\realistic_analysis.png"
    plt.savefig(save_path, dpi=300, facecolor=fig.get_facecolor(), transparent=False)
    print(f"Saved analytics graph to: {save_path}")

if __name__ == "__main__":
    analyze_trades()
