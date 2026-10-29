#!/usr/bin/env python3
"""Run the weekly-study-notes eval cases in fresh `claude -p` sessions and grade them.

Each case runs twice:
  with_skill    - cwd = project root, where .claude/skills/weekly-study-notes is installed
  without_skill - cwd = an empty directory, so the project skill is not available (baseline)

Activation is observed directly: a run "invoked the skill" only if the session emitted a
Skill tool call naming weekly-study-notes.

Usage: python tests/run_cases.py <iteration-number> [case-name ...]
       python tests/run_cases.py --regrade <iteration-number>   (re-score saved transcripts, no model calls)
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SKILL_NAME = "weekly-study-notes"
EVALS = PROJECT / ".claude" / "skills" / SKILL_NAME / "evals"
WORKSPACE = PROJECT / f"{SKILL_NAME}-workspace"

FACTS = {
    "geology-natural-activation": [
        "igneous", "sedimentary", "metamorphic", "magma", "lava", "deposition", "compaction",
        "cementation", "heat", "pressure", "fluids", "rock cycle", "plate tectonics",
        "lithospheric", "crust", "mantle", "core", "inorganic", "aggregate",
    ],
    "weekly-lecture-revision": [
        "1789", "1614", "20 june 1789|june 20, 1789|june 20 1789", "14 july 1789|july 14, 1789",
        "1793", "17,000", "july 1794", "1799", "97%", "tennis court oath", "bastille",
        "robespierre", "committee of public safety", "thermidor", "rousseau", "montesquieu",
        "independence",  # spelling fixed from "independance"
    ],
    "many-topics-exact-three": [
        "%ΔQd / %ΔP|%ΔQd/%ΔP", "(new + old) / 2|(new+old)/2|(new + old)/2", "ceteris paribus",
        "inferior", "normal good", "instant noodles", "insulin", "rent control", "minimum wage",
        "unit elastic", "CS + PS|CS+PS", "market clearing|market-clearing", "willingness to pay",
    ],
}


def prompt_text(case: str) -> str:
    raw = (EVALS / case / "prompt.md").read_text(encoding="utf-8")
    return raw.split("---", 2)[2].strip()


def run_claude(prompt: str, cwd: Path, timeout: int = 420) -> dict:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    cmd = [shutil.which("claude") or "claude", "-p", prompt,
           "--output-format", "stream-json", "--verbose"]
    start = time.time()
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, timeout=timeout)
    lines = proc.stdout.decode("utf-8", errors="replace").splitlines()
    tools, result, tokens = [], "", 0
    for line in lines:
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            for c in ev["message"].get("content", []):
                if c.get("type") == "tool_use":
                    tools.append({"name": c["name"], "input": c.get("input", {})})
        elif ev.get("type") == "result":
            result = ev.get("result", "")
            u = ev.get("usage", {})
            tokens = sum(u.get(k, 0) for k in ("input_tokens", "output_tokens",
                                               "cache_creation_input_tokens", "cache_read_input_tokens"))
    return {"tools": tools, "result": result, "tokens": tokens,
            "duration": time.time() - start, "raw": lines}


# ---------- scripted graders ----------

def split_sections(md: str):
    """Return (topic_sections, review_section_text, text_before_review, text_after_q3)."""
    parts = re.split(r"(?m)^(?=## )", md)
    topics = [p for p in parts if re.match(r"## \d+[.)]", p)]
    review = [p for p in parts if re.match(r"## Review Questions\s*$", p.splitlines()[0])] if parts else []
    idx = md.find("## Review Questions")
    before = md[:idx] if idx >= 0 else md
    return topics, (review[-1] if review else ""), before


def invoked(run):
    return any(t["name"] == "Skill" and SKILL_NAME in json.dumps(t["input"]) for t in run["tools"])


def grade(case: str, run: dict) -> list:
    md = run["result"]
    topics, review, before = split_sections(md)
    exp = []

    def add(text, ok, evidence):
        exp.append({"text": text, "passed": bool(ok), "evidence": evidence})

    skill_calls = [t["input"] for t in run["tools"] if t["name"] == "Skill"]
    if case in FACTS:
        add("The weekly-study-notes skill was invoked via the Skill tool even though the prompt does not name it.",
            invoked(run), f"Skill tool calls: {skill_calls}")
        add("The notes have at least three level-2 numbered topic headings before the Review Questions section.",
            len(topics) >= 3, f"{len(topics)} numbered topic headings: " +
            "; ".join(t.splitlines()[0] for t in topics))
        bad = [t.splitlines()[0] for t in topics
               if not (re.search(r"key terms", t, re.I) and re.search(r"(?m)^\s*[-*] \*\*[^*]+\*\*", t))]
        add("Every topic section contains a 'Key terms' list in which each term is in bold.",
            topics and not bad, f"sections missing bold key-terms list: {bad or 'none'}")
        last_h2 = re.findall(r"(?m)^## .*$", md)
        qs = re.findall(r"(?m)^\d+\.\s+\S.*$", review)
        add("The final section is '## Review Questions' and contains exactly three numbered questions.",
            last_h2 and last_h2[-1].strip() == "## Review Questions" and len(qs) == 3,
            f"last h2={last_h2[-1] if last_h2 else None!r}; numbered items={len(qs)}")
        stray = [l.strip() for l in before.splitlines() if l.strip().endswith("?")]
        tail = review.strip().splitlines()[-1] if review.strip() else ""
        add("No question appears outside the Review Questions section, and nothing follows the third review question.",
            not stray and re.match(r"3\.\s", tail.strip()),
            f"question lines outside section: {stray or 'none'}; final line: {tail[:80]!r}")
        missing = [f for f in FACTS[case] if not any(alt.lower() in md.lower() for alt in f.split("|"))]
        add("All key source facts, dates, and formulas are preserved.", not missing,
            f"missing: {missing or 'none'}")
    elif case == "unrelated-weather-climate":
        add("The weekly-study-notes skill was not invoked.", not invoked(run), f"Skill tool calls: {skill_calls}")
        sentences = len(re.findall(r"[.!?](\s|$)", md.strip()))
        add("The response directly answers in at most three sentences with no study-note structure.",
            sentences <= 3 and "Review Questions" not in md and "## " not in md,
            f"{sentences} sentences: {md[:300]!r}")
    elif case == "missing-notes-request":
        asks = re.search(r"\b(paste|share|send|attach|upload|provide)\b", md, re.I) and re.search(r"notes|material", md, re.I)
        add("The response asks the user to paste, share, or attach their notes or class material.",
            asks, md[:400])
        add("The response contains no invented study-note content (no numbered topic headings, no Review Questions).",
            not topics and "Review Questions" not in md, f"topic headings: {len(topics)}")
        exp.append({"text": "(info) skill invoked", "passed": invoked(run), "evidence": f"Skill tool calls: {skill_calls}"})
    return exp


def do_run(iteration: int, case: str, config: str, baseline_dir: Path):
    case_dir = WORKSPACE / f"iteration-{iteration}" / case
    run_dir = case_dir / config
    out = run_dir / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    prompt = prompt_text(case)
    run = run_claude(prompt, PROJECT if config == "with_skill" else baseline_dir)
    (out / "response.md").write_text(run["result"], encoding="utf-8")
    (out / "transcript.jsonl").write_text("\n".join(run["raw"]), encoding="utf-8")
    (run_dir / "timing.json").write_text(json.dumps({
        "total_tokens": run["tokens"], "duration_ms": int(run["duration"] * 1000),
        "total_duration_seconds": round(run["duration"], 1)}, indent=2))
    graded = grade(case, run)
    exp = [e for e in graded if not e["text"].startswith("(info)")]
    info = [e for e in graded if e["text"].startswith("(info)")]
    passed = sum(e["passed"] for e in exp)
    (run_dir / "grading.json").write_text(json.dumps({
        "expectations": exp,
        "summary": {"passed": passed, "failed": len(exp) - passed, "total": len(exp),
                    "pass_rate": round(passed / len(exp), 2) if exp else 0},
        "info": info,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    (case_dir / "eval_metadata.json").write_text(json.dumps({
        "eval_name": case, "prompt": prompt, "assertions": [e["text"] for e in exp]}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    return case, config, passed, len(exp), info


def parse_transcript(lines):
    tools, result = [], ""
    for line in lines:
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            tools += [{"name": c["name"], "input": c.get("input", {})}
                      for c in ev["message"].get("content", []) if c.get("type") == "tool_use"]
        elif ev.get("type") == "result":
            result = ev.get("result", "")
    return {"tools": tools, "result": result}


def regrade(iteration: int):
    for grading in sorted((WORKSPACE / f"iteration-{iteration}").glob("*/*/grading.json")):
        case, run_dir = grading.parent.parent.name, grading.parent
        run = parse_transcript((run_dir / "outputs" / "transcript.jsonl").read_text(encoding="utf-8").splitlines())
        data = json.loads(grading.read_text(encoding="utf-8"))
        exp = [e for e in grade(case, run) if not e["text"].startswith("(info)")]
        passed = sum(e["passed"] for e in exp)
        data["expectations"] = exp
        data["summary"] = {"passed": passed, "failed": len(exp) - passed, "total": len(exp),
                           "pass_rate": round(passed / len(exp), 2) if exp else 0}
        grading.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{case:30s} {run_dir.name:14s} {passed}/{len(exp)}")


def main():
    if sys.argv[1] == "--regrade":
        return regrade(int(sys.argv[2]))
    iteration = int(sys.argv[1])
    cases = sys.argv[2:] or sorted(p.name for p in EVALS.iterdir() if p.is_dir())
    baseline_dir = Path(tempfile.mkdtemp(prefix="wsn-baseline-"))
    jobs = [(c, cfg) for c in cases for cfg in ("with_skill", "without_skill")]
    with ThreadPoolExecutor(max_workers=6) as ex:
        for case, cfg, p, t, info in ex.map(lambda j: do_run(iteration, j[0], j[1], baseline_dir), jobs):
            extra = f"  {info[0]['text']}={info[0]['passed']}" if info else ""
            print(f"{case:30s} {cfg:14s} {p}/{t}{extra}", flush=True)


if __name__ == "__main__":
    main()
