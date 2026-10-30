"""Join single-line signals into behavior, remove noise, and compute the verdict.

The verdict is always computed here. A reviewer can annotate findings but cannot pick the verdict.
"""
from __future__ import annotations

import re
from dataclasses import replace

from .credential_scanner import AUTH_HEADER
from .models import EXTERNAL, Finding, Severity, Skill, SkillFile, Verdict
from .scanning import is_first_party

_FENCE = re.compile(r"^\s*(```|~~~)")


def block_map(f: SkillFile) -> list:
    """Block id per line. A code fence or paragraph is one block; a script is one block."""
    if f.kind != "instruction":
        return [0] * len(f.lines)
    ids, current, in_fence = [], 0, False
    for raw in f.lines:
        if _FENCE.match(raw):
            current += 1
            ids.append(current)
            in_fence = not in_fence
            if not in_fence:
                current += 1
            continue
        if not in_fence and not raw.strip():
            current += 1
        ids.append(current)
    return ids


def _block(ids: list, line: int) -> int:
    return ids[line - 1] if 0 < line <= len(ids) else -1


def _block_text(f: SkillFile, ids: list, block: int) -> str:
    return "\n".join(l for l, b in zip(f.lines, ids) if b == block)


def correlate_file(f: SkillFile, findings: list, publisher_domain: str) -> list:
    """Credentials or private data near a network sink is what turns mentions into exfiltration."""
    ids = block_map(f)
    mine = [x for x in findings if x.file == f.rel and x.line and not x.negated]
    sources = [x for x in mine if "cred_source" in x.tags]
    data = [x for x in mine if "private_data" in x.tags]
    sinks = [x for x in mine if "net_sink" in x.tags]
    out, seen = [], set()

    for sink in sinks:
        sink_block = _block(ids, sink.line)
        first_party = is_first_party(sink.destination, publisher_domain)
        dest = sink.destination or "an unidentified destination"
        for src in sources:
            distance = abs(_block(ids, src.line) - sink_block)
            if distance > 2:
                continue
            key = ("cred", src.line, sink.line)
            if key in seen:
                continue
            seen.add(key)
            text = _block_text(f, ids, sink_block)
            is_auth = bool(AUTH_HEADER.search(text)) and "upload" not in sink.tags
            sensitive_file = "cred_file" in src.tags
            if distance > 0:
                sev, why = Severity.HIGH, (
                    f"A credential is referenced close to a network send to {dest}, in separate blocks. "
                    "This may be exfiltration split apart. Read the two passages together.")
            elif sensitive_file:
                sev, why = Severity.CRITICAL, (
                    f"Reads a sensitive credential source and sends over the network to {dest}. "
                    "Nothing about this needs another service's secrets.")
            elif first_party and is_auth:
                sev, why = Severity.MEDIUM, (
                    f"Uses a credential to authenticate to the publisher's own service ({dest}). Expected for an API "
                    "integration, but it does mean this skill handles that credential.")
            elif first_party:
                sev, why = Severity.HIGH, f"Sends a credential to the publisher's domain ({dest}) outside a normal auth header."
            elif is_auth:
                sev, why = Severity.HIGH, f"Sends a credential as authentication to {dest}, which is not the declared publisher."
            else:
                sev, why = Severity.CRITICAL, f"Reads a credential and sends it to {dest}. This is credential exfiltration."
            out.append(Finding(
                "EXFIL_CREDENTIAL", "credentials", sev, f.rel, sink.line, sink.evidence, why,
                destination=sink.destination, data_at_risk=src.data_at_risk or "credential",
                trigger=sink.trigger, data_flow=EXTERNAL, tags=frozenset({"exfil"})))
        for item in data:
            if _block(ids, item.line) != sink_block:
                continue
            key = ("data", item.line, sink.line)
            if key in seen:
                continue
            seen.add(key)
            convo = "conversation" in item.tags
            sev = Severity.MEDIUM if first_party else (Severity.CRITICAL if convo else Severity.HIGH)
            out.append(Finding(
                "EXFIL_DATA", "privacy", sev, f.rel, sink.line, sink.evidence,
                f"Private data ({item.data_at_risk}) is sent to {dest}.",
                destination=sink.destination, data_at_risk=item.data_at_risk, trigger=sink.trigger,
                data_flow=EXTERNAL, tags=frozenset({"exfil"})))
    return out


def correlate(skill: Skill, findings: list, publisher_domain: str = "") -> list:
    """Add joined findings and suppress line-level noise they make redundant."""
    extra = []
    for f in skill.files:
        if f.norm:
            extra += correlate_file(f, findings, publisher_domain)
    merged = findings + extra
    # An explicit upload to the publisher's own domain is integration, not an unexplained transfer.
    adjusted = []
    for x in merged:
        if x.rule_id in {"NET_UPLOAD", "NET_CURL_DATA"} and is_first_party(x.destination, publisher_domain):
            x = replace(x, severity=Severity.MEDIUM,
                        explanation=x.explanation + " The destination is the declared publisher's domain.")
        adjusted.append(x)
    return dedupe(adjusted)


def dedupe(findings: list) -> list:
    best = {}
    for x in findings:
        key = (x.rule_id, x.file, x.line, x.destination, x.explanation)
        if key not in best or x.severity > best[key].severity:
            best[key] = x
    # A credential word is noise on a line that already has a stronger credential finding.
    strong = {(x.file, x.line) for x in best.values()
              if x.category == "credentials" and x.rule_id != "CRED_WORD"}
    # A URL is not a mere mention on a line that already reports it as a destination.
    routed = {(x.file, x.line) for x in best.values()
              if x.category == "network" and x.destination and x.rule_id != "NET_URL_REFERENCE"}
    kept = [x for x in best.values()
            if not (x.rule_id == "CRED_WORD" and (x.file, x.line) in strong)
            and not (x.rule_id == "NET_URL_REFERENCE" and (x.file, x.line) in routed)]
    return sorted(kept, key=lambda x: (-x.severity, x.file, x.line, x.rule_id))


def effective(findings: list) -> list:
    return [x for x in findings if not x.false_positive]


def verdict(findings: list, incomplete: bool) -> tuple:
    """Return (verdict, reasons). Unread files block a clean verdict: absence of evidence isn't evidence."""
    live = effective(findings)
    top = max((x.severity for x in live), default=None)
    counts = {s: sum(1 for x in live if x.severity == s) for s in Severity}
    summary = ", ".join(f"{counts[s]} {s.name}" for s in reversed(Severity))
    if top == Severity.CRITICAL:
        return Verdict.UNSAFE, f"At least one CRITICAL finding ({summary})."
    if top in (Severity.HIGH, Severity.MEDIUM):
        return Verdict.CAUTION, f"Findings need review ({summary})."
    if incomplete:
        return Verdict.CAUTION, f"No serious finding, but some files could not be inspected ({summary})."
    return Verdict.CLEAN, (
        f"No concerning behavior in the files inspected ({summary}). "
        "This is not a guarantee that the skill is safe.")
