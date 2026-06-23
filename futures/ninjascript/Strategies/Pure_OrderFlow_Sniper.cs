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
using System.Net;
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
    public class Pure_OrderFlow_Sniper : Strategy
    {
        private double ibHigh = double.MinValue;
        private double ibLow = double.MaxValue;
        private double ibBuyVolume = 0;
        private double ibSellVolume = 0;
        private bool isTrackingIB = false;
        private bool hasTradedToday = false;
        private Order longStopOrder = null;
        private Order shortStopOrder = null;
        private List<DateTime> highImpactNewsTimes = new List<DateTime>();
        
        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Quantity", Order=1, GroupName="Parameters")]
        public int Quantity
        { get; set; }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = @"Pure Statistical Order Flow IB Breakout Filtered by Delta.";
                Name                                        = "Pure_OrderFlow_Sniper";
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
                TimeInForce                                 = TimeInForce.Day;
                TraceOrders                                 = false;
                RealtimeErrorHandling                       = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling                          = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade                         = 20;
                
                // High Stakes Broker sizing
                Quantity = 16;
            }
            else if (State == State.Configure)
            {
                // 50 Points TP (4 ticks per point for MNQ/NQ)
                SetProfitTarget(CalculationMode.Ticks, 640);
                // 80 Points SL (4 ticks per point)
                SetStopLoss(CalculationMode.Ticks, 320);
            }
            else if (State == State.Historical)
            {
                FetchForexFactoryNews();
            }
        }

        private void FetchForexFactoryNews()
        {
            try
            {
                using (WebClient client = new WebClient())
                {
                    string json = client.DownloadString("https://nfs.faireconomy.media/ff_calendar_thisweek.json");
                    
                    // Basic string parsing to avoid Newtonsoft.Json dependency issues in NinjaTrader
                    string[] events = json.Split(new string[] { "},{" }, StringSplitOptions.None);
                    foreach (string ev in events)
                    {
                        if (ev.Contains("\"country\":\"USD\"") && ev.Contains("\"impact\":\"High\""))
                        {
                            // Extract Date
                            int dateIdx = ev.IndexOf("\"date\":\"") + 8;
                            int dateEndIdx = ev.IndexOf("\"", dateIdx);
                            if (dateIdx > 7 && dateEndIdx > dateIdx)
                            {
                                string dateStr = ev.Substring(dateIdx, dateEndIdx - dateIdx);
                                if (DateTime.TryParse(dateStr, out DateTime parsedDate))
                                {
                                    highImpactNewsTimes.Add(parsedDate);
                                    Print("Loaded Red Folder News: " + parsedDate.ToString());
                                }
                            }
                        }
                    }
                }
            }
            catch (Exception e)
            {
                Print("Error fetching Forex Factory news: " + e.Message);
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < 20) return;
            
            int timeValue = ToTime(Time[0]);
            
            // 09:30 AM EST: Reset all parameters for the new session
            if (timeValue == 93000)
            {
                ibHigh = double.MinValue;
                ibLow = double.MaxValue;
                ibBuyVolume = 0;
                ibSellVolume = 0;
                isTrackingIB = true;
                hasTradedToday = false;
                longStopOrder = null;
                shortStopOrder = null;
            }
            
            // --- RED FOLDER NEWS PROTECTION ---
            // Check if we are within 2 minutes BEFORE or 5 minutes AFTER High Impact USD News
            bool isRedFolderNewsImminent = false;
            foreach (DateTime newsTime in highImpactNewsTimes)
            {
                TimeSpan diff = newsTime - Time[0];
                if (diff.TotalMinutes <= 2 && diff.TotalMinutes >= -5)
                {
                    isRedFolderNewsImminent = true;
                    break;
                }
            }

            if (isRedFolderNewsImminent)
            {
                if (Position.MarketPosition != MarketPosition.Flat)
                {
                    ExitLong("News Flatten", "IB_Long");
                    ExitShort("News Flatten", "IB_Short");
                    Print(Time[0] + " FLATTENED DUE TO RED FOLDER NEWS!");
                }
                
                if (longStopOrder != null && longStopOrder.OrderState != OrderState.Filled)
                    CancelOrder(longStopOrder);
                if (shortStopOrder != null && shortStopOrder.OrderState != OrderState.Filled)
                    CancelOrder(shortStopOrder);
                    
                return; // Halt trading logic until news window passes
            }
            
            // 09:30 to 10:30 EST: Track Initial Balance and Order Flow
            if (isTrackingIB && timeValue >= 93000 && timeValue <= 103000)
            {
                if (High[0] > ibHigh) ibHigh = High[0];
                if (Low[0] < ibLow) ibLow = Low[0];
                
                // UpVolume/DownVolume Order Flow proxy
                if (Close[0] >= Open[0])
                    ibBuyVolume += Volume[0];
                else
                    ibSellVolume += Volume[0];
            }
            
            // Exactly 10:30 AM EST: Evaluate Order Flow and Place Breakout Orders
            if (timeValue == 103000 && !hasTradedToday)
            {
                isTrackingIB = false;
                double delta = ibBuyVolume - ibSellVolume;
                
                if (delta > 0)
                {
                    // Positive Delta -> Ignore Shorts, Place Long Stop at IB High
                    longStopOrder = EnterLongStopMarket(0, true, Quantity, ibHigh, "IB_Long");
                    Print(Time[0] + " [Positive Delta " + delta + "] Placed BUY STOP at " + ibHigh);
                }
                else if (delta < 0)
                {
                    // Negative Delta -> Ignore Longs, Place Sell Stop at IB Low
                    shortStopOrder = EnterShortStopMarket(0, true, Quantity, ibLow, "IB_Short");
                    Print(Time[0] + " [Negative Delta " + delta + "] Placed SELL STOP at " + ibLow);
                }
            }
            
            // Lock out trading after an entry occurs
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                hasTradedToday = true;
            }
            
            // Cancel unfilled pending breakout orders at 15:45 EST to avoid EOD chops
            if (timeValue >= 154500 && Position.MarketPosition == MarketPosition.Flat)
            {
                if (longStopOrder != null && longStopOrder.OrderState != OrderState.Filled)
                    CancelOrder(longStopOrder);
                if (shortStopOrder != null && shortStopOrder.OrderState != OrderState.Filled)
                    CancelOrder(shortStopOrder);
            }
        }
    }
}
