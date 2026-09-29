using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.Tools;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.DrawingTools;
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Windows.Media;

namespace NinjaTrader.NinjaScript.Strategies
{
    public class ManualCustomBot : Strategy
    {
        [NinjaScriptProperty]
        [Range(10.0, 10000.0)]
        [Display(Name = "Trade Risk ($)", Order = 1, GroupName = "1. Sprint Size")]
        public double TradeRiskCurrency { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Loss Pause Filter", Order = 2, GroupName = "1. Sprint Size")]
        public bool LossPauseFilter { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Use Pullback Entry", Order = 3, GroupName = "1. Sprint Size")]
        public bool UsePullbackEntry { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 10000.0)]
        [Display(Name = "Daily Loss Limit ($)", Order = 1, GroupName = "2. Risk Management")]
        public double DailyLossLimit { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 10000.0)]
        [Display(Name = "Daily Profit Limit ($)", Order = 2, GroupName = "2. Risk Management")]
        public double DailyProfitLimit { get; set; }
        
        [NinjaScriptProperty]
        [Range(1.0, 1000.0)]
        [Display(Name = "Target Points (1:1)", Order = 1, GroupName = "3. 5-Bar Anomaly")]
        public double TargetPoints { get; set; }

        private double dailyRealizedPnL;
        private double startOfDayCumProfit;
        private bool hitDailyLimit;
        private bool hitLossPause;
        private int lastTradeCount;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = @"15-Minute 5-Bar Anomaly (Dynamic Position Sizing).";
                Name                                        = "ManualCustomBot";
                Calculate                                   = Calculate.OnBarClose;
                EntriesPerDirection                         = 1;
                EntryHandling                               = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy                = true;
                ExitOnSessionCloseSeconds                   = 30;
                IsFillLimitOnTouch                          = false;
                MaximumBarsLookBack                         = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution                         = OrderFillResolution.Standard;
                Slippage                                    = 2;
                StartBehavior                               = StartBehavior.WaitUntilFlat;
                TimeInForce                                 = TimeInForce.Gtc;
                TraceOrders                                 = false;
                RealtimeErrorHandling                       = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling                          = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade                         = 20;
                IsInstantiatedOnEachOptimizationIteration   = true;

                TradeRiskCurrency                           = 1040.0;
                LossPauseFilter                             = false;
                UsePullbackEntry                            = false;
                DailyLossLimit                              = 1040.0;
                DailyProfitLimit                            = 1040.0;
                TargetPoints                                = 40.0;
            }
            else if (State == State.DataLoaded)
            {
                dailyRealizedPnL = 0;
                startOfDayCumProfit = 0;
                hitDailyLimit = false;
                hitLossPause = false;
                lastTradeCount = 0;
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade) return;

            if (Bars.IsFirstBarOfSession)
            {
                dailyRealizedPnL = 0;
                hitDailyLimit = false;
                hitLossPause = false;
                startOfDayCumProfit = (SystemPerformance != null) ? SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit : 0;
                lastTradeCount = (SystemPerformance != null) ? SystemPerformance.AllTrades.Count : 0;
            }

            if (SystemPerformance != null)
            {
                dailyRealizedPnL = SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit - startOfDayCumProfit;
                
                if (SystemPerformance.AllTrades.Count > lastTradeCount)
                {
                    Trade lastTrade = SystemPerformance.AllTrades[SystemPerformance.AllTrades.Count - 1];
                    if (lastTrade.ProfitCurrency < 0) hitLossPause = true;
                    lastTradeCount = SystemPerformance.AllTrades.Count;
                }
            }
            
            double currentDailyPnL = dailyRealizedPnL + (Position.MarketPosition != MarketPosition.Flat ? Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]) : 0);
            
            if (!hitDailyLimit && (currentDailyPnL <= -DailyLossLimit || currentDailyPnL >= DailyProfitLimit))
            {
                hitDailyLimit = true;
                if (Position.MarketPosition != MarketPosition.Flat)
                {
                    ExitLong("CircuitBreaker", "");
                    ExitShort("CircuitBreaker", "");
                }
            }

            UpdateChartDashboard();

            bool isPausedForLoss = LossPauseFilter && hitLossPause;
            if (hitDailyLimit || isPausedForLoss || Position.MarketPosition != MarketPosition.Flat) return;

                        // STRICT TIME OF DAY FILTER (09:30 AM to 4:00 PM EST)
            int time = ToTime(Time[0]);
            if (time < 93000 || time >= 160000) return;

            bool is5BarDownAnomaly = true;
            bool is5BarUpAnomaly = true;

            // MOMENTUM INVERSION: Ride the trend, do not fade it.
            for (int i = 0; i < 5; i++)
            {
                if (Close[i] >= Open[i]) is5BarDownAnomaly = false; // If any bar is green, it's not 5 red
                if (Close[i] <= Open[i]) is5BarUpAnomaly = false;   // If any bar is red, it's not 5 green
            }

            // DYNAMIC POSITION SIZING LOGIC
            double pointValue = Instrument.MasterInstrument.PointValue;
            double riskPerContract = TargetPoints * pointValue;
            int dynamicContracts = (int)Math.Floor(TradeRiskCurrency / riskPerContract);
            dynamicContracts = Math.Max(1, dynamicContracts); // Safety to prevent 0 contracts

            if (is5BarUpAnomaly) // 5 Green -> LONG (Riding Momentum)
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
            }
        }

        private void UpdateChartDashboard()
        {
            if (State != State.Historical && State != State.Realtime) return;

            string status = hitDailyLimit ? "LOCKED (Limit Hit)" : (hitLossPause ? "PAUSED (Loss Filter)" : "HUNTING ANOMALY");
            double currentOpenPnL = Position.MarketPosition != MarketPosition.Flat ? Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]) : 0;
            double liveDailyPnL = dailyRealizedPnL + currentOpenPnL;

            string dashboardText = string.Format(
                "=== DYNAMIC RISK SPRINT ===\n" +
                " Status: {0}\n" +
                " Session PnL: ${1:F2}\n" +
                " Target: $1k Locked Bets\n" +
                "===========================",
                status, liveDailyPnL);

            Draw.TextFixed(this, "ManualDashboard", dashboardText, TextPosition.TopRight, 
                           Brushes.White, new Gui.Tools.SimpleFont("Consolas", 14), 
                           Brushes.Black, Brushes.Magenta, 80);
        }
    }
}






