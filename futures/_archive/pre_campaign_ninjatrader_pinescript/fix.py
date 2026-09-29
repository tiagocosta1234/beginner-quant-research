import re
with open('Brokerapi_Institutional_Radar.pine', 'r', encoding='utf-8') as f:
    content = f.read()

# For Long
long_pattern = re.compile(r'(// Boundary Projection Labels\n.*?size=size\.small\)\n)(.*?)(    // Native Alert Dispatch\n    alert\(\"INSTITUTIONAL LONG)', re.DOTALL)

long_replace = r'''\1
    // Detailed Institutional Signal Label at Entry Bar
    float sweep_depth_val = lon_low - low
    string prob_str_val = "Edge: "
    if sweep_depth_val >= 3.0 and sweep_depth_val <= 6.0
        prob_str_val += "61% (Prime 3-6pt Sweep)"
    else if sweep_depth_val > 6.0 and sweep_depth_val <= 10.0
        prob_str_val += "20% (Deep Sweep)"
    else if sweep_depth_val > 10.0
        prob_str_val += "43% (Extreme Sweep)"
    else
        prob_str_val += "35% (Shallow Sweep)"
    if hour(time, tz) == 10 and minute(time, tz) >= 30
        prob_str_val := "10% Time Edge | " + prob_str_val
    label.new(bar_index, low - 2, prob_str_val, color=color.new(color.orange, 0), textcolor=color.black, style=label.style_label_up, size=size.normal)

\3'''

content = long_pattern.sub(long_replace, content)

# For Short
short_pattern = re.compile(r'(// Boundary Projection Labels\n.*?size=size\.small\)\n)(.*?)(    // Native Alert Dispatch\n    alert\(\"INSTITUTIONAL SHORT)', re.DOTALL)

short_replace = r'''\1
    // Detailed Institutional Signal Label at Entry Bar
    float sweep_depth_val_h = high - lon_high
    string prob_str_val_h = "Edge: "
    if sweep_depth_val_h >= 3.0 and sweep_depth_val_h <= 6.0
        prob_str_val_h += "61% (Prime 3-6pt Sweep)"
    else if sweep_depth_val_h > 6.0 and sweep_depth_val_h <= 10.0
        prob_str_val_h += "20% (Deep Sweep)"
    else if sweep_depth_val_h > 10.0
        prob_str_val_h += "43% (Extreme Sweep)"
    else
        prob_str_val_h += "35% (Shallow Sweep)"
    if hour(time, tz) == 10 and minute(time, tz) >= 30
        prob_str_val_h := "10% Time Edge | " + prob_str_val_h
    label.new(bar_index, high + 2, prob_str_val_h, color=color.new(color.orange, 0), textcolor=color.black, style=label.style_label_down, size=size.normal)

\3'''

content = short_pattern.sub(short_replace, content)

with open('Brokerapi_Institutional_Radar.pine', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed!')
