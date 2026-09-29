with open('Brokerapi_Institutional_Radar.pine', 'r', encoding='utf-8') as f:
    content = f.read()

prob_logic_low = """
    // Detailed Institutional Signal Label at Entry Bar
    float sweep_depth = lon_low - low
    string prob_str = "Edge: "
    if sweep_depth >= 3.0 and sweep_depth <= 6.0
        prob_str += "61% (Prime 3-6pt Sweep)"
    else if sweep_depth > 6.0 and sweep_depth <= 10.0
        prob_str += "20% (Deep Sweep)"
    else if sweep_depth > 10.0
        prob_str += "43% (Extreme Sweep)"
    else
        prob_str += "35% (Shallow Sweep)"
    if hour(time, tz) == 10 and minute(time, tz) >= 30
        prob_str := "10% Time Edge | " + prob_str
    label.new(bar_index, low - 2, prob_str, color=color.new(color.orange, 0), textcolor=color.black, style=label.style_label_up, size=size.normal)
"""

prob_logic_high = """
    // Detailed Institutional Signal Label at Entry Bar
    float sweep_depth = high - lon_high
    string prob_str = "Edge: "
    if sweep_depth >= 3.0 and sweep_depth <= 6.0
        prob_str += "61% (Prime 3-6pt Sweep)"
    else if sweep_depth > 6.0 and sweep_depth <= 10.0
        prob_str += "20% (Deep Sweep)"
    else if sweep_depth > 10.0
        prob_str += "43% (Extreme Sweep)"
    else
        prob_str += "35% (Shallow Sweep)"
    if hour(time, tz) == 10 and minute(time, tz) >= 30
        prob_str := "10% Time Edge | " + prob_str
    label.new(bar_index, high + 2, prob_str, color=color.new(color.orange, 0), textcolor=color.black, style=label.style_label_down, size=size.normal)
"""

content = content.replace('    // Detailed Institutional Signal Label at Entry Bar', prob_logic_low, 1)
content = content.replace('    // Detailed Institutional Signal Label at Entry Bar', prob_logic_high, 1)

with open('Brokerapi_Institutional_Radar.pine', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched successfully!')
