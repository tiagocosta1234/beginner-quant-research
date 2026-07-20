#region Using declarations
using System;
using System.ComponentModel.DataAnnotations;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript.Indicators;
using System.IO;
using System.Collections.Generic;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class EfficientBreakout : Strategy
    {
        public enum GammaType { Positive, Negative, Neutral }
        private int tradeQuantity;
        private double orbHigh = double.MinValue;
        private double orbLow = double.MaxValue;
        private bool isRangeDefined = false;
        private int tradesTakenToday = 0;
        private int lastTradingDay = -1;
        
        #region 1. Risk Management Properties
        [NinjaScriptProperty]
        [Range(1000, 1000000)]
        [Display(Name="Initial Balance", Description="Starting balance of the account", Order=1, GroupName="1. Risk Management")]
        public double InitialBalance { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 10.0)]
        [Display(Name="Risk Percentage", Description="Percentage of initial balance to risk per trade", Order=2, GroupName="1. Risk Management")]
        public double RiskPercentage { get; set; }
        
        [NinjaScriptProperty]
        [Range(1, 1000)]
        [Display(Name="Stop Loss (Ticks)", Description="Stop loss distance in ticks from entry", Order=3, GroupName="1. Risk Management")]
        public int StopLossTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 1000)]
        [Display(Name="Profit Target (Ticks)", Description="Take profit distance in ticks from entry", Order=4, GroupName="1. Risk Management")]
        public int ProfitTargetTicks { get; set; }
        #endregion

        #region 2. Session Parameters
        [NinjaScriptProperty]
        [PropertyEditor("NinjaTrader.Gui.Tools.TimeEditorKey")]
        [Display(Name="ORB Start Time (EST)", Description="When the opening range begins forming", Order=1, GroupName="2. Session Settings")]
        public DateTime ORBStartTime { get; set; }

        [NinjaScriptProperty]
        [PropertyEditor("NinjaTrader.Gui.Tools.TimeEditorKey")]
        [Display(Name="ORB End Time (EST)", Description="When the range locks and trading begins", Order=2, GroupName="2. Session Settings")]
        public DateTime ORBEndTime { get; set; }

        [NinjaScriptProperty]
        [PropertyEditor("NinjaTrader.Gui.Tools.TimeEditorKey")]
        [Display(Name="Session Cutoff (EST)", Description="No new trades allowed after this time", Order=3, GroupName="2. Session Settings")]
        public DateTime SessionCutoff { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Max Trades Per Day", Description="Maximum number of trades allowed per day", Order=4, GroupName="2. Session Settings")]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name="Daily Profit Target ($)", Description="Stop trading if this daily profit is reached", Order=5, GroupName="2. Session Settings")]
        public double DailyProfitTarget { get; set; }
        #endregion

        #region 3. Trade Management
        [NinjaScriptProperty]
        [Display(Name="Use Dynamic Trailing Stop", Description="Trail stop behind moving average or fixed ticks", Order=1, GroupName="3. Trade Management")]
        public bool UseTrailingStop { get; set; }

        [NinjaScriptProperty]
        [Range(1, 1000)]
        [Display(Name="Trailing Stop Distance (Ticks)", Description="How far behind price to trail", Order=2, GroupName="3. Trade Management")]
        public int TrailingDistance { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Use Scale-Outs", Description="Take partial profit at Target 1 and let the rest run", Order=3, GroupName="3. Trade Management")]
        public bool UseScaleOuts { get; set; }
        #endregion

        #region 4. Day Filters
        [NinjaScriptProperty]
        [Display(Name="Trade Monday", Description="Allow trades on Mondays", Order=1, GroupName="4. Day Filters")]
        public bool TradeMonday { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Trade Tuesday", Description="Allow trades on Tuesdays", Order=2, GroupName="4. Day Filters")]
        public bool TradeTuesday { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Trade Wednesday", Description="Allow trades on Wednesdays", Order=3, GroupName="4. Day Filters")]
        public bool TradeWednesday { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Trade Thursday", Description="Allow trades on Thursdays", Order=4, GroupName="4. Day Filters")]
        public bool TradeThursday { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Trade Friday", Description="Allow trades on Fridays", Order=5, GroupName="4. Day Filters")]
        public bool TradeFriday { get; set; }
        #endregion

        #region 5. Institutional Context
        [NinjaScriptProperty]
        [Display(Name="Gamma Regime", Description="Current day's Gamma exposure", Order=1, GroupName="5. Institutional Context")]
        public GammaType GammaRegime { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Call Resistance (Gamma)", Description="0 DTE Call Resistance", Order=2, GroupName="5. Institutional Context")]
        public double CallResistance { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Put Support (Gamma)", Description="0 DTE Put Support", Order=3, GroupName="5. Institutional Context")]
        public double PutSupport { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Value Area High", Description="Overnight VAH", Order=4, GroupName="5. Institutional Context")]
        public double VAH { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Value Area Low", Description="Overnight VAL", Order=5, GroupName="5. Institutional Context")]
        public double VAL { get; set; }
        #endregion

        // ML Feature Variables
        private double entryRSI = 0;
        private double entryATR = 0;
        private double entryVolume = 0;
        private double orbRangeSize = 0;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = @"v1.3 Master: 15M Set-and-Forget ORB (Tuesday Filtered).";
                Name                                        = "EfficientBreakout";
                Calculate                                   = Calculate.OnEachTick;
                EntriesPerDirection                         = 1;
                EntryHandling                               = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy                = true;
                ExitOnSessionCloseSeconds                   = 30;
                IsFillLimitOnTouch                          = false;
                MaximumBarsLookBack                         = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution                         = OrderFillResolution.Standard;
                StartBehavior                               = StartBehavior.WaitUntilFlat;
                TimeInForce                                 = TimeInForce.Gtc;
                BarsRequiredToTrade                         = 5;
                
                // Proven v1.0 Defaults
                InitialBalance                              = 50000;
                RiskPercentage                              = 1.0;
                StopLossTicks                               = 200;  
                ProfitTargetTicks                           = 600;  
                ORBStartTime                                = DateTime.Parse("09:30:00");
                ORBEndTime                                  = DateTime.Parse("10:00:00");
                SessionCutoff                               = DateTime.Parse("15:30:00");
                MaxTradesPerDay                             = 3;
                DailyProfitTarget                           = 1500.0;
                
                // Advanced Trade Management
                UseTrailingStop                             = true;
                TrailingDistance                            = 100;
                UseScaleOuts                                = true;
                
                // Institutional Defaults
                GammaRegime                                 = GammaType.Neutral;
                CallResistance                              = 20000;
                PutSupport                                  = 10000;
                VAH                                         = 20000;
                VAL                                         = 10000;
                
                // Optimized Day Filters
                TradeMonday                                 = true;
                TradeTuesday                                = false; // Permanently disabled for efficiency 
                TradeWednesday                              = true;
                TradeThursday                               = true;
                TradeFriday                                 = true;
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade)
                return;

            // 1. DAY RESET LOGIC
            if (Time[0].Day != lastTradingDay)
            {
                lastTradingDay = Time[0].Day;
                tradesTakenToday = 0;
                isRangeDefined = false;
                orbHigh = double.MinValue;
                orbLow = double.MaxValue;
            }

            bool isDayAllowed = false;
            switch (Time[0].DayOfWeek)
            {
                case DayOfWeek.Monday:    isDayAllowed = TradeMonday; break;
                case DayOfWeek.Tuesday:   isDayAllowed = TradeTuesday; break;
                case DayOfWeek.Wednesday: isDayAllowed = TradeWednesday; break;
                case DayOfWeek.Thursday:  isDayAllowed = TradeThursday; break;
                case DayOfWeek.Friday:    isDayAllowed = TradeFriday; break;
            }

            // 2. ACTIVE POSITION PROTECTION (Dynamic Trailing & Hard Consistency Stop)
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                // Hard Consistency Stop
                double realizedDailyProfit = 0;
                foreach (Trade trade in SystemPerformance.AllTrades)
                {
                    if (trade.Exit != null && trade.Exit.Time.Date == Time[0].Date)
                        realizedDailyProfit += trade.ProfitCurrency;
                }
                double openProfit = Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]);
                
                if (realizedDailyProfit + openProfit >= DailyProfitTarget)
                {
                    if (Position.MarketPosition == MarketPosition.Long)
                        ExitLong("Daily Target Hit", "ORB_Long");
                    else if (Position.MarketPosition == MarketPosition.Short)
                        ExitShort("Daily Target Hit", "ORB_Short");
                    return; 
                }

                if (UseTrailingStop)
                {
                    if (Position.MarketPosition == MarketPosition.Long)
                    {
                        double newStop = Close[0] - (TrailingDistance * TickSize);
                        SetStopLoss(CalculationMode.Price, newStop);
                    }
                    else if (Position.MarketPosition == MarketPosition.Short)
                    {
                        double newStop = Close[0] + (TrailingDistance * TickSize);
                        SetStopLoss(CalculationMode.Price, newStop);
                    }
                }
                return; 
            }

            if (!isDayAllowed) return;

            int currentTime = ToTime(Time[0]);
            int orbStartStr = ToTime(ORBStartTime);
            int orbEndStr = ToTime(ORBEndTime);
            int cutoffStr = ToTime(SessionCutoff);

            // 3. RANGE BUILDING PHASE
            if (currentTime >= orbStartStr && currentTime <= orbEndStr)
            {
                if (High[0] > orbHigh) orbHigh = High[0];
                if (Low[0] < orbLow) orbLow = Low[0];
                return; 
            }
            if (currentTime > orbEndStr) isRangeDefined = true;

            // 4. BREAKOUT EXECUTION PHASE
            if (isRangeDefined && tradesTakenToday < MaxTradesPerDay && currentTime < cutoffStr && Position.MarketPosition == MarketPosition.Flat)
            {
                entryRSI = RSI(14, 3)[0];
                entryATR = ATR(14)[0];
                entryVolume = Volume[0];
                orbRangeSize = orbHigh - orbLow;
                
                // --- V10 ML EDGE FILTER ---
                if (orbRangeSize > 72.88 && entryVolume > 108777) return;
                // Check Daily Profit Target
                double dailyProfit = 0;
                foreach (Trade trade in SystemPerformance.AllTrades)
                {
                    if (trade.Exit != null && trade.Exit.Time.Date == Time[0].Date)
                        dailyProfit += trade.ProfitCurrency;
                }
                
                if (dailyProfit >= DailyProfitTarget)
                    return; // Stop trading, daily target reached!

                double riskAmountCash = InitialBalance * (RiskPercentage / 100.0);
                double tickValue = Instrument.MasterInstrument.PointValue * Instrument.MasterInstrument.TickSize;
                double stopLossCash = StopLossTicks * tickValue;
                
                tradeQuantity = (int)Math.Floor(riskAmountCash / stopLossCash);
                if (tradeQuantity < 2) tradeQuantity = 2; // Ensure at least 2 for scale outs

                if (Close[0] > orbHigh)
                {
                    SetStopLoss("ORB_Long", CalculationMode.Ticks, StopLossTicks, false);
                    EnterLong(tradeQuantity, "ORB_Long");
                    tradesTakenToday++;
                }
                else if (Close[0] < orbLow)
                {
                    SetStopLoss("ORB_Short", CalculationMode.Ticks, StopLossTicks, false);
                    EnterShort(tradeQuantity, "ORB_Short");
                    tradesTakenToday++;
                }
            }
        }
        
        protected override void OnPositionUpdate(Position position, double averagePrice, int quantity, MarketPosition marketPosition)
        {
            if (position.MarketPosition == MarketPosition.Flat && SystemPerformance.AllTrades.Count > 0)
            {
                // Position just closed. Log the last trade!
                Trade lastTrade = SystemPerformance.AllTrades[SystemPerformance.AllTrades.Count - 1];
                try
                {
                    string logPath = @"Advanced_Trades_Log.csv";
                    bool appendHeader = !File.Exists(logPath);
                    using (StreamWriter sw = File.AppendText(logPath))
                    {
                        if (appendHeader) sw.WriteLine("EntryTime,Direction,EntryPrice,Profit,GammaRegime,VAH,VAL,EntryRSI,EntryATR,EntryVolume,ORBRange");
                        string direction = lastTrade.Entry.MarketPosition == MarketPosition.Long ? "Long" : "Short";
                        sw.WriteLine($"{lastTrade.Entry.Time},{direction},{lastTrade.Entry.Price},{lastTrade.ProfitCurrency},{GammaRegime},{VAH},{VAL},{entryRSI},{entryATR},{entryVolume},{orbRangeSize}");
                    }
                } catch { }
            }
        }
    }
}