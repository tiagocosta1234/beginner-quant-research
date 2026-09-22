import re

file_path = 'ResearchBot.cs'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_setup_block = False
current_setup = ''
brace_depth = 0

for i, line in enumerate(lines):
    # Match start of a setup block
    setup_match = re.search(r'(else )?if \(ActiveSetup == StrategySetupType\.([a-zA-Z0-9_]+)\)', line)
    
    if setup_match:
        setup_name = setup_match.group(2)
        # We replace the condition
        new_lines.append(f'            if (ActiveSetup == StrategySetupType.OmniMode || ActiveSetup == StrategySetupType.{setup_name})\n')
        new_lines.append('            {\n')
        new_lines.append('                do\n')
        new_lines.append('                {\n')
        
        in_setup_block = True
        brace_depth = 1 # Account for the opening brace that follows on the next line
        continue

    if in_setup_block:
        if '{' in line:
            brace_depth += line.count('{')
        if '}' in line:
            brace_depth -= line.count('}')
        
        if brace_depth == 0:
            # We reached the end of the setup block
            new_lines.append('                } while (false);\n')
            new_lines.append('            }\n')
            in_setup_block = False
            continue
            
        # Replace 'return;' with 'break;' to safely escape the block instead of OnBarUpdate
        # We only replace isolated 'return;' or 'return ;'
        modified_line = re.sub(r'\breturn\b\s*;', 'break;', line)
        
        # We need to skip the original '{' that followed the if statement
        if brace_depth == 1 and '{' in line and not modified_line.strip() == '{':
            # It's not just the opening brace, it's code. Wait, standard C# style has '{' on its own line
            pass
        elif brace_depth == 1 and modified_line.strip() == '{':
            continue # skip the original opening brace
            
        new_lines.append(modified_line)
    else:
        new_lines.append(line)

with open('ResearchBot_Omni.cs', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Refactoring complete.')
