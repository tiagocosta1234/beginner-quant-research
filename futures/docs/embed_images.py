import re
import base64
import os

docs_dir = r"broker_hacker\docs"
md_path = os.path.join(docs_dir, "MASTER_TRADING_JOURNAL.md")

with open(md_path, "r", encoding="utf-8") as f:
    content = f.read()

def replace_image(match):
    alt_text = match.group(1)
    filename = match.group(2)
    
    img_path = os.path.join(docs_dir, filename)
    if os.path.exists(img_path):
        with open(img_path, "rb") as img_file:
            b64_string = base64.b64encode(img_file.read()).decode("utf-8")
        return f"![{alt_text}](data:image/png;base64,{b64_string})"
    return match.group(0)

pattern = re.compile(r'!\[([^\]]*)\]\((media_[0-9]+\.png)\)')
new_content = pattern.sub(replace_image, content)

with open(md_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Successfully embedded images as Base64 strings.")
