"""Render the plain-language Markdown report.

Everything quoted from a skill is untrusted, so it only appears inside code spans. A
skill must not be able to inject headings, links, or instructions into its own report.
"""
from __future__ import annotations

from .models import Severity, Skill, SourceInfo
from .risk_classifier import effective
from .scanning import redact

NONE = "No evidence was found in the inspected files."


def code(text) -> str:
    text = redact(str(text)).replace("\n", " ").replace("\r", " ").replace("|", "\\|")
    if not text:
        return ""
    fence = "``" if "`" in text else "`"
    pad = " " if fence == "``" else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def plain(text) -> str:
    """Generated explanations can embed skill text; keep it from breaking the table."""
    return redact(str(text)).replace("\n", " ").replace("|", "\\|").replace("<", "&lt;")


def _bullets(items) -> str:
    return "\n".join(f"- {i}" for i in items) if items else f"- {NONE}"


def _facts(findings, category=None, rule_prefix=None, min_sev=Severity.LOW):
    return [x for x in effective(findings)
            if (not category or x.category == category)
            and (not rule_prefix or x.rule_id.startswith(rule_prefix))
            and x.severity >= min_sev]


def _section_external(findings, review) -> str:
    live = effective(findings)
    active = [x for x in live if x.category == "network" and x.severity > Severity.LOW]
    refs = [x for x in live if x.rule_id == "NET_URL_REFERENCE"]
    rows = [f"| {code(x.location)} | {code(x.evidence)} | {plain(x.destination) or 'not identifiable'} | "
            f"{plain(x.data_at_risk) or 'see explanation'} | {x.trigger} |" for x in active]
    out = [f"- **Network activity instructed:** {'yes' if active else 'no evidence found in the inspected files'}."]
    if rows:
        out += ["", "| Location | Instruction | Destination | Data that may be sent | When |", "|---|---|---|---|---|", *rows]
    out += ["", f"**Mentioned URLs, not endpoints ({len(refs)}):**", ""]
    out.append(_bullets(sorted({f"{plain(x.destination)} ({code(x.location)})" for x in refs})) if refs
               else "- None.")
    if review.get("external_notes"):
        out += ["", "**Reviewer notes:**", "", _bullets(review["external_notes"])]
    return "\n".join(out)


def _section_credentials(findings, review) -> str:
    creds = _facts(findings, category="credentials", min_sev=Severity.MEDIUM)
    words = [x for x in effective(findings) if x.rule_id in {"CRED_WORD", "CRED_PLACEHOLDER"} or
             (x.category == "credentials" and x.negated)]
    env = [x for x in creds if x.rule_id in {"CRED_ENV_NAME", "CRED_ENV_DUMP"}]
    files = [x for x in creds if x.rule_id in {"CRED_SENSITIVE_FILE", "CRED_DOTENV", "CRED_APP_FILE"}]
    out = [
        f"- **Passwords or tokens handled:** {'yes, see below' if creds else 'no evidence found in the inspected files'}.",
        f"- **Environment variables referenced:** {'yes: ' + ', '.join(sorted({code(x.evidence) + ' at ' + code(x.location) for x in env})) if env else 'no evidence found'}.",
        f"- **Sensitive files named:** {'yes: ' + ', '.join(sorted({code(x.location) for x in files})) if files else 'no evidence found'}.",
        f"- **Passing mentions or prohibitions (not behavior):** {len(words)}.",
        "- Credential values are never shown in this report.",
    ]
    if review.get("credential_notes"):
        out += ["", "**Reviewer notes:**", "", _bullets(review["credential_notes"])]
    return "\n".join(out)


def _section_privacy(findings, review) -> str:
    priv = _facts(findings, category="privacy", min_sev=Severity.MEDIUM)
    exfil = [x for x in priv if "exfil" in x.tags]
    out = [
        f"- **Private data categories referenced:** "
        f"{', '.join(sorted({plain(x.data_at_risk) for x in priv if x.data_at_risk})) or 'no evidence found in the inspected files'}.",
        f"- **Private data sent to a separate service:** {'yes, see the findings table' if exfil else 'no evidence found in the inspected files'}.",
        "- **AI provider:** anything Claude reads while using a skill, including the skill's own text, goes "
        "through your configured AI provider. That is how Claude Code works and is not specific to this skill.",
    ]
    if review.get("privacy_notes"):
        out += ["", "**Reviewer notes:**", "", _bullets(review["privacy_notes"])]
    return "\n".join(out)


def _findings_table(findings) -> str:
    if not findings:
        return f"{NONE}\n"
    rows = ["| Finding | File and line | Risk | Explanation |", "|---|---|---|---|"]
    for x in findings:
        risk = x.severity.name + (" (false positive)" if x.false_positive else "")
        note = plain(x.explanation)
        if x.origin == "manual":
            note = "*Manual review.* " + note
        if x.disposition:
            note += f" **Reviewer:** {plain(x.disposition)}"
        rows.append(f"| {code(x.evidence) or code(x.rule_id)} | {code(x.location)} | {risk} | {note} |")
    return "\n".join(rows) + "\n"


