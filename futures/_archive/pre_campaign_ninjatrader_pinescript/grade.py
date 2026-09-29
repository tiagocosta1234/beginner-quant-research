import re
with open('Brokerapi_Institutional_Radar.pine', 'r', encoding='utf-8') as f:
    content = f.read()

# For Long
long_pattern = re.compile(r'(    // Detailed Institutional Signal Label at Entry Bar\n    float sweep_depth_val = lon_low - low\n.*?size=size\.normal\)\n)', re.DOTALL)

long_replace = r'''    // Detailed Institutional Signal Label at Entry Bar
    float sweep_depth_val = lon_low - low
    string prob_str_val = "Grade: "
    if sweep_depth_val >= 3.0 and sweep_depth_val <= 6.0
        prob_str_val += "A (Prime 3-6pt Sweep)"
    else if sweep_depth_val > 6.0 and sweep_depth_val <= 10.0
        prob_str_val += "D (Deep Sweep)"
    else if sweep_depth_val > 10.0
        prob_str_val += "B (Extreme Sweep)"
    else
        prob_str_val += "C (Shallow Sweep)"
    if hour(time, tz) == 10 and minute(time, tz) >= 30
        prob_str_val := "Grade: F (Time Decay)"
    label.new(bar_index, sl_p, prob_str_val, color=color.new(color.orange, 0), textcolor=color.black, style=label.style_label_up, size=size.normal)
'''

content = long_pattern.sub(long_replace, content)

# For Short
short_pattern = re.compile(r'(    // Detailed Institutional Signal Label at Entry Bar\n    float sweep_depth_val_h = high - lon_high\n.*?size=size\.normal\)\n)', re.DOTALL)

short_replace = r'''    // Detailed Institutional Signal Label at Entry Bar
    float sweep_depth_val_h = high - lon_high
    string prob_str_val_h = "Grade: "
    if sweep_depth_val_h >= 3.0 and sweep_depth_val_h <= 6.0
        prob_str_val_h += "A (Prime 3-6pt Sweep)"
    else if sweep_depth_val_h > 6.0 and sweep_depth_val_h <= 10.0
        prob_str_val_h += "D (Deep Sweep)"
    else if sweep_depth_val_h > 10.0
        prob_str_val_h += "B (Extreme Sweep)"
    else
        prob_str_val_h += "C (Shallow Sweep)"
    if hour(time, tz) == 10 and minute(time, tz) >= 30
        prob_str_val_h := "Grade: F (Time Decay)"
    label.new(bar_index, sl_p, prob_str_val_h, color=color.new(color.orange, 0), textcolor=color.black, style=label.style_label_down, size=size.normal)
'''

content = short_pattern.sub(short_replace, content)

with open('Brokerapi_Institutional_Radar.pine', 'w', encoding='utf-8') as f:
    f.write(content)
print('Letter grades injected!')
