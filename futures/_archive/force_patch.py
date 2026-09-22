import re

file_path = r'broker_hacker\ManualCustomBot.cs'
with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

# Replace the entry calculation block using regex to avoid whitespace issues
pattern = r'bool fiveBull.*?is5BarUpAnomaly = fiveBull && Close\[0\] < Open\[0\]; // 5 green, 1 red'
replacement = '''            // STRICT TIME OF DAY FILTER (09:30 AM to 4:00 PM EST)
            int time = ToTime(Time[0]);
            if (time < 93000 || time >= 160000) return;

            bool is5BarDownAnomaly = true;
            bool is5BarUpAnomaly = true;

            // MOMENTUM INVERSION: Ride the trend, do not fade it.
            for (int i = 0; i < 5; i++)
            {
                if (Close[i] >= Open[i]) is5BarDownAnomaly = false; // If any bar is green, it's not 5 red
                if (Close[i] <= Open[i]) is5BarUpAnomaly = false;   // If any bar is red, it's not 5 green
            }'''
code = re.sub(pattern, replacement, code, flags=re.DOTALL)

# Replace the execution block using regex
exec_pattern = r'if \(is5BarUpAnomaly\) // 5 green, 1 red -> SHORT.*?EnterLong\(dynamicContracts, "5_Bar_Anomaly_Long"\);\s*\}\s*\}'
exec_replacement = '''if (is5BarUpAnomaly) // 5 Green -> LONG (Riding Momentum)
            {
                SetStopLoss(CalculationMode.Ticks, (int)Math.Round(TargetPoints / TickSize));
                SetProfitTarget(CalculationMode.Ticks, (int)Math.Round(TargetPoints / TickSize));
                
                if (UsePullbackEntry)
                {
                    double limitPrice = Close[0] - (TargetPoints / 2);
                    EnterLongLimit(dynamicContracts, limitPrice, "5_Bar_Anomaly_Long");
                }
                else
                {
                    EnterLong(dynamicContracts, "5_Bar_Anomaly_Long");
                }
            }
            else if (is5BarDownAnomaly) // 5 Red -> SHORT (Riding Momentum)
            {
                SetStopLoss(CalculationMode.Ticks, (int)Math.Round(TargetPoints / TickSize));
                SetProfitTarget(CalculationMode.Ticks, (int)Math.Round(TargetPoints / TickSize));
                
                if (UsePullbackEntry)
                {
                    double limitPrice = Close[0] + (TargetPoints / 2);
                    EnterShortLimit(dynamicContracts, limitPrice, "5_Bar_Anomaly_Short");
                }
                else
                {
                    EnterShort(dynamicContracts, "5_Bar_Anomaly_Short");
                }
            }'''
code = re.sub(exec_pattern, exec_replacement, code, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(code)

with open(r'C:\Users\author\Documents\NinjaTrader 8\bin\Custom\Strategies\ManualCustomBot.cs', 'w', encoding='utf-8') as f:
    f.write(code)

print("SUCCESSFULLY PATCHED USING REGEX")
