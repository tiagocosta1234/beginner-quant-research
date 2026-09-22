import re

with open('broker_hacker\\ManualCustomBot.cs', 'r') as f:
    code = f.read()

old_logic = '''            bool is5BarDownAnomaly = true;
            bool is5BarUpAnomaly = true;

            for (int i = 0; i < 5; i++)
            {
                if (Close[i] >= Open[i]) is5BarDownAnomaly = false;
                if (Close[i] <= Open[i]) is5BarUpAnomaly = false;
            }'''

new_logic = '''            bool fiveBull = true;
            bool fiveBear = true;
            for (int i = 1; i <= 5; i++)
            {
                if (Close[i] <= Open[i]) fiveBull = false;
                if (Close[i] >= Open[i]) fiveBear = false;
            }

            bool is5BarDownAnomaly = fiveBear && Close[0] > Open[0]; // 5 red, 1 green
            bool is5BarUpAnomaly = fiveBull && Close[0] < Open[0]; // 5 green, 1 red'''

code = code.replace(old_logic, new_logic)

old_exec = '''            if (is5BarDownAnomaly)
            {
                SetStopLoss(CalculationMode.Ticks, (int)Math.Round(StopLossPoints / TickSize));
                SetProfitTarget(CalculationMode.Ticks, (int)Math.Round(TakeProfitPoints / TickSize));
                
                if (UsePullbackEntry)
                {
                    double limitPrice = Close[0] + (StopLossPoints / 2);
                    EnterShortLimit(dynamicContracts, limitPrice, "5_Bar_Anomaly_Short");
                }
                else
                {
                    EnterShort(dynamicContracts, "5_Bar_Anomaly_Short");
                }
            }
            else if (is5BarUpAnomaly)
            {
                SetStopLoss(CalculationMode.Ticks, (int)Math.Round(StopLossPoints / TickSize));
                SetProfitTarget(CalculationMode.Ticks, (int)Math.Round(TakeProfitPoints / TickSize));
                
                if (UsePullbackEntry)
                {
                    double limitPrice = Close[0] - (StopLossPoints / 2);
                    EnterLongLimit(dynamicContracts, limitPrice, "5_Bar_Anomaly_Long");
                }
                else
                {
                    EnterLong(dynamicContracts, "5_Bar_Anomaly_Long");
                }
            }'''

new_exec = '''            if (is5BarUpAnomaly) // 5 green, 1 red -> SHORT
            {
                SetStopLoss(CalculationMode.Ticks, (int)Math.Round(StopLossPoints / TickSize));
                SetProfitTarget(CalculationMode.Ticks, (int)Math.Round(TakeProfitPoints / TickSize));
                
                if (UsePullbackEntry)
                {
                    double limitPrice = Close[0] + (StopLossPoints / 2);
                    EnterShortLimit(dynamicContracts, limitPrice, "5_Bar_Anomaly_Short");
                }
                else
                {
                    EnterShort(dynamicContracts, "5_Bar_Anomaly_Short");
                }
            }
            else if (is5BarDownAnomaly) // 5 red, 1 green -> LONG
            {
                SetStopLoss(CalculationMode.Ticks, (int)Math.Round(StopLossPoints / TickSize));
                SetProfitTarget(CalculationMode.Ticks, (int)Math.Round(TakeProfitPoints / TickSize));
                
                if (UsePullbackEntry)
                {
                    double limitPrice = Close[0] - (StopLossPoints / 2);
                    EnterLongLimit(dynamicContracts, limitPrice, "5_Bar_Anomaly_Long");
                }
                else
                {
                    EnterLong(dynamicContracts, "5_Bar_Anomaly_Long");
                }
            }'''

code = code.replace(old_exec, new_exec)

with open('broker_hacker\\ManualCustomBot.cs', 'w') as f:
    f.write(code)
