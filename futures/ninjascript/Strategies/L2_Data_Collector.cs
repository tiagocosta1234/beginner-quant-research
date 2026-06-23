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
using System.IO;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class L2_Data_Collector : Strategy
    {
        private StreamWriter writer;
        private string filePath = @"MNQ_Level2.csv";
        private List<string> buffer = new List<string>();
        private int bufferLimit = 5000;
        private object fileLock = new object();

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"Extracts historical Level 2 Order Book data during Market Replay.";
                Name = "L2_Data_Collector";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
                IsFillLimitOnTouch = false;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade = 20;
            }
            else if (State == State.Configure)
            {
                AddDataSeries(Data.BarsPeriodType.Tick, 1);
            }
            else if (State == State.DataLoaded)
            {
                try
                {
                    bool writeHeader = !File.Exists(filePath);
                    writer = new StreamWriter(filePath, true);
                    if (writeHeader)
                    {
                        writer.WriteLine("Time,Side,Operation,Position,Price,Volume");
                    }
                }
                catch (Exception e)
                {
                    Print("Failed to initialize L2 StreamWriter: " + e.Message);
                }
            }
            else if (State == State.Terminated)
            {
                FlushBuffer();
                if (writer != null)
                {
                    writer.Close();
                    writer.Dispose();
                }
            }
        }

        protected override void OnMarketDepth(MarketDepthEventArgs marketDepthUpdate)
        {
            // Only collect data during NY Power Hours to save disk space
            if (marketDepthUpdate.Time.TimeOfDay < new TimeSpan(9, 30, 0) || marketDepthUpdate.Time.TimeOfDay > new TimeSpan(11, 0, 0))
                return;

            string side = marketDepthUpdate.MarketDataType == MarketDataType.Ask ? "Ask" : "Bid";
            string operation = marketDepthUpdate.Operation.ToString();
            
            string line = string.Format("{0},{1},{2},{3},{4},{5}", 
                marketDepthUpdate.Time.ToString("yyyy-MM-dd HH:mm:ss.fff"),
                side,
                operation,
                marketDepthUpdate.Position,
                marketDepthUpdate.Price.ToString(System.Globalization.CultureInfo.InvariantCulture),
                marketDepthUpdate.Volume.ToString(System.Globalization.CultureInfo.InvariantCulture));

            lock (fileLock)
            {
                buffer.Add(line);
                if (buffer.Count >= bufferLimit)
                {
                    FlushBuffer();
                }
            }
        }

        private void FlushBuffer()
        {
            if (buffer.Count > 0 && writer != null)
            {
                try
                {
                    foreach (string s in buffer)
                    {
                        writer.WriteLine(s);
                    }
                    writer.Flush();
                    buffer.Clear();
                }
                catch (Exception e)
                {
                    Print("Error writing to L2 file: " + e.Message);
                }
            }
        }

        protected override void OnBarUpdate()
        {
            // Empty, required for strategy but we are using OnMarketDepth for data extraction
        }
    }
}
