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
    public class TouchORB_15M : Strategy
    {
        // -----------------------------------------------------
        // Global Cross-Chart Synchronization
        // -----------------------------------------------------
        private static DateTime globalLastTradeDate = DateTime.MinValue;

        // -----------------------------------------------------
        // NinjaScript Properties
        // -----------------------------------------------------
        [NinjaScriptProperty]
        [Range(1, 100000)]
        [Display(Name="Static Risk ($)", Order=1, GroupName="Parameters")]
        public double RiskDollars { get; set; }
        
        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Max Contracts Limit", Order=2, GroupName="Parameters")]
        public int MaxContracts { get; set; }

        // -----------------------------------------------------
        // State Variables & Order Objects
        // -----------------------------------------------------
        private double orbHigh = double.MinValue;
        private double orbLow = double.MaxValue;
        private int currentDay = -1;
        private bool bracketsSet = false;
        private bool ordersPlaced = false;
        private bool eodExitFired = false;
        private double entryPrice = 0;

        private Order longEntryOrderT1;
        private Order longEntryOrderT2;
        private Order shortEntryOrderT1;
        private Order shortEntryOrderT2;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = @"Asymmetric Split-Runner ORB with Breakeven Runner and Strict OCO.";
                Name                                        = "TouchORB_15M";
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

                RiskDollars                                 = 1000.0;
                MaxContracts                                = 40;
            }
            else if (State == State.DataLoaded)
            {
                globalLastTradeDate = DateTime.MinValue;
                ClearOutputWindow();
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < 2) return;

            int today = Time[0].Day;
            int currentTime = ToTime(Time[0]);

            // Daily Reset
            if (currentDay != today)
            {
                currentDay = today;
                orbHigh = double.MinValue;
                orbLow = double.MaxValue;
                bracketsSet = false;
                ordersPlaced = false;
                eodExitFired = false;
                entryPrice = 0;
                
                longEntryOrderT1 = null;
                longEntryOrderT2 = null;
                shortEntryOrderT1 = null;
                shortEntryOrderT2 = null;
            }

            // Global Lock Bypass & Cross-Chart Cancellation
            if (globalLastTradeDate == Time[0].Date) 
            {
                if (longEntryOrderT1 != null && longEntryOrderT1.OrderState == OrderState.Working) CancelOrder(longEntryOrderT1);
                if (longEntryOrderT2 != null && longEntryOrderT2.OrderState == OrderState.Working) CancelOrder(longEntryOrderT2);
                if (shortEntryOrderT1 != null && shortEntryOrderT1.OrderState == OrderState.Working) CancelOrder(shortEntryOrderT1);
                if (shortEntryOrderT2 != null && shortEntryOrderT2.OrderState == OrderState.Working) CancelOrder(shortEntryOrderT2);
                return;
            }

            // -----------------------------------------------------
            // Midday Breakeven Switch (11:30 AM EST)
            // -----------------------------------------------------
            if (currentTime >= 113000 && !eodExitFired)
            {
                // 1. Cancel any pending entry orders that never triggered
                if (longEntryOrderT1 != null && longEntryOrderT1.OrderState == OrderState.Working) CancelOrder(longEntryOrderT1);
                if (longEntryOrderT2 != null && longEntryOrderT2.OrderState == OrderState.Working) CancelOrder(longEntryOrderT2);
                if (shortEntryOrderT1 != null && shortEntryOrderT1.OrderState == OrderState.Working) CancelOrder(shortEntryOrderT1);
                if (shortEntryOrderT2 != null && shortEntryOrderT2.OrderState == OrderState.Working) CancelOrder(shortEntryOrderT2);

                // 2. Move active stops to Breakeven
                if (Position.MarketPosition == MarketPosition.Long)
                {
                    SetStopLoss("LongORB_T2", CalculationMode.Price, entryPrice, false);
                }
                else if (Position.MarketPosition == MarketPosition.Short)
                {
                    SetStopLoss("ShortORB_T2", CalculationMode.Price, entryPrice, false);
                }
                eodExitFired = true;
                return;
            }

            // -----------------------------------------------------
            // 15-Minute Range Capture (Optimized for 15m Chart)
            // -----------------------------------------------------
            if (currentTime == 94500)
            {
                orbHigh = High[0];
                orbLow = Low[0];
            }

            // -----------------------------------------------------
            // Order Execution (After 9:45 AM EST)
            // -----------------------------------------------------
            if (currentTime > 94500 && Position.MarketPosition == MarketPosition.Flat && !ordersPlaced)
            {
                if (orbHigh == double.MinValue || orbLow == double.MaxValue) return;
                
                ordersPlaced = true; // Lock execution

                // Physical Range Measurement
                double orbRange = orbHigh - orbLow;
                if (orbRange <= 0) return; // Failsafe for corrupted bars

                // Sizing Math: Static Dollar Risk with Cap
                double stopLossDollarsPerContract = orbRange * Instrument.MasterInstrument.PointValue;
                int qty = (int)Math.Floor(RiskDollars / stopLossDollarsPerContract);
                if (qty < 1) qty = 1;
                if (qty > MaxContracts) qty = MaxContracts; // Maximum Leverage Cap
                
                // Asymmetric Split-Runner Tranches
                int qtyT1 = (int)Math.Ceiling(qty / 2.0); // 50% rounded up
                int qtyT2 = qty - qtyT1;                  // The remainder
                if (qtyT2 < 1) // Failsafe if total qty was 1
                {
                    qtyT1 = 1;
                    qtyT2 = 0;
                }

                // Volatility Brackets
                int ticks = (int)Math.Round(orbRange / TickSize);
                
                if (!bracketsSet)
                {
                    // Tranche 1: The Risk Cover (1:1 Target)
                    SetStopLoss("LongORB_T1", CalculationMode.Ticks, ticks, false);
                    SetProfitTarget("LongORB_T1", CalculationMode.Ticks, ticks);
                    
                    SetStopLoss("ShortORB_T1", CalculationMode.Ticks, ticks, false);
                    SetProfitTarget("ShortORB_T1", CalculationMode.Ticks, ticks);
                    
                    if (qtyT2 > 0)
                    {
                        // Tranche 2: The Runner (1:3 Target)
                        SetStopLoss("LongORB_T2", CalculationMode.Ticks, ticks, false);
                        SetProfitTarget("LongORB_T2", CalculationMode.Ticks, ticks * 3);
                        
                        SetStopLoss("ShortORB_T2", CalculationMode.Ticks, ticks, false);
                        SetProfitTarget("ShortORB_T2", CalculationMode.Ticks, ticks * 3);
                    }
                    
                    bracketsSet = true;
                }

                // Place Stop-Market Unmanaged Orders via Managed Methods
                EnterLongStopMarket(qtyT1, orbHigh, "LongORB_T1");
                EnterShortStopMarket(qtyT1, orbLow, "ShortORB_T1");
                
                if (qtyT2 > 0)
                {
                    EnterLongStopMarket(qtyT2, orbHigh, "LongORB_T2");
                    EnterShortStopMarket(qtyT2, orbLow, "ShortORB_T2");
                }
                
                Print(Time[0] + " - Placed Split-Runner Orders: ORB Range " + orbRange + " | Qty " + qty + " (T1: " + qtyT1 + ", T2: " + qtyT2 + ")");
            }
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled, double averageFillPrice, OrderState orderState, DateTime time, ErrorCode error, string nativeError)
        {
            if (order.Name == "LongORB_T1") longEntryOrderT1 = order;
            if (order.Name == "LongORB_T2") longEntryOrderT2 = order;
            if (order.Name == "ShortORB_T1") shortEntryOrderT1 = order;
            if (order.Name == "ShortORB_T2") shortEntryOrderT2 = order;
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity, MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution.Order != null && execution.Order.OrderState == OrderState.Filled)
            {
                // Capture Entry Price, OCO Cancellation Logic & Global Lock
                if (execution.Order.Name.StartsWith("LongORB"))
                {
                    globalLastTradeDate = time.Date;
                    entryPrice = execution.Order.AverageFillPrice;
                    if (shortEntryOrderT1 != null && shortEntryOrderT1.OrderState == OrderState.Working) CancelOrder(shortEntryOrderT1);
                    if (shortEntryOrderT2 != null && shortEntryOrderT2.OrderState == OrderState.Working) CancelOrder(shortEntryOrderT2);
                }
                else if (execution.Order.Name.StartsWith("ShortORB"))
                {
                    globalLastTradeDate = time.Date;
                    entryPrice = execution.Order.AverageFillPrice;
                    if (longEntryOrderT1 != null && longEntryOrderT1.OrderState == OrderState.Working) CancelOrder(longEntryOrderT1);
                    if (longEntryOrderT2 != null && longEntryOrderT2.OrderState == OrderState.Working) CancelOrder(longEntryOrderT2);
                }
            }
        }
    }
}
