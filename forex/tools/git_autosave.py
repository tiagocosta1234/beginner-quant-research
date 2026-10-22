"""Autosave checkpoint for D:/finance/beginner-quant-research (the trader 2026-10-11: "(original wording omitted)").
Every run: stage tracked edits + NEW text files under the allowlist, refuse anything that looks like a secret, commit as the repo's
git identity (tiagocosta1234). LOCAL COMMIT ONLY (the trader 2026-10-19: every push needs his OK). Daily limit: the trader 2026-10-22 said 40 commits a day is the MINIMUM ("it can go more than 40 commits") and then "max is 90 commits a day",
so MAX_DAILY is 90 (it was a ceiling of 40 on 2026-10-19), counting every commit on HEAD, agents' included.
Run by the Windows task "TopSecretGitAutosave" every 30 min.   python D:/finance/beginner-quant-research/forex/tools/git_autosave.py
Push only when the trader has said OK:   python D:/finance/beginner-quant-research/forex/tools/git_autosave.py --push   (no force; rebases once if the remote moved)"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

MAX_DAILY = 90

NO_WINDOW = 0x08000000   # CREATE_NO_WINDOW
REPO = Path("D:/finance/beginner-quant-research")
LOG = REPO / "forex/tools/git_autosave.log"
NEW_OK = ("forex/ea_research/", "Knowledge_Base/", "forex/expert_advisors/", "forex/forward_test/", "forex/ea_batch/", "forex/tools/", "CLAUDE.md")
NEW_EXT = {".py", ".md", ".csv", ".txt", ".json", ".png", ".mq5", ".mqh", ".set", ".ps1", ".bat"}
MAX_NEW = 5_000_000
NEVER = re.compile(r"(^|/)\.env|\.key$|\.pem$|credential|secret_|token", re.I)
SECRET = re.compile(rb"(\d{8,10}:[A-Za-z0-9_-]{30,}|ghp_[A-Za-z0-9]{30,}|github_pat_|sk-[A-Za-z0-9]{20,}|password\s*=\s*\S{4,})", re.I)


def git(*a, check=True):
    r = subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW)   # pythonw has no console: without this every git call flashes a window
    if check and r.returncode: raise RuntimeError(f"git {' '.join(a)}: {r.stderr.strip()[:300]}")
    return r


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M} {msg}\n")


def commits_today():
    return len([l for l in git("log", "--since=midnight", "--format=%H").stdout.splitlines() if l.strip()])


def push():
    """Run only on the trader's explicit OK: plain push, one rebase if the remote moved, never force."""
    if git("push", "-q", "origin", "master", check=False).returncode:
        r = git("pull", "--rebase", "-q", "origin", "master", check=False)
        if r.returncode: git("rebase", "--abort", check=False); return log("push rejected and rebase conflicted: nothing pushed")
        if git("push", "-q", "origin", "master", check=False).returncode: return log("push failed after rebase")
    log("ok: pushed on the trader's OK")


def main():
    if git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() != "master": return log("skip: not on master")
    if (REPO / ".git/rebase-merge").exists() or (REPO / ".git/MERGE_HEAD").exists(): return log("skip: rebase/merge in progress")
    if "--push" in sys.argv: return push()
    n_today = commits_today()
    if n_today >= MAX_DAILY: return log(f"skip: {n_today} commits today, daily cap {MAX_DAILY}")
    tracked = [l[3:] for l in git("status", "--porcelain", "-uno").stdout.splitlines() if l[:2].strip() in ("M", "D", "MM", "AM")]
    new = [p for p in git("ls-files", "--others", "--exclude-standard").stdout.splitlines()
           if p.startswith(NEW_OK) and Path(p).suffix.lower() in NEW_EXT and "__pycache__" not in p and (REPO / p).stat().st_size <= MAX_NEW]
    stage, refused = [], []
    for p in tracked + new:
        f = REPO / p
        if p != "forex/tools/git_autosave.py" and (NEVER.search(p) or (f.exists() and f.suffix.lower() != ".png" and SECRET.search(f.read_bytes()))): refused.append(p); continue
        if not p.endswith(".pyc"): stage.append(p)
    if refused: log("refused (possible secret): " + ", ".join(refused[:10]))
    if not stage: return log("nothing to save")
    for i in range(0, len(stage), 50): git("add", "--", *stage[i:i + 50])
    if not git("diff", "--cached", "--quiet", check=False).returncode: return log("nothing staged")
    git("commit", "-q", "-m", f"quick autosave, {len(stage)} files ({dt.datetime.now():%d %b %H:%M})".lower() + "\n\nautomatic, from forex/tools/git_autosave.py")
    log(f"ok: {len(stage)} files committed locally (commit {n_today + 1} of {MAX_DAILY} today), not pushed")


if __name__ == "__main__":
    try: main()
    except Exception as e: log(f"error: {e}")