def _category_coverage(findings) -> str:
    labels = [("network", "External network access"), ("credentials", "Credentials and secrets"),
              ("privacy", "Private data"), ("injection", "Prompt injection and hidden instructions"),
              ("script", "Scripts and dependencies"), ("destructive", "Destructive operations"),
              ("source", "Source and version mismatch")]
    lines = []
    for cat, label in labels:
        items = [x for x in effective(findings) if x.category == cat]
        if not items:
            lines.append(f"- **{label}:** {NONE}")
        else:
            top = max(x.severity for x in items)
            lines.append(f"- **{label}:** {len(items)} finding(s), highest {top.name}.")
    return "\n".join(lines)


def _what_it_does(skill: Skill, review: dict) -> str:
    what = review.get("what_it_does", {})
    desc = skill.frontmatter.get("description", "")
    def line(label, key, fallback):
        return f"- **{label}:** {plain(what[key]) if key in what else fallback}"
    return "\n".join([
        line("Main purpose", "purpose", f"As the skill describes itself (unverified): {code(desc) or 'no description'}"),
        line("When it activates", "activates", "Claude Code decides from the description above. Needs manual review."),
        line("What it tells Claude Code to do", "instructions", "Needs manual review; see the findings below."),
        line("Tools it may use", "tools", f"Declared `allowed-tools`: {code(skill.frontmatter.get('allowed-tools', '')) or 'none declared'}."),
        line("Output", "output", "Needs manual review."),
    ])


def render(skill: Skill, info: SourceInfo, findings: list, verdict_text: str, reason: str,
           audit_date: str, review: dict | None = None) -> str:
    review = review or {}
    n_low = sum(1 for x in effective(findings) if x.severity == Severity.LOW)
    serious = [x for x in findings if x.severity > Severity.LOW or x.false_positive or x.origin == "manual"]
    low = [x for x in findings if x not in serious]
    sections = [
        "# Third-Party Skill Security Audit",
        "",
        f"> **Verdict: {verdict_text}.** {plain(reason)}",
    ]
    if review.get("one_sentence"):
        sections += [">", f"> {plain(review['one_sentence'])}"]
    sections += [
        "",
        "## 1. Skill Information",
        "",
        f"- **Skill name:** {code(skill.name)}",
        f"- **Original author or publisher:** {plain(info.publisher)}",
        f"- **Official repository or directory:** {plain(info.source)}",
        f"- **Version or commit identifier:** {plain(info.commit)}",
        f"- **Installation location:** {plain(info.install_location)}",
        f"- **Audit date:** {audit_date}",
        f"- **Source verification:** {info.status}",
    ]
    sections += [f"  - {plain(d)}" for d in info.details]
    sections += [f"  - {plain(d)}" for d in review.get("source_notes", [])]
    sections += [f"- **Fingerprint of audited files (SHA-256):** `{info.tree_sha256}`", "",
                 "## 2. What This Skill Does", "", _what_it_does(skill, review), "",
                 "## 3. External Connections", "", _section_external(findings, review), "",
                 "## 4. Credentials and Permissions", "", _section_credentials(findings, review), "",
                 "## 5. Data Privacy", "", _section_privacy(findings, review), "",
                 "## 6. Security Findings", "", "**By category:**", "", _category_coverage(findings), "",
                 _findings_table(serious)]
    if low:
        sections += [f"<details><summary>{n_low} informational (LOW) findings</summary>", "", _findings_table(low),
                     "</details>", ""]
    if review.get("automated_vs_manual"):
        sections += ["**Automated scan compared with manual review:**", "",
                     _bullets([plain(x) for x in review["automated_vs_manual"]]), ""]
    sections += ["## 7. Final Verdict", "", f"**{verdict_text}**", "", plain(reason), ""]
    if review.get("verdict_note"):
        sections += [plain(review["verdict_note"]), ""]
    sections += [
        "The verdict is computed from the findings, and a reviewer cannot select it. A clean verdict never means the "
        "skill is guaranteed safe. It means only that no concerning behavior was identified in the files and "
        "behaviors actually inspected.",
        "",
        "## Audit Scope and Limits",
        "",
        f"- **Files inspected ({sum(1 for f in skill.files if f.norm)}):**",
    ]
    sections += [f"  - {code(f.rel)} ({f.kind}, {f.size} bytes)" for f in skill.files if f.norm]
    sections.append("- **Not analysed:** " + ("" if skill.not_analysed else "nothing."))
    sections += [f"  - {code(rel)}: {plain(why)}" for rel, why in skill.not_analysed]
    if skill.out_of_scope:
        sections.append("- **Installed alongside this skill but not covered by this audit:** "
                        + ", ".join(code(s) for s in skill.out_of_scope))
    if review.get("limitations"):
        sections += [f"- {plain(x)}" for x in review["limitations"]]
    sections += [
        "- The skill was never run. Static analysis cannot see behavior of remote servers, code downloaded later, "
        "or text a model might be persuaded by in ways no pattern anticipates.",
        "- Text quoted from the skill is untrusted data, not guidance.",
        "",
    ]
    return "\n".join(sections)
