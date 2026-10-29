"""Offload cheap, non-sensitive text jobs (summaries, log digests, formatting) to the local FreeLLMAPI router
(data\\tools\\freellmapi, http://127.0.0.1:3001, free-tier models, NOT frontier quality). Never use it for trading
calls, live-risk decisions or anything from the MT5 / Notion / broker setup: those stay with Claude.
The unified key is read from FREELLMAPI_KEY or data/tools/freellmapi/.unified_key (outside this repo; never commit it).
Usage: python forex/tools/llm_offload.py "prompt" [--file PATH] [--max-tokens N] [--model auto]"""
import os, re, sys, json, argparse, urllib.request

URL = "http://127.0.0.1:3001/v1/chat/completions"
KEY_FILE = "data/tools/freellmapi/.unified_key"
BLOCKED_PATHS = re.compile(r"(^|[\\/])(\.env[^\\/]*|.*secret.*|.*credential.*|.*token.*|.*\.key|.*\.pem)$", re.I)
SECRET_TEXT = re.compile(r"(api[_-]?key|secret|password|passwd|token|bearer)\s*[:=]|BEGIN [A-Z ]*PRIVATE KEY|sk-[A-Za-z0-9]{20,}|gsk_[A-Za-z0-9]{20,}", re.I)


def key():
    k = os.environ.get("FREELLMAPI_KEY", "").strip()
    if not k and os.path.exists(KEY_FILE): k = open(KEY_FILE, encoding="utf-8").read().strip()
    if not k: sys.exit("no unified key: set FREELLMAPI_KEY or write it to %s (copy it from the dashboard Keys page)" % KEY_FILE)
    return k


def ask(prompt, max_tokens=800, model="auto"):
    if SECRET_TEXT.search(prompt): sys.exit("refused: the prompt looks like it contains a credential")
    body = json.dumps({"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + key()})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.load(r)
        return d["choices"][0]["message"]["content"], d.get("model", "?")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("prompt"); p.add_argument("--file"); p.add_argument("--max-tokens", type=int, default=800); p.add_argument("--model", default="auto")
    a = p.parse_args()
    text = a.prompt
    if a.file:
        if BLOCKED_PATHS.search(a.file.replace("\\", "/")): sys.exit("refused: %s looks like a secrets file" % a.file)
        text += "\n\n" + open(a.file, encoding="utf-8", errors="replace").read()
    out, model = ask(text, a.max_tokens, a.model)
    print(out); print("\n[answered by %s via FreeLLMAPI]" % model, file=sys.stderr)


if __name__ == "__main__":
    main()
