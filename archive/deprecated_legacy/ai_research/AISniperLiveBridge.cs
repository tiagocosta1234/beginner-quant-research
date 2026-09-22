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
using System.Net.Http;
using System.Net.Http.Headers;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class AISniperLiveBridge : Strategy
    {
        private HttpClient client;
        private string apiUrl = "http://127.0.0.1:5000/predict";

        // BROKER Trackers
        private double eodWatermark = 50000.0;
        private bool isDailyPaused = false;
        private DateTime lastTickTime = DateTime.MinValue;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = @"AI Sniper Live Bridge - Connects to Python FastAPI via HTTP for real-time inference.";
                Name                                        = "AISniperLiveBridge";
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
                BarsRequiredToTrade                         = 20;
            }
            else if (State == State.Configure)
            {
                client = new HttpClient();
            }
            else if (State == State.Terminated)
            {
                if (client != null) client.Dispose();
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade) return;
            
            DateTime currentTime = Time[0];
            
            // 1. Time-Gates (09:30 to 15:55 EST & 16:59 EOD & 18:00 Reset)
            TimeSpan t0930 = new TimeSpan(9, 30, 0);
            TimeSpan t1555 = new TimeSpan(15, 55, 0);
            TimeSpan t1659 = new TimeSpan(16, 59, 0); // Trigger anywhere in the 16:59 minute
            TimeSpan t1800 = new TimeSpan(18, 0, 0);
            
            double unrealizedPnL = Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]);
            
            if (lastTickTime != DateTime.MinValue)
            {
                // Reset daily pause at 18:00
                if (currentTime.TimeOfDay >= t1800 && lastTickTime.TimeOfDay < t1800)
                {
                    isDailyPaused = false;
                }
                
                // True EOD Watermark Tracker at 16:59
                if (currentTime.TimeOfDay >= t1659 && lastTickTime.TimeOfDay < t1659)
                {
                    double totalBalance = 50000.0 + SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit + unrealizedPnL;
                    if (totalBalance > eodWatermark)
                    {
                        eodWatermark = totalBalance;
                    }
                }
            }
            lastTickTime = currentTime;
            
            // 2. Broker Daily Limits Tracker (-$2,000 Loss / +$3,000 Profit)
            double dailyProfit = 0;
            foreach (Trade trade in SystemPerformance.AllTrades)
            {
                if (trade.Exit.Time.Date == currentTime.Date)
                {
                    dailyProfit += trade.ProfitCurrency;
                }
            }
            
            double currentDailyPnl = dailyProfit + unrealizedPnL;
            if (currentDailyPnl <= -2000.0 || currentDailyPnl >= 3000.0)
            {
                if (!isDailyPaused)
                {
                    Print(currentTime + " - 🚨 BROKER DAILY LIMIT HIT! Flattening positions and locking out until 18:00 EST.");
                }
                isDailyPaused = true;
            }

            // 3. Enforce Flattening Outside RTH (15:55 Time-Gate) or if Paused
            bool isOutsideRTH = (currentTime.TimeOfDay < t0930 || currentTime.TimeOfDay >= t1555);
            
            if (isOutsideRTH || isDailyPaused)
            {
                if (Position.MarketPosition == MarketPosition.Long)
                    ExitLong("AIFlat_TimeGate", "AILong");
                else if (Position.MarketPosition == MarketPosition.Short)
                    ExitShort("AIFlat_TimeGate", "AIShort");
                    
                return; // Block API calls completely
            }

            try
            {
                // Prepare API Data
                double currentPosition = Position.MarketPosition == MarketPosition.Long ? Position.Quantity : (Position.MarketPosition == MarketPosition.Short ? -Position.Quantity : 0);

                double totalBalance = 50000.0 + SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit + unrealizedPnL;
                string jsonPayload = $@"{{
                ""timestamp"": ""{Time[0].ToString("yyyy-MM-dd HH:mm:ss")}"",
                ""open"": {Open[0]},
                ""high"": {High[0]},
                ""low"": {Low[0]},
                ""close"": {Close[0]},
                ""volume"": {Volume[0]},
                ""position"": {currentPosition},
                ""current_balance"": {totalBalance},
                ""high_water_mark"": {eodWatermark},
                ""trailing_drawdown_limit"": 2500.0
            }}";

                var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                // Blocking API Call
                var responseTask = client.PostAsync(apiUrl, content);
                responseTask.Wait(); 
                var response = responseTask.Result;
                
                if (response.IsSuccessStatusCode)
                {
                    var responseStringTask = response.Content.ReadAsStringAsync();
                    responseStringTask.Wait();
                    string responseString = responseStringTask.Result;
                    
                    if (responseString.Contains("\"target_position\""))
                    {
                        try
                        {
                            string targetPosString = responseString.Split(new string[] { "\"target_position\":" }, StringSplitOptions.None)[1].Split(',')[0].Split('}')[0].Trim();
                            int targetPosition = int.Parse(targetPosString);
                            int currentPosInt = (int)currentPosition;
                            
                            if (targetPosition != currentPosInt)
                            {
                                // Flip logic or Scaling logic
                                if (currentPosInt > 0 && targetPosition <= 0)
                                {
                                    ExitLong(currentPosInt, "AIFlat", "AILong");
                                    if (targetPosition < 0) EnterShort(Math.Abs(targetPosition), "AIShort");
                                }
                                else if (currentPosInt < 0 && targetPosition >= 0)
                                {
                                    ExitShort(Math.Abs(currentPosInt), "AIFlat", "AIShort");
                                    if (targetPosition > 0) EnterLong(targetPosition, "AILong");
                                }
                                else if (currentPosInt >= 0 && targetPosition > 0)
                                {
                                    if (targetPosition > currentPosInt)
                                        EnterLong(targetPosition - currentPosInt, "AILong");
                                    else
                                        ExitLong(currentPosInt - targetPosition, "AIFlat", "AILong");
                                }
                                else if (currentPosInt <= 0 && targetPosition < 0)
                                {
                                    if (Math.Abs(targetPosition) > Math.Abs(currentPosInt))
                                        EnterShort(Math.Abs(targetPosition) - Math.Abs(currentPosInt), "AIShort");
                                    else
                                        ExitShort(Math.Abs(currentPosInt) - Math.Abs(targetPosition), "AIFlat", "AIShort");
                                }
                            }
                        }
                        catch (Exception parseEx)
                        {
                            Print("Failed to parse API target position: " + parseEx.Message);
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Print("API Bridge Error: " + ex.Message);
            }
        }
    }
}
