#!/usr/bin/env python3
"""Check whether the installed weekly-study-notes skill really activates for each query.

Runs every query in a fresh `claude -p` session from the project root and watches the
stream for a Skill tool call naming weekly-study-notes. The session is stopped as soon as
the first tool call (or the final result) shows the decision.

Works on Windows (the skill-creator's run_eval.py relies on select() on pipes, which
Windows does not support, and tests a stand-in command file rather than the real skill).

Usage: python tests/trigger_eval.py [queries.json] [runs-per-query] [output.json]
"""

import json
import os
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SKILL_NAME = "weekly-study-notes"


def triggered(query: str, timeout: int = 180) -> bool:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    cmd = [shutil.which("claude") or "claude", "-p", query,
           "--output-format", "stream-json", "--verbose", "--max-turns", "2"]
    proc = subprocess.Popen(cmd, cwd=PROJECT, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)
    timer = threading.Timer(timeout, proc.kill)
    timer.start()
    try:
        for raw in proc.stdout:
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "assistant":
                for c in ev["message"].get("content", []):
                    if c.get("type") == "tool_use":
                        return c["name"] == "Skill" and SKILL_NAME in json.dumps(c.get("input", {}))
            elif ev.get("type") == "result":
                return False
        return False
    finally:
        timer.cancel()
        if proc.poll() is None:
            proc.kill()
        proc.wait()


def main():
    qfile = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "tests" / "trigger_queries.json"
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    items = json.loads(qfile.read_text(encoding="utf-8"))
    jobs = [(i, q["query"]) for i, q in enumerate(items) for _ in range(runs)]
    with ThreadPoolExecutor(max_workers=8) as ex:
        hits = list(ex.map(lambda j: triggered(j[1]), jobs))
    results = []
    for i, item in enumerate(items):
        n = sum(h for (j, _), h in zip(jobs, hits) if j == i)
        ok = (n / runs >= 0.5) == item["should_trigger"]
        results.append({**item, "triggers": n, "runs": runs, "pass": ok})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}/{runs} expected={item['should_trigger']!s:5}  "
              f"{item['query'][:70]!r}")
    passed = sum(r["pass"] for r in results)
    print(f"\n{passed}/{len(results)} queries passed")
    if out:
        out.write_text(json.dumps({"results": results, "passed": passed, "total": len(results)},
                                  indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
