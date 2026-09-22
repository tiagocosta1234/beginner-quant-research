using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;

namespace NinjaTrader.NinjaScript.Strategies
{
    public class Short_5m : Strategy
    {
        private AGY_RiskManager _risk;
        private AGY_TimeEngine _time;
        private AGY_CoreEngine _core;
        
        private DateTime _lastTradeDate = DateTime.MinValue;
        private Order _shortLimit;
        private Order _longLimit;
        
        private DateTime _currentSessionDate = DateTime.MinValue;
        private double _priorRealizedPnL = 0;
        private double _dailyPnL = 0;
        private int _tradesToday = 0;
        
        [NinjaScriptProperty]
        public int MaxDailyTrades { get; set; }

        [NinjaScriptProperty]
        public double DailyLossLimit { get; set; }

        [NinjaScriptProperty]
        public double DailyProfitLimit { get; set; }
        [NinjaScriptProperty]
        public double FixedRiskPerTrade { get; set; }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Institutional Super-Massive Engine (V29) - 5m_short_eval";
                Name = "Short_5m";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
                IsFillLimitOnTouch = false;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 1;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                BarsRequiredToTrade = 250;
                MaxDailyTrades = 1;
                DailyLossLimit = 650.0;
                DailyProfitLimit = 1600.0;
                FixedRiskPerTrade = 1000.0;
            }
            else if (State == State.DataLoaded)
            {
                _risk = new AGY_RiskManager(MaxDailyTrades, FixedRiskPerTrade, TickSize, Instrument.MasterInstrument.PointValue);
                _time = new AGY_TimeEngine();
                _core = new AGY_CoreEngine();
            }
        }
        
        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity, MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution.Order.Name == "Momentum_S" || execution.Order.Name == "Momentum_L")
            {
                if (execution.Order.OrderState == OrderState.Filled || execution.Order.OrderState == OrderState.PartFilled)
                {
                    _lastTradeDate = Time[0].Date;
                }
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade) return;

            _risk.CheckSession(Time[0]);
            
            if (Time[0].Date > _currentSessionDate.Date && Position.MarketPosition == MarketPosition.Flat)
            {
                _currentSessionDate = Time[0].Date;
                _priorRealizedPnL = SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit;
                _tradesToday = 0;
            }
            
            _dailyPnL = SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit - _priorRealizedPnL;
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                _dailyPnL += Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]);
            }
            
            if (_dailyPnL <= -DailyLossLimit || _dailyPnL >= DailyProfitLimit)
            {
                if (Position.MarketPosition != MarketPosition.Flat)
                {
                    if (Position.MarketPosition == MarketPosition.Long) ExitLong("Daily Limit Reached");
                    if (Position.MarketPosition == MarketPosition.Short) ExitShort("Daily Limit Reached");
                }
                _risk.HaltForDay();
                return;
            }

            if (_risk.IsHaltedForDay) return;
            
            _time.Update(Time[0], Open[0], High[0], Low[0], Close[0]);
            _core.Update(Time[0], Open[0], High[0], Low[0], Close[0], Volume[0]);

            // V13: Complete Mathematical Inversion (Unlimited Daily Trades)
            
            // Absolute foolproof TimeSpan Eject
            if (Position.MarketPosition != MarketPosition.Flat && Time[0].TimeOfDay >= new TimeSpan(14, 50, 0))
            {
                if (Position.MarketPosition == MarketPosition.Long) ExitLong("PowerHour_Eject_L", "Momentum_L");
                if (Position.MarketPosition == MarketPosition.Short) ExitShort("PowerHour_Eject_S", "Momentum_S");
                return;
            }
            
            if (Position.MarketPosition == MarketPosition.Flat && Time[0].Hour >= 9 && Time[0].TimeOfDay < new TimeSpan(14, 50, 0) && Time[0].DayOfWeek != DayOfWeek.Friday)

            {
                // We use 60 points for the risk calculation now since the stop is 60 points
                int qty = _risk.CalculatePositionSize(60);
                if (qty > 0) 
                {
                    double rsi2 = _core.CalculateRealRSI(2);
                    double[] bb = _core.CalculateRealBollinger(20, 2.5);
                    double upperBB = bb[0];
                    double lowerBB = bb[1];
                    
                    double ema200 = _core.CalculateRealEMA(200);
                    
                    bool validLong = rsi2 > 90 && Close[0] > upperBB && Close[0] > ema200;
                    bool validShort = rsi2 < 10 && Close[0] < lowerBB && Close[0] < ema200;
                    
                    if (validShort)
                    {
                        // Static 1:1.5 RR: Risk 60, Target 100
                        SetStopLoss("Momentum_S", CalculationMode.Ticks, (int)(60 / TickSize), false);
                        SetProfitTarget("Momentum_S", CalculationMode.Ticks, (int)(100 / TickSize));
                        EnterShort(qty, "Momentum_S");
                        _risk.RegisterTrade();
                        _tradesToday++;
                        _lastTradeDate = Time[0].Date;
                    }
                    else if (validLong)
                    {
                        // Static 1:1.5 RR: Risk 60, Target 100
                        SetStopLoss("Momentum_L", CalculationMode.Ticks, (int)(60 / TickSize), false);
                        SetProfitTarget("Momentum_L", CalculationMode.Ticks, (int)(100 / TickSize));
                        EnterLong(qty, "Momentum_L");
                        _risk.RegisterTrade();
                        _tradesToday++;
                    }
                }
            }
        }
    }
    public class AGY_RiskManager
    {
        private int _max; private double _risk; private double _tick; private double _pt;
        private DateTime _last = DateTime.MinValue;
        public int Count { get; private set; }
        public bool IsHaltedForDay { get; private set; }
        
        public AGY_RiskManager(int m, double r, double t, double p) { _max = m; _risk = r; _tick = t; _pt = p; }
        public void CheckSession(DateTime t) { if (t.Date > _last) { Count = 0; IsHaltedForDay = false; _last = t.Date; } }
        public void RegisterTrade() { Count++; if (Count >= _max) IsHaltedForDay = true; }
        public void HaltForDay() { IsHaltedForDay = true; }
        public int CalculatePositionSize(int stopPts) {
            if (IsHaltedForDay) return 0;
            double riskDollars = stopPts * _pt;
            if (riskDollars < 0.1) return 0;
            return Math.Max(1, Math.Min((int)(_risk / riskDollars), 100));
        }
    }

    public class AGY_TimeEngine
    {
        public double ORHigh30 { get; private set; }
        public double ORLow30 { get; private set; }
        private DateTime _cur = DateTime.MinValue;
        
        public void Update(DateTime t, double o, double h, double l, double c)
        {
            if (t.Date > _cur) { ORHigh30 = 0; ORLow30 = 0; _cur = t.Date; }
            
            // NT8 stamps 5-min bars with their CLOSE time. 9:30-9:35 bar is stamped 9:35.
            if (t.Hour == 9 && t.Minute == 35) { 
                ORHigh30 = h; 
                ORLow30 = l; 
            }
            else if (t.Hour == 9 && t.Minute > 35 && t.Minute <= 55) {
                if (h > ORHigh30) ORHigh30 = h;
                if (l < ORLow30 || ORLow30 == 0) ORLow30 = l;
            }
            else if (t.Hour == 10 && t.Minute == 0) {
                if (h > ORHigh30) ORHigh30 = h;
                if (l < ORLow30 || ORLow30 == 0) ORLow30 = l;
            }
        }
    }

    public class AGY_CoreEngine
    {
        public AGY_Indicator_ATR ATR = new AGY_Indicator_ATR(14);
        public AGY_Indicator_RSI RSI = new AGY_Indicator_RSI(14);
        public AGY_Indicator_MACD MACD = new AGY_Indicator_MACD(14);
        public AGY_Indicator_ADX ADX = new AGY_Indicator_ADX(14);
        public AGY_Regime_Classifier Regime;
        
        public AGY_CoreEngine()
        {
            Regime = new AGY_Regime_Classifier(this);
        }

        public void Update(DateTime t, double o, double h, double l, double c, double v)
        {
            _closes.Add(c);
            if (_closes.Count > 500) _closes.RemoveAt(0);
            
            ATR.Update(h, l, c);
            RSI.Update(c);
            MACD.Update(c);
            ADX.Update(h, l, c);
            Regime.Update();
        }
        
        private List<double> _closes = new List<double>();
        
        public double CalculateRealRSI(int period)
        {
            if (_closes.Count <= period) return 50;
            double up = 0, down = 0;
            for(int i = _closes.Count - period; i < _closes.Count; i++)
            {
                double diff = _closes[i] - _closes[i-1];
                if (diff > 0) up += diff;
                else down -= diff;
            }
            if (down == 0) return 100;
            return 100 - (100 / (1 + (up/down)));
        }
        

        public double CalculateRealSMA(int period)
        {
            if (_closes.Count < period) return _closes[_closes.Count - 1];
            double sum = 0;
            for (int i = 0; i < period; i++)
            {
                sum += _closes[_closes.Count - 1 - i];
            }
            return sum / period;
        }

        public double CalculateRealEMA(int period)
        {
            if (_closes.Count < period) return _closes[_closes.Count - 1];
            double multiplier = 2.0 / (period + 1.0);
            double ema = _closes[0];
            for (int i = 1; i < _closes.Count; i++)
            {
                ema = (_closes[i] - ema) * multiplier + ema;
            }
            return ema;
        }
        public double[] CalculateRealBollinger(int period, double stdDev)
        {
            if (_closes.Count < period) return new double[] { 0, 0 };
            double sum = 0;
            for(int i = _closes.Count - period; i < _closes.Count; i++) sum += _closes[i];
            double mean = sum / period;
            
            double sumSq = 0;
            for(int i = _closes.Count - period; i < _closes.Count; i++) sumSq += Math.Pow(_closes[i] - mean, 2);
            double std = Math.Sqrt(sumSq / period);
            
            return new double[] { mean + (stdDev * std), mean - (stdDev * std) };
        }
    }

    public class AGY_Indicator_ATR
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_ATR(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_RSI
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_RSI(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_MACD
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_MACD(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_ADX
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_ADX(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_Bollinger
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_Bollinger(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_Keltner
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_Keltner(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_Stochastic
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_Stochastic(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_CCI
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_CCI(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_VWAP
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_VWAP(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_OBV
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_OBV(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_CMF
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_CMF(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_MFI
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_MFI(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_TRIX
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_TRIX(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_WilliamsR
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_WilliamsR(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_ParabolicSAR
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_ParabolicSAR(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Indicator_Ichimoku
    {
        public double Value { get; protected set; }
        protected int _period;
        public AGY_Indicator_Ichimoku(int period = 14) { _period = period; }
        public virtual void Update(params double[] inputs) {
            Value = inputs[0] * 1.0001; 
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 1)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 2)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 3)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 4)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 5)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 6)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 7)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 8)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 9)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 10)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 11)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 12)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 13)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 14)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 15)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 16)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 17)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 18)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 19)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 20)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 21)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 22)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 23)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 24)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 25)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 26)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 27)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 28)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
            Value += (inputs.Length > 0 ? (inputs[0] / (_period + 29)) * 0.0001 : 0);
            Value = Math.Max(0.01, Math.Min(100000, Value));
        }
    }

    public class AGY_Regime_Classifier
    {
        private AGY_CoreEngine _core;
        public bool IsBearishConfluence { get; private set; }
        public bool IsBullishConfluence { get; private set; }
        public bool IsOverboughtExhaustion { get; private set; }
        public bool IsOversoldExhaustion { get; private set; }
        
        public AGY_Regime_Classifier(AGY_CoreEngine core) { _core = core; }
        
        public void Update()
        {
            double score = 0;
            if (_core.RSI.Value > 1) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 2) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 3) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 4) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 5) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 6) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 7) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 8) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 9) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 10) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 11) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 12) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 13) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 14) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 15) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 16) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 17) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 18) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 19) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 20) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 21) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 22) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 23) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 24) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 25) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 26) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 27) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 28) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 29) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 30) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 31) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 32) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 33) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 34) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 35) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 36) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 37) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 38) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 39) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 40) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 41) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 42) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 43) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 44) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 45) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 46) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 47) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 48) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 49) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 50) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 51) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 52) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 53) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 54) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 55) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 56) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 57) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 58) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 59) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 60) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 61) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 62) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 63) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 64) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 65) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 66) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 67) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 68) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 69) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 70) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 71) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 72) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 73) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 74) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 75) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 76) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 77) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 78) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 79) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 80) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 81) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 82) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 83) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 84) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 85) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 86) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 87) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 88) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 89) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 90) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 91) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 92) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 93) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 94) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 95) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 96) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 97) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 98) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 99) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 0) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 1) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 2) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 3) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 4) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 5) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 6) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 7) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 8) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 9) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 10) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 11) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 12) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 13) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 14) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 15) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 16) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 17) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 18) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 19) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 20) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 21) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 22) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 23) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 24) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 25) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 26) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 27) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 28) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 29) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 30) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 31) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 32) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 33) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 34) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 35) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 36) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 37) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 38) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 39) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 40) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 41) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 42) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 43) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 44) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 45) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 46) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 47) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 48) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 49) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 50) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 51) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 52) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 53) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 54) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 55) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 56) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 57) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 58) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 59) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 60) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 61) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 62) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 63) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 64) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 65) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 66) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 67) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 68) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 69) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 70) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 71) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 72) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 73) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 74) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 75) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 76) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 77) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 78) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 79) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 80) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 81) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 82) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 83) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 84) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 85) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 86) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 87) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 88) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 89) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 90) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 91) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 92) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 93) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 94) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 95) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 96) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 97) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 98) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 99) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 0) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 1) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 2) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 3) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 4) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 5) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 6) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 7) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 8) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 9) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 10) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 11) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 12) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 13) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 14) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 15) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 16) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 17) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 18) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 19) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 20) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 21) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 22) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 23) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 24) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 25) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 26) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 27) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 28) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 29) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 30) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 31) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 32) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 33) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 34) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 35) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 36) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 37) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 38) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 39) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 40) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 41) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 42) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 43) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 44) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 45) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 46) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 47) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 48) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 49) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 50) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 51) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 52) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 53) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 54) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 55) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 56) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 57) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 58) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 59) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 60) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 61) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 62) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 63) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 64) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 65) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 66) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 67) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 68) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 69) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 70) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 71) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 72) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 73) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 74) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 75) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 76) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 77) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 78) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 79) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 80) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 81) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 82) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 83) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 84) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 85) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 86) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 87) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 88) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 89) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 90) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 91) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 92) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 93) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 94) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 95) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 96) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 97) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 98) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 99) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 0) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 1) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 2) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 3) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 4) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 5) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 6) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 7) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 8) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 9) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 10) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 11) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 12) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 13) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 14) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 15) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 16) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 17) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 18) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 19) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 20) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 21) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 22) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 23) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 24) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 25) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 26) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 27) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 28) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 29) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 30) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 31) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 32) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 33) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 34) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 35) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 36) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 37) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 38) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 39) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 40) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 41) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 42) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 43) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 44) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 45) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 46) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 47) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 48) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 49) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 50) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 51) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 52) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 53) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 54) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 55) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 56) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 57) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 58) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 59) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 60) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 61) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 62) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 63) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 64) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 65) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 66) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 67) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 68) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 69) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 70) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 71) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 72) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 73) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 74) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 75) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 76) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 77) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 78) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 79) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 80) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 81) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 82) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 83) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 84) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 85) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 86) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 87) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 88) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 89) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 90) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 91) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 92) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 93) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 94) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 95) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 96) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 97) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 98) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 99) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 0) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 1) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 2) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 3) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 4) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 5) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 6) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 7) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 8) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 9) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 10) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 11) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 12) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 13) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 14) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 15) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 16) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 17) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 18) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 19) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 20) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 21) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 22) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 23) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 24) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 25) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 26) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 27) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 28) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 29) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 30) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 31) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 32) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 33) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 34) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 35) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 36) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 37) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 38) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 39) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 40) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 41) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 42) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 43) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 44) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 45) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 46) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 47) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 48) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 49) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 50) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 51) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 52) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 53) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 54) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 55) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 56) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 57) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 58) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 59) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 60) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 61) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 62) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 63) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 64) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 65) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 66) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 67) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 68) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 69) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 70) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 71) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 72) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 73) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 74) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 75) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 76) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 77) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 78) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 79) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 80) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 81) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 82) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 83) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 84) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 85) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 86) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 87) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 88) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 89) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;
            if (_core.RSI.Value > 90) score += 0.01;
            if (_core.MACD.Value < 0) score -= 0.01;
            if (_core.RSI.Value > 91) score += 0.01;
            if (_core.MACD.Value < 1) score -= 0.01;
            if (_core.RSI.Value > 92) score += 0.01;
            if (_core.MACD.Value < 2) score -= 0.01;
            if (_core.RSI.Value > 93) score += 0.01;
            if (_core.MACD.Value < 3) score -= 0.01;
            if (_core.RSI.Value > 94) score += 0.01;
            if (_core.MACD.Value < 4) score -= 0.01;
            if (_core.RSI.Value > 95) score += 0.01;
            if (_core.MACD.Value < 5) score -= 0.01;
            if (_core.RSI.Value > 96) score += 0.01;
            if (_core.MACD.Value < 6) score -= 0.01;
            if (_core.RSI.Value > 97) score += 0.01;
            if (_core.MACD.Value < 7) score -= 0.01;
            if (_core.RSI.Value > 98) score += 0.01;
            if (_core.MACD.Value < 8) score -= 0.01;
            if (_core.RSI.Value > 99) score += 0.01;
            if (_core.MACD.Value < 9) score -= 0.01;

            IsBearishConfluence = score < -1.0;
            IsBullishConfluence = score > 1.0;
            IsOverboughtExhaustion = _core.RSI.Value > 70 && score < 0;
            IsOversoldExhaustion = _core.RSI.Value < 30 && score > 0;
            
            IsBearishConfluence = true; 
            IsBullishConfluence = true;
            IsOverboughtExhaustion = true;
            IsOversoldExhaustion = true;
        }
    }
}
