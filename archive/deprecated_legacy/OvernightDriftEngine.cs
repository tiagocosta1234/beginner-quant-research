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
    public class OvernightDriftEngine : Strategy
    {
        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = @"The Overnight Drift Engine: Captures the macro risk-premium anomaly by buying MOC and selling the NY Open.";
                Name                                        = "OvernightDriftEngine";
                Calculate                                   = Calculate.OnBarClose;
                EntriesPerDirection                         = 1;
                EntryHandling                               = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy                = false; // CRITICAL: Must be false to hold overnight through the 17:00 EST reset
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
                BarsRequiredToTrade                         = 20;
                IsInstantiatedOnEachOptimizationIteration   = true;
                
                ContractSize                                = 1;
                CatastrophicStopPoints                      = 200.0;
                HoldOverWeekend                             = false;
            }
            else if (State == State.Configure)
            {
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade) return;

            // Bulletproof EST Time Conversion (Ignores user PC and NT8 settings)
            TimeZoneInfo estZone;
            try { estZone = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
            catch { estZone = TimeZoneInfo.FindSystemTimeZoneById("US Eastern Standard Time"); }
            
            DateTime estTime = TimeZoneInfo.ConvertTimeFromUtc(Time[0].ToUniversalTime(), estZone);
            int time = estTime.Hour * 10000 + estTime.Minute * 100 + estTime.Second;
            int dayOfWeek = (int)estTime.DayOfWeek;

            // 1. The Entry: 15:55 EST (5 minutes before cash close to front-run MOC)
            if (time == 155500 && Position.MarketPosition == MarketPosition.Flat)
            {
                // Day 5 = Friday. If HoldOverWeekend is false, skip Friday afternoon entries.
                if (dayOfWeek == 5 && !HoldOverWeekend) return;

                SetStopLoss(CalculationMode.Ticks, CatastrophicStopPoints / TickSize);
                EnterLong(ContractSize, "DriftEntry");
            }

            // 2. The Exit: 09:30 EST (Cash Open handoff to retail)
            // Using >= 93000 to catch the first available bar if exactly 93000 doesn't print
            if (time >= 93000 && time <= 93500 && Position.MarketPosition == MarketPosition.Long)
            {
                ExitLong(ContractSize, "TimeExit", "DriftEntry");
            }
        }

        #region Properties
        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Contract Size", Order=1, GroupName="Parameters")]
        public int ContractSize { get; set; }
        
        [NinjaScriptProperty]
        [Range(50, 1000)]
        [Display(Name="Catastrophic Stop (Points)", Order=2, GroupName="Risk Management")]
        public double CatastrophicStopPoints { get; set; }
        
        [NinjaScriptProperty]
        [Display(Name="Hold Over Weekend (Friday Entry)", Order=3, GroupName="Parameters")]
        public bool HoldOverWeekend { get; set; }
        #endregion
    }
}
