import re

file_path = 'broker_hacker\\ManualCustomBot.cs'

with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Replace Properties
old_props = '''        [NinjaScriptProperty]
        [Range(1.0, 1000.0)]
        [Display(Name = "Stop Loss (Points)", Order = 1, GroupName = "3. 5-Bar Anomaly")]
        public double StopLossPoints { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 1000.0)]
        [Display(Name = "Take Profit (Points)", Order = 2, GroupName = "3. 5-Bar Anomaly")]
        public double TakeProfitPoints { get; set; }'''

new_props = '''        [NinjaScriptProperty]
        [Range(1.0, 1000.0)]
        [Display(Name = "Target Points (1:1)", Order = 1, GroupName = "3. 5-Bar Anomaly")]
        public double TargetPoints { get; set; }'''
code = code.replace(old_props, new_props)

# 2. Replace Defaults
old_defaults = '''                StopLossPoints                              = 40.0;
                TakeProfitPoints                            = 40.0;'''
new_defaults = '''                TargetPoints                                = 40.0;'''
code = code.replace(old_defaults, new_defaults)

# 3. Replace Variable Usages
code = code.replace('StopLossPoints', 'TargetPoints')
code = code.replace('TakeProfitPoints', 'TargetPoints')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(code)

print('Successfully consolidated to TargetPoints (1:1).')
