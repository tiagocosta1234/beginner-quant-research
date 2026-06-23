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
    public class OrderFlow_Exporter : Strategy
    {
        private StreamWriter sw;
        private string filePath = @"MNQ_OrderFlow.csv";
        private double buyVolume = 0;
        private double sellVolume = 0;
        private double cumDelta = 0;
        private DateTime currentSessionDate = DateTime.MinValue;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"Exports 1-Minute OHLCV plus Tick-based Order Flow Delta to a CSV file.";
                Name = "OrderFlow_Exporter";
                Calculate = Calculate.OnBarClose; 
                IsOverlay = true;
            }
            else if (State == State.Configure)
            {
                // Add a 1-tick series to accurately track volume per tick
                AddDataSeries(BarsPeriodType.Tick, 1);
            }
            else if (State == State.DataLoaded)
            {
                try
                {
                    sw = new StreamWriter(filePath, false);
                    sw.WriteLine("Time,Open,High,Low,Close,TotalVolume,BuyVolume,SellVolume,Delta,CumDelta");
                }
                catch (Exception e)
                {
                    Print("Error opening CSV: " + e.Message);
                }
            }
            else if (State == State.Terminated)
            {
                if (sw != null)
                {
                    sw.Close();
                    sw.Dispose();
                }
            }
        }

        protected override void OnBarUpdate()
        {
            // Ensure both data series are receiving data
            if (CurrentBars[0] < 1 || CurrentBars[1] < 1) return;

            // Tick Series (BarsInProgress == 1)
            if (BarsInProgress == 1)
            {
                // Simple Tick Rule for Order Flow Imbalance
                if (Close[0] >= Close[1])
                    buyVolume += Volume[0];
                else
                    sellVolume += Volume[0];
            }
            
            // 1-Minute Series (BarsInProgress == 0)
            // Triggers exactly once when the 1-minute bar closes
            else if (BarsInProgress == 0)
            {
                // Reset Cumulative Delta on new session
                if (Time[0].Date != currentSessionDate.Date)
                {
                    cumDelta = 0;
                    currentSessionDate = Time[0].Date;
                }

                double delta = buyVolume - sellVolume;
                cumDelta += delta;

                if (sw != null)
                {
                    string line = string.Format("{0},{1},{2},{3},{4},{5},{6},{7},{8},{9}",
                        Time[0].ToString("yyyy-MM-dd HH:mm:ss"),
                        Open[0].ToString(System.Globalization.CultureInfo.InvariantCulture),
                        High[0].ToString(System.Globalization.CultureInfo.InvariantCulture),
                        Low[0].ToString(System.Globalization.CultureInfo.InvariantCulture),
                        Close[0].ToString(System.Globalization.CultureInfo.InvariantCulture),
                        Volume[0].ToString(System.Globalization.CultureInfo.InvariantCulture),
                        buyVolume.ToString(System.Globalization.CultureInfo.InvariantCulture),
                        sellVolume.ToString(System.Globalization.CultureInfo.InvariantCulture),
                        delta.ToString(System.Globalization.CultureInfo.InvariantCulture),
                        cumDelta.ToString(System.Globalization.CultureInfo.InvariantCulture)
                    );
                    sw.WriteLine(line);
                }

                // Reset internal aggregators for the next minute
                buyVolume = 0;
                sellVolume = 0;
            }
        }
    }
}
