import sys
with open('3_5_year_results.txt', 'r', encoding='utf-16') as f:
    content = f.read()

blocks = content.split('=== GC Backtest:')
for block in blocks[1:]:
    title = block.split('===')[0].strip()
    if '15-Minute' in title: continue
    
    trades = [l for l in block.split('\n') if l.startswith('2026')]
    wins = 0; losses = 0; pnl = 0.0
    for t in trades:
        parts = t.split('|')
        if len(parts) > 6:
            val = float(parts[-1].replace('$', '').replace(',', '').strip())
            pnl += val
            if 'WIN' in parts[-2]: wins += 1
            else: losses += 1
    total = wins + losses
    wr = (wins/total*100) if total > 0 else 0
    print(f'{title}:')
    print(f'  Trades in 2026: {total}')
    print(f'  Wins/Losses: {wins}/{losses} ({wr:.1f}%)')
    print(f'  Net Profit: ${pnl:.2f}')
