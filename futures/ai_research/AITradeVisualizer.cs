#region Using declarations
using System;
using System.Collections.Generic;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class AITradeVisualizer : Strategy
    {
        private string csvPath = @"ai_research\AI_Trading_Bot\full_backtest_trades.csv";
        
        public class AITrade 
        {
            public DateTime EntryTime;
            public DateTime ExitTime;
            public string Direction;
            public int Size;
            public bool IsEntered;
            public bool IsExited;
        }
        
        private List<AITrade> trades = new List<AITrade>();
        
        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"Reads full_backtest_trades.csv and perfectly replicates the AI's trades in the Strategy Analyzer to visualize them on the chart.";
                Name = "AITradeVisualizer";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 100; // Allow infinite scaling
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                BarsRequiredToTrade = 0;
            }
            else if (State == State.Configure)
            {
                trades.Clear();
                if (File.Exists(csvPath))
                {
                    try 
                    {
                        string[] lines = File.ReadAllLines(csvPath);
                        // Skip header row
                        for (int i = 1; i < lines.Length; i++)
                        {
                            if (string.IsNullOrWhiteSpace(lines[i])) continue;
                            string[] cols = lines[i].Split(',');
                            if (cols.Length >= 4)
                            {
                                AITrade t = new AITrade();
                                t.EntryTime = DateTime.Parse(cols[0].Trim());
                                t.ExitTime = DateTime.Parse(cols[1].Trim());
                                t.Direction = cols[2].Trim();
                                t.Size = int.Parse(cols[3].Trim());
                                t.IsEntered = false;
                                t.IsExited = false;
                                trades.Add(t);
                            }
                        }
                        Print("✅ Loaded " + trades.Count + " AI Trades from CSV.");
                    } 
                    catch (Exception ex)
                    {
                        Print("Error parsing CSV: " + ex.Message);
                    }
                }
                else
                {
                    Print("❌ CSV File not found: " + csvPath);
                }
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < 1) return;
            DateTime currentTime = Time[0];
            
            foreach (var t in trades)
            {
                // 1. Execute Entry
                if (!t.IsEntered && currentTime >= t.EntryTime)
                {
                    string signalName = "AI_" + t.EntryTime.Ticks + "_" + Guid.NewGuid().ToString().Substring(0, 4);
                    
                    if (t.Direction == "Long")
                        EnterLong(t.Size, signalName);
                    else
                        EnterShort(t.Size, signalName);
                        
                    t.IsEntered = true;
                }
                
                // 2. Execute Exit
                if (t.IsEntered && !t.IsExited && currentTime >= t.ExitTime)
                {
                    if (t.Direction == "Long")
                        ExitLong(t.Size, "Exit", ""); // Blank fromEntrySignal exits FIFO
                    else
                        ExitShort(t.Size, "Exit", "");
                        
                    t.IsExited = true;
                }
            }
        }
    }
}
