"""Command line: `python -m src.main audit --path PATH` and `python -m src.main list`."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from .models import Finding, Severity, Verdict
from .report_generator import render
from .risk_classifier import correlate, dedupe, effective, verdict
from .skill_loader import load_skill, parse_frontmatter
from .source_verifier import verify
from .static_analyzer import analyze_skill

EXIT_CODES = {Verdict.CLEAN: 0, Verdict.CAUTION: 1, Verdict.UNSAFE: 2}
EXIT_ERROR = 3


def apply_review(skill, findings: list, review: dict) -> list:
    """Merge a human review. Citations are checked, so a manual finding can't point at evidence that isn't there."""
    by_rel = {f.rel: f for f in skill.files}
    for d in review.get("dispositions", []):
        matches = [x for x in findings if x.rule_id == d["rule_id"] and x.file == d["file"] and x.line == d["line"]]
        if not matches:
            raise ValueError(f"Review disposition matches no finding: {d['rule_id']} {d['file']}:{d['line']}")
        for x in matches:
            x.disposition = d["note"]
            if d.get("false_positive"):
                x.false_positive = True
            if d.get("severity"):
                x.severity = Severity[d["severity"]]
    for m in review.get("manual_findings", []):
        f = by_rel.get(m["file"])
        if f is None:
            raise ValueError(f"Manual finding cites a file outside the audit: {m['file']}")
        line = m["line"]
        actual = f.lines[line - 1] if 0 < line <= len(f.lines) else ""
        if m["evidence"] not in actual:
            raise ValueError(f"Manual finding evidence not on {m['file']}:{line}: {m['evidence']!r}")
        findings.append(Finding(
            m.get("rule_id", "MANUAL"), m["category"], Severity[m["severity"]], m["file"], line, m["evidence"],
            m["explanation"], destination=m.get("destination", ""), data_at_risk=m.get("data_at_risk", ""),
            trigger=m.get("trigger", "conditional"), origin="manual"))
    return dedupe(findings)


def run_audit(path, publisher=None, source=None, commit=None, install_location=None, publisher_domain="",
              marketplace_file=None, plugin_name=None, review=None):
    skill = load_skill(path)
    info, source_findings = verify(skill, publisher, source, commit, install_location, marketplace_file, plugin_name)
    findings = analyze_skill(skill) + source_findings
    findings = correlate(skill, findings, publisher_domain)
    if review:
        findings = apply_review(skill, findings, review)
    verdict_text, reason = verdict(findings, skill.incomplete)
    return skill, info, findings, verdict_text, reason


def cmd_audit(args) -> int:
    review = None
    if args.review:
        review = json.loads(Path(args.review).read_text(encoding="utf-8"))
    skill, info, findings, verdict_text, reason = run_audit(
        args.path, args.publisher, args.source, args.commit, args.install_location, args.publisher_domain or "",
        args.marketplace_file, args.plugin_name, review)
    today = date.today().isoformat()
    safe_name = re.sub(r"[^\w.-]+", "-", skill.name)[:60] or "skill"
    output = Path(args.output) if args.output else Path("reports") / f"{safe_name}-{today}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(skill, info, findings, verdict_text, reason, today, review), encoding="utf-8")

    live = effective(findings)
    print(f"Skill:    {skill.name}")
    print(f"Files:    {sum(1 for f in skill.files if f.norm)} inspected, {len(skill.not_analysed)} not analysed")
    print(f"Source:   {info.status}")
    print("Findings: " + ", ".join(f"{sum(1 for x in live if x.severity == s)} {s.name}" for s in reversed(Severity)))
    for x in [x for x in live if x.severity >= Severity.HIGH][:10]:
        print(f"  [{x.severity.name}] {x.location} {x.rule_id}")
    print(f"Verdict:  {verdict_text}")
    print(f"Report:   {output}")
    return EXIT_CODES[verdict_text]


def cmd_list(args) -> int:
    """Show skills on disk. Reads files only; nothing is loaded or run."""
    home = Path(args.home) if args.home else Path.home()
    roots = [("user", home / ".claude" / "skills"),
             ("project", Path.cwd() / ".claude" / "skills"),
             ("plugin", home / ".claude" / "plugins" / "cache"),
             ("synced", home / ".claude" / "plugins" / "synced")]
    total = 0
    for label, root in roots:
        if not root.is_dir():
            print(f"[{label}] {root}: not present")
            continue
        paths = sorted(root.rglob("SKILL.md"))
        print(f"[{label}] {root}: {len(paths)} skill(s)")
        for p in paths:
            try:
                name = parse_frontmatter(p.read_text(encoding="utf-8", errors="replace").split("\n"))[0].get("name", p.parent.name)
            except OSError:
                name = p.parent.name
            print(f"  {name}  ->  {p.parent}")
            total += 1
    print(f"Total: {total}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skill-security-auditor",
                                     description="Statically audit a Claude Code skill. Never runs the skill.")
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="audit a skill or plugin directory")
    audit.add_argument("--path", required=True, help="skill directory (holding SKILL.md) or plugin directory")
    audit.add_argument("--source", help="original source repository URL")
    audit.add_argument("--commit", help="expected commit or version")
    audit.add_argument("--publisher", help="publisher name")
    audit.add_argument("--publisher-domain", help="domain that counts as the publisher's own, e.g. example.com")
    audit.add_argument("--install-location", help="where it is installed; omit for an uninstalled source checkout")
    audit.add_argument("--marketplace-file", help="local marketplace.json to check the source against")
    audit.add_argument("--plugin-name", help="plugin name in the marketplace file")
    audit.add_argument("--review", help="JSON file with manual review notes and findings")
    audit.add_argument("--output", help="report path (default: reports/<skill>-<date>.md)")
    audit.set_defaults(func=cmd_audit)
    listing = sub.add_parser("list", help="list skills on this machine")
    listing.add_argument("--home", help=argparse.SUPPRESS)
    listing.set_defaults(func=cmd_list)
    return parser


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
