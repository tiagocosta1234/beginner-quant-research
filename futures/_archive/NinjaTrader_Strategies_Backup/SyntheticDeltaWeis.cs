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
    public class SyntheticDeltaWeis : Strategy
    {
        private ATR _atr;
        
        // Wave state
        private int _currentWaveDirection = 1; // 1 for Up, -1 for Down
        private double _waveExtreme = 0; // The highest high of an up-wave, or lowest low of a down-wave
        private double _waveStartPrice = 0;
        
        // Cumulative trackers
        private double _cumulativeWaveVol = 0;
        private double _cumulativeBuyVol = 0;
        private double _cumulativeSellVol = 0;
        
        private bool _tradedToday = false;
        private DateTime _currentSessionDate;

        [NinjaScriptProperty]
                [Display(Name="Contracts", Order=1, GroupName="1. Risk")]
        public int Contracts { get; set; }

        [NinjaScriptProperty]
                [Display(Name="Stop Loss (Points)", Order=2, GroupName="1. Risk")]
        public int StopLossPoints { get; set; }

        [NinjaScriptProperty]
                [Display(Name="Take Profit (Points)", Order=3, GroupName="1. Risk")]
        public int TakeProfitPoints { get; set; }

        [NinjaScriptProperty]
                [Display(Name="ATR Reversal Multiplier", Order=1, GroupName="2. Microstructure")]
        public double AtrReversalMultiplier { get; set; }
        
        [NinjaScriptProperty]
                [Display(Name="Effort Threshold (Volume)", Order=2, GroupName="2. Microstructure")]
        public double EffortThreshold { get; set; }

        [NinjaScriptProperty]
                [Display(Name="Result Threshold (Points)", Order=3, GroupName="2. Microstructure")]
        public double ResultThreshold { get; set; }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = @"Synthetic Delta Weis Waves (Effort vs Result)";
                Name                                        = "SyntheticDeltaWeis";
                Calculate                                   = Calculate.OnBarClose;
                EntriesPerDirection                         = 1;
                EntryHandling                               = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy                = true;
                ExitOnSessionCloseSeconds                   = 30;
                IsFillLimitOnTouch                          = false;
                MaximumBarsLookBack                         = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution                         = OrderFillResolution.Standard;
                Slippage                                    = 1;
                StartBehavior                               = StartBehavior.WaitUntilFlat;
                TimeInForce                                 = TimeInForce.Gtc;
                TraceOrders                                 = false;
                RealtimeErrorHandling                       = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling                          = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade                         = 20;
                IsInstantiatedOnEachOptimizationIteration   = true;
                
                Contracts = 10;
                StopLossPoints = 40;
                TakeProfitPoints = 40;
                
                AtrReversalMultiplier = 1.5;
                EffortThreshold = 5000; // Minimum volume required to consider a wave 'High Effort'
                ResultThreshold = 10;   // Maximum points moved to consider a wave 'Low Result'
            }
            else if (State == State.Configure)
            {
                _atr = ATR(14);
                AddChartIndicator(_atr);
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < 20) return;

            // Session tracker
            if (Time[0].Date != _currentSessionDate)
            {
                _currentSessionDate = Time[0].Date;
                _tradedToday = false;
            }

            // Power Hour Eject
            if (Time[0].TimeOfDay >= new TimeSpan(14, 50, 0))
            {
                if (Position.MarketPosition == MarketPosition.Long) ExitLong("PowerHour_Eject", "");
                if (Position.MarketPosition == MarketPosition.Short) ExitShort("PowerHour_Eject", "");
                return;
            }

            if (Time[0].TimeOfDay >= new TimeSpan(14, 50, 0)) return;
            if (_tradedToday) return;

            // 1. Approximate Volume Delta for this bar (Intrabar Proportional)
            double range = High[0] - Low[0];
            double buyPressure = 0.5; // Default to neutral if bar is flat
            if (range > 0)
            {
                buyPressure = (Close[0] - Low[0]) / range;
            }
            double barBuyVol = Volume[0] * buyPressure;
            double barSellVol = Volume[0] - barBuyVol;

            // 2. Wave Detection & Reversal Logic
            double reversalDistance = _atr[0] * AtrReversalMultiplier;

            if (_currentWaveDirection == 1)
            {
                // We are in an UP wave
                if (High[0] > _waveExtreme) 
                {
                    _waveExtreme = High[0]; // Extend the up wave
                }
                else if (Close[0] < _waveExtreme - reversalDistance)
                {
                    // Price dropped below the threshold from the peak. REVERSAL!
                    _currentWaveDirection = -1;
                    _waveExtreme = Low[0];
                    _waveStartPrice = High[1]; // Approximate top
                    _cumulativeWaveVol = 0;
                    _cumulativeBuyVol = 0;
                    _cumulativeSellVol = 0;
                }
            }
            else
            {
                // We are in a DOWN wave
                if (Low[0] < _waveExtreme)
                {
                    _waveExtreme = Low[0]; // Extend the down wave
                }
                else if (Close[0] > _waveExtreme + reversalDistance)
                {
                    // Price rallied above the threshold from the trough. REVERSAL!
                    _currentWaveDirection = 1;
                    _waveExtreme = High[0];
                    _waveStartPrice = Low[1]; // Approximate bottom
                    _cumulativeWaveVol = 0;
                    _cumulativeBuyVol = 0;
                    _cumulativeSellVol = 0;
                }
            }

            // 3. Accumulate Volume
            _cumulativeWaveVol += Volume[0];
            _cumulativeBuyVol += barBuyVol;
            _cumulativeSellVol += barSellVol;

            // 4. Effort vs Result (Absorption) Detection
            // We want to detect if a wave is accumulating MASSIVE volume, but going nowhere.
            if (_currentWaveDirection == 1)
            {
                double resultPoints = _waveExtreme - _waveStartPrice;
                if (_cumulativeWaveVol > EffortThreshold && resultPoints < ResultThreshold)
                {
                    // HIGH EFFORT, LOW RESULT (UP WAVE)
                    // Massive buying pressure absorbed by hidden limit sellers.
                    // Fade the upward drift.
                    SetStopLoss("Weis_S", CalculationMode.Ticks, StopLossPoints * 4, false);
                    SetProfitTarget("Weis_S", CalculationMode.Ticks, TakeProfitPoints * 4);
                    EnterShort(Contracts, "Weis_S");
                    _tradedToday = true;
                }
            }
            else if (_currentWaveDirection == -1)
            {
                double resultPoints = _waveStartPrice - _waveExtreme;
                if (_cumulativeWaveVol > EffortThreshold && resultPoints < ResultThreshold)
                {
                    // HIGH EFFORT, LOW RESULT (DOWN WAVE)
                    // Massive selling pressure absorbed by hidden limit buyers.
                    // Fade the downward drift.
                    SetStopLoss("Weis_L", CalculationMode.Ticks, StopLossPoints * 4, false);
                    SetProfitTarget("Weis_L", CalculationMode.Ticks, TakeProfitPoints * 4);
                    EnterLong(Contracts, "Weis_L");
                    _tradedToday = true;
                }
            }
        }
    }
}
