#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.SuperDom;
using NinjaTrader.Gui.Tools;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class GexMatrix : Strategy
    {
        // GEX Proxies
        private double CallWallLevel = 0;
        private double PutWallLevel = 0;
        private double ZeroGammaLevel = 0;
        private bool IsPositiveGEX = true;

        // Session Tracking
        private double sessionHigh = 0;
        private double sessionLow = double.MaxValue;
        private double previousSessionClose = 0;
        private List<double> dailyRanges;
        
        // Execution Locks
        private bool callWallTraded = false;
        private bool putWallTraded = false;
        private bool zeroGammaTraded = false;
        private bool levelsCalculated = false;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = @"The Autonomous GEX Matrix: Simulating Options Dealer Hedging mechanically.";
                Name                                        = "GexMatrix";
                Calculate                                   = Calculate.OnBarClose;
                EntriesPerDirection                         = 1;
                EntryHandling                               = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy                = true;
                ExitOnSessionCloseSeconds                   = 30;
                IsFillLimitOnTouch                          = false;
                MaximumBarsLookBack                         = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution                         = OrderFillResolution.Standard;
                Slippage                                    = 0;
                StartBehavior                               = StartBehavior.WaitUntilFlat;
                TimeInForce                                 = TimeInForce.Gtc;
                TraceOrders                                 = false;
                RealtimeErrorHandling                       = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling                          = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade                         = 2;
                IsInstantiatedOnEachOptimizationIteration   = true;
                
                ContractSize                                = 2; // 2 Minis
                TargetTicks                                 = 80; // 20 NQ Points ($800)
                StopLossTicks                               = 80; // 20 NQ Points ($800)
                
                StrikeInterval                              = 50.0; // NQ options strike every 50 points
                ToleranceTicks                              = 20; // 5 NQ points tolerance to trigger walls
                LookbackDays                                = 14;
            }
            else if (State == State.Configure)
            {
                SetProfitTarget("", CalculationMode.Ticks, TargetTicks);
                SetStopLoss("", CalculationMode.Ticks, StopLossTicks, false);
            }
            else if (State == State.DataLoaded)
            {
                dailyRanges = new List<double>();
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade) return;

            int currentTime = ToTime(Time[0]);

            // Session Boundaries
            if (Bars.IsFirstBarOfSession)
            {
                if (sessionHigh != 0 && sessionLow != double.MaxValue)
                {
                    dailyRanges.Add(sessionHigh - sessionLow);
                    if (dailyRanges.Count > LookbackDays) dailyRanges.RemoveAt(0);
                    
                    previousSessionClose = Close[1]; // Prior day's final settlement
                }

                sessionHigh = High[0];
                sessionLow = Low[0];
                
                callWallTraded = false;
                putWallTraded = false;
                zeroGammaTraded = false;
                levelsCalculated = false;
            }

            // Real-time tracking for tomorrow's ADR
            if (High[0] > sessionHigh) sessionHigh = High[0];
            if (Low[0] < sessionLow) sessionLow = Low[0];

            // Wait for 14 days of data to build the volatility budget proxy
            if (dailyRanges.Count < LookbackDays) return;

            // ==========================================
            // AUTONOMOUS GEX CALCULATION (09:30 AM EST)
            // ==========================================
            if (!levelsCalculated && currentTime >= 93000)
            {
                double adr = dailyRanges.Average();
                
                // 1. Zero Gamma Proxy (Prior Day Settlement)
                ZeroGammaLevel = previousSessionClose;

                // 2. Call Wall Proxy (Zero Gamma + ADR, snapped to closest Options Strike)
                CallWallLevel = Math.Round((ZeroGammaLevel + adr) / StrikeInterval) * StrikeInterval;

                // 3. Put Wall Proxy (Zero Gamma - ADR, snapped to closest Options Strike)
                PutWallLevel = Math.Round((ZeroGammaLevel - adr) / StrikeInterval) * StrikeInterval;

                // 4. Regime Classification (Open relative to Zero Gamma)
                IsPositiveGEX = Open[0] >= ZeroGammaLevel;

                levelsCalculated = true;
                
                // Draw the dynamic levels for visualization on chart
                Draw.Line(this, "CallWall", false, 0, CallWallLevel, -1, CallWallLevel, Brushes.Red, DashStyleHelper.Solid, 2);
                Draw.Line(this, "PutWall", false, 0, PutWallLevel, -1, PutWallLevel, Brushes.Green, DashStyleHelper.Solid, 2);
                Draw.Line(this, "ZeroGamma", false, 0, ZeroGammaLevel, -1, ZeroGammaLevel, Brushes.Blue, DashStyleHelper.Dash, 2);
            }

            if (!levelsCalculated) return;
            if (currentTime < 93000 || currentTime > 154500) return;
            if (Position.MarketPosition != MarketPosition.Flat) return;

            double tolerance = ToleranceTicks * TickSize;

            if (IsPositiveGEX)
            {
                // ==========================================
                // POSITIVE GAMMA REGIME (Mean Reversion / Fading)
                // ==========================================
                // Dealers suppress volatility. They buy dips and sell rallies.
                
                // 1. Fade the Call Wall (Resistance)
                if (!callWallTraded && High[0] >= (CallWallLevel - tolerance) && High[0] <= (CallWallLevel + tolerance))
                {
                    // Confirm rejection with a red close
                    if (Close[0] < Open[0])
                    {
                        EnterShort(ContractSize, "Fade Call Wall");
                        callWallTraded = true;
                    }
                }
                // 2. Fade the Put Wall (Support)
                else if (!putWallTraded && Low[0] <= (PutWallLevel + tolerance) && Low[0] >= (PutWallLevel - tolerance))
                {
                    // Confirm bounce with a green close
                    if (Close[0] > Open[0])
                    {
                        EnterLong(ContractSize, "Fade Put Wall");
                        putWallTraded = true;
                    }
                }
            }
            else
            {
                // ==========================================
                // NEGATIVE GAMMA REGIME (Volatility Expansion / Squeezes)
                // ==========================================
                // Dealers amplify volatility. Walls break.
                
                // 1. Gamma Squeeze Above Call Wall
                if (!callWallTraded && Close[1] <= CallWallLevel && Close[0] > CallWallLevel)
                {
                    EnterLong(ContractSize, "Call Wall Squeeze");
                    callWallTraded = true;
                }
                // 2. Liquidation Below Put Wall
                else if (!putWallTraded && Close[1] >= PutWallLevel && Close[0] < PutWallLevel)
                {
                    EnterShort(ContractSize, "Put Wall Breakdown");
                    putWallTraded = true;
                }
                
                // 3. Volatility Trigger (Zero Gamma Flip)
                if (!zeroGammaTraded)
                {
                    if (Close[1] >= ZeroGammaLevel && Close[0] < ZeroGammaLevel)
                    {
                        EnterShort(ContractSize, "Zero Gamma Breakdown");
                        zeroGammaTraded = true;
                    }
                    else if (Close[1] <= ZeroGammaLevel && Close[0] > ZeroGammaLevel)
                    {
                        EnterLong(ContractSize, "Zero Gamma Breakout");
                        zeroGammaTraded = true;
                    }
                }
            }
        }

        #region Properties
        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Contract Size", Order=1, GroupName="Parameters")]
        public int ContractSize { get; set; }
        
        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Target (Ticks)", Order=2, GroupName="Parameters")]
        public int TargetTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Stop Loss (Ticks)", Order=3, GroupName="Parameters")]
        public int StopLossTicks { get; set; }

        [NinjaScriptProperty]
        [Range(10, 100)]
        [Display(Name="Strike Interval (Points)", Order=4, GroupName="GEX Data")]
        public double StrikeInterval { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Tolerance (Ticks)", Order=5, GroupName="GEX Data")]
        public int ToleranceTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="ADR Lookback Days", Order=6, GroupName="GEX Data")]
        public int LookbackDays { get; set; }
        #endregion
    }
}
