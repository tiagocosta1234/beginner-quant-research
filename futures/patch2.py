with open('Brokerapi_Institutional_Radar.pine', 'r', encoding='utf-8') as f:
    content = f.read()

prob_logic_low = """
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
"""

prob_logic_high = """
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
"""

parts = content.split('    // Detailed Institutional Signal Label at Entry Bar')
if len(parts) == 3:
    new_content = parts[0] + prob_logic_low + parts[1] + prob_logic_high + parts[2]
    with open('Brokerapi_Institutional_Radar.pine', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Patched successfully!')
else:
    print('Could not find split points. Found', len(parts), 'parts.')
