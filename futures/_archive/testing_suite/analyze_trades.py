import csv
import sys

def parse_currency(val):
    if not val: return 0.0
    val = val.replace('$', '').replace(',', '').strip()
    if val.startswith('(') and val.endswith(')'):
        return -float(val[1:-1])
    try:
        return float(val)
    except:
        return 0.0

def main():
    try:
        # User usually exports to AI_Trading_Bot or broker_hacker. Let's try AI_Trading_Bot first
        filepath = r'ai_research\AI_Trading_Bot\simulation_trades.csv'
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            trades = list(reader)
    except FileNotFoundError:
        print(f"{filepath} not found.")
        return

    wins = 0
    losses = 0
    total_profit = 0.0
    gross_win = 0.0
    gross_loss = 0.0

    for t in trades:
        profit = parse_currency(t.get('Profit', '0'))
        total_profit += profit
        if profit > 0:
            wins += 1
            gross_win += profit
        elif profit < 0:
            losses += 1
            gross_loss += profit
            
    total_trades = wins + losses
    if total_trades == 0:
        print("No trades found.")
        return

    win_rate = (wins / total_trades) * 100
    avg_win = gross_win / wins if wins > 0 else 0
    avg_loss = gross_loss / losses if losses > 0 else 0

    print(f"Total Trades: {total_trades}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total Net Profit: ${total_profit:.2f}")
    print(f"Average Win: ${avg_win:.2f}")
    print(f"Average Loss: ${avg_loss:.2f}")

if __name__ == "__main__":
    main()
