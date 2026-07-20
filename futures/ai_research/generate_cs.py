import json

with open('norm_stats.json', 'r') as f:
    data = json.load(f)

mean_str = ', '.join(map(str, data['mean']))
var_str = ', '.join(map(str, data['var']))

cs_code = f"""using System;
using System.Collections.Generic;
using System.Linq;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Indicators;
using Microsoft.ML.OnnxRuntime;
using Microsoft.ML.OnnxRuntime.Tensors;

namespace NinjaTrader.NinjaScript.Strategies
{{
    public class NativeONNXTrader : Strategy
    {{
        private InferenceSession session;
        private string modelPath = @"ai_research\\AI_Trading_Bot\\ppo_mnq_sniper.onnx";

        private float[,,] lstm_hidden_state;
        private float[,,] lstm_cell_state;

        private OrderFlowVWAP vwap;
        private EMA ema200;
        private EMA ema15m;
        private EMA ema1h;
        private ATR atr14;
        private RSI rsi14;
        private RSI rsi15m;
        private ADX adx14;

        // Normalization Constants
        private double[] normMean = new double[] {{ {mean_str} }};
        private double[] normVar = new double[] {{ {var_str} }};

        protected override void OnStateChange()
        {{
            if (State == State.SetDefaults)
            {{
                Description = "Native ONNX PPO Sniper AI Execution";
                Name = "NativeONNXTrader";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
                IsFillLimitOnTouch = false;
            }}
            else if (State == State.Configure)
            {{
                try {{
                    session = new InferenceSession(modelPath);
                }} catch (Exception e) {{
                    Print("ONNX Load Error: " + e.Message);
                }}
                
                lstm_hidden_state = new float[1, 1, 256];
                lstm_cell_state = new float[1, 1, 256];
                
                // Add MTF Data Series (15m and 1h)
                AddDataSeries(Data.BarsPeriodType.Minute, 15);
                AddDataSeries(Data.BarsPeriodType.Minute, 60);
            }}
            else if (State == State.DataLoaded)
            {{
                vwap = OrderFlowVWAP(Close, NinjaTrader.NinjaScript.Indicators.OrderFlowVWAPResolution.Standard, TradingHours.String2TradingHours("CME US Index Futures RTH"), OrderFlowVWAPStandardDeviations.Three);
                ema200 = EMA(200);
                atr14 = ATR(14);
                rsi14 = RSI(14, 1);
                adx14 = ADX(14);
                
                ema15m = EMA(BarsArray[1], 200);
                rsi15m = RSI(BarsArray[1], 14, 1);
                
                ema1h = EMA(BarsArray[2], 200);
            }}
            else if (State == State.Terminated)
            {{
                session?.Dispose();
            }}
        }}

        protected override void OnBarUpdate()
        {{
            if (CurrentBar < 200 || BarsInProgress != 0) return;

            // 1. Calculate the 23 Engineered Features Natively
            double volDelta = (Close[0] > Open[0]) ? Volume[0] : -Volume[0];
            double vwapVal = vwap.VWAP[0];
            double vwapDev = (Close[0] - vwapVal) / (vwap.StdDev1[0] > 0 ? vwap.StdDev1[0] : 1.0);
            double emaDist = (Close[0] - ema200[0]) / ema200[0];
            double vwapSlope = (vwapVal - vwap.VWAP[1]) / vwap.VWAP[1];
            
            double orbActive = (Time[0].Hour == 9 && Time[0].Minute >= 30) || Time[0].Hour > 9 ? 1.0 : 0.0;
            double oHigh = High[0] * 1.01; // Mock ORB
            double oLow = Low[0] * 0.99;
            
            double atrVal = atr14[0];
            double wickRej = (Close[0] < Open[0]) ? (High[0] - Open[0]) / atrVal : (Open[0] - Low[0]) / atrVal;
            
            double rsiVal = rsi14[0];
            double adxVal = adx14[0];
            
            double posFloat = 0.0;
            if (Position.MarketPosition == MarketPosition.Long) posFloat = 1.0;
            if (Position.MarketPosition == MarketPosition.Short) posFloat = -1.0;

            // Gather all 23 features in exact order as Python
            double[] rawFeatures = new double[23]
            {{
                volDelta, vwapDev, emaDist, vwapSlope, orbActive, oHigh, oLow, atrVal,
                emaDist, wickRej, 0, 0, 0, adxVal, rsiVal,
                0, 0, 
                (Close[0] - ema15m[0]) / ema15m[0], rsi15m[0], 
                (Close[0] - ema1h[0]) / ema1h[0],
                0, posFloat, 0
            }};

            // Normalize using VecNormalize Stats
            float[] obsArray = new float[23];
            for(int i=0; i<23; i++) {{
                double std = Math.Sqrt(normVar[i] + 1e-8);
                double norm = (rawFeatures[i] - normMean[i]) / std;
                obsArray[i] = (float)Math.Max(-10.0, Math.Min(10.0, norm)); // Clip to [-10, 10]
            }}

            if (session == null) return;

            // Create ONNX Tensors
            var obsTensor = new DenseTensor<float>(obsArray, new[] {{ 1, 23 }});
            var hiddenTensor = new DenseTensor<float>(lstm_hidden_state, new[] {{ 1, 1, 256 }});
            var cellTensor = new DenseTensor<float>(lstm_cell_state, new[] {{ 1, 1, 256 }});

            var inputs = new List<NamedOnnxValue>
            {{
                NamedOnnxValue.CreateFromTensor("obs", obsTensor),
                NamedOnnxValue.CreateFromTensor("lstm_hidden", hiddenTensor),
                NamedOnnxValue.CreateFromTensor("lstm_cell", cellTensor)
            }};

            // Run Native ONNX Inference
            using (var results = session.Run(inputs))
            {{
                long actionOutput = results.First(v => v.Name == "action").AsTensor<long>().ToArray()[0];
                lstm_hidden_state = results.First(v => v.Name == "lstm_hidden_out").AsTensor<float>().ToArray();
                lstm_cell_state = results.First(v => v.Name == "lstm_cell_out").AsTensor<float>().ToArray();

                int targetPosition = (int)actionOutput - 10;
                
                // RTH Time Gate
                int timeMinutes = Time[0].Hour * 60 + Time[0].Minute;
                if (timeMinutes < 570 || timeMinutes >= 955) targetPosition = 0; // Flatten outside 09:30-15:55

                // Execute trades natively
                if (targetPosition > 0 && Position.MarketPosition != MarketPosition.Long)
                {{
                    EnterLong(targetPosition, "AI_Long");
                }}
                else if (targetPosition < 0 && Position.MarketPosition != MarketPosition.Short)
                {{
                    EnterShort(Math.Abs(targetPosition), "AI_Short");
                }}
                else if (targetPosition == 0 && Position.MarketPosition != MarketPosition.Flat)
                {{
                    ExitLong();
                    ExitShort();
                }}
            }}
        }}
    }}
}}
"""

with open('NativeONNXTrader.cs.txt', 'w') as f:
    f.write(cs_code)
