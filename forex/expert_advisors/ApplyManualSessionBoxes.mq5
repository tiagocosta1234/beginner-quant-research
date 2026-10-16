//+------------------------------------------------------------------+
//| ApplyManualSessionBoxes.mq5 (script)                               |
//| Adds the ManualSessionBoxes indicator to every open chart that     |
//| does not have it yet. It only adds an indicator: it does not     |
//| touch Expert Advisors, presets, orders or other indicators.      |
//+------------------------------------------------------------------+
#property copyright "the trader"
#property version   "1.00"
#property script_show_inputs

void OnStart()
{
   int added = 0, already = 0, failed = 0;
   for(long id = ChartFirst(); id >= 0; id = ChartNext(id))
   {
      bool has = false;
      int n = ChartIndicatorsTotal(id, 0);
      for(int k = 0; k < n; k++)
         if(StringFind(ChartIndicatorName(id, 0, k), "ManualSessionBoxes") >= 0) has = true;
      if(has) { already++; continue; }

      int h = iCustom(ChartSymbol(id), ChartPeriod(id), "ManualSessionBoxes");
      if(h != INVALID_HANDLE && ChartIndicatorAdd(id, 0, h))
         added++;
      else
      {
         failed++;
         PrintFormat("ManualSessionBoxes: could not add to %s (error %d)", ChartSymbol(id), GetLastError());
      }
   }
   PrintFormat("ManualSessionBoxes: added to %d charts, already on %d, failed %d", added, already, failed);
   Alert(StringFormat("ManualSessionBoxes added to %d charts (%d already had it, %d failed)", added, already, failed));
}
