"""Runs ONE model-written strategy in a separate interpreter (python -I): reads sources, calls strategy(df) per source on the rows it is given, writes positions.
   python -I sandbox.py <code.py> <spec.json> <out.npz>      spec = [{"name":..., "path":..., "n": rows to use (prefix)}]"""
import ast, builtins, json, sys
import numpy as np
import pandas as pd

BAD_NAMES = {"open", "exec", "eval", "compile", "__import__", "input", "globals", "locals", "getattr", "setattr", "delattr", "breakpoint", "exit", "quit"}
OK_IMPORTS = {"numpy", "pandas", "math"}


def check(code):
    tree = ast.parse(code)
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] not in OK_IMPORTS:
                    raise ValueError(f"import {a.name} not allowed")
        elif isinstance(n, ast.ImportFrom):
            if (n.module or "").split(".")[0] not in OK_IMPORTS:
                raise ValueError(f"import from {n.module} not allowed")
        elif isinstance(n, ast.Name) and n.id in BAD_NAMES:
            raise ValueError(f"name {n.id} not allowed")
        elif isinstance(n, ast.Attribute) and n.attr.startswith("__"):
            raise ValueError("dunder attribute not allowed")
    return tree


def main():
    code_path, spec_path, out_path = sys.argv[1:4]
    code = open(code_path, encoding="utf-8").read()
    check(code)
    import math
    def safe_import(name, *a, **k):
        if name.split(".")[0] not in OK_IMPORTS:
            raise ImportError(f"import {name} not allowed")
        return builtins.__import__(name, *a, **k)

    bi = {k: v for k, v in vars(builtins).items() if k not in BAD_NAMES}
    bi["__import__"] = safe_import
    ns = {"np": np, "pd": pd, "math": math, "__builtins__": bi}
    exec(compile(code, "strategy", "exec"), ns)
    fn = ns["strategy"]
    out, errs = {}, {}
    for s in json.load(open(spec_path)):
        try:
            df = pd.read_parquet(s["path"], columns=["open", "high", "low", "close", "spread_bp", "tick_volume"]).iloc[: s["n"]].copy().reset_index(drop=True)
            p = np.asarray(fn(df.copy()), dtype=float)
            if p.shape != (len(df),) or not np.isfinite(p).all():
                raise ValueError(f"bad output shape/values {p.shape}")
            out[s["name"]] = np.clip(np.round(p), -1, 1).astype(np.int8)
        except Exception as e:
            errs[s["name"]] = f"{type(e).__name__}: {str(e)[:200]}"
    np.savez(out_path, **out)
    json.dump(errs, open(out_path + ".err.json", "w"))


if __name__ == "__main__":
    main()
