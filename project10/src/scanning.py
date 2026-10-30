"""Text normalization and the rule engine shared by every scanner.

Rules match against a normalized copy of the file so hidden characters, look-alike
letters, and line wrapping cannot split a keyword. Line numbers and evidence always
come from the raw text.
"""
from __future__ import annotations

import bisect
import re
import unicodedata
from dataclasses import dataclass

from .models import AUTOMATIC, CONDITIONAL, DESCRIPTIVE, Finding, Severity, SkillFile, USER_TRIGGERED

ZERO_WIDTH = "\u200b\u200c\u200d\u2060\ufeff\u00ad\u180e\ufe0f"
BIDI = "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\u200e\u200f"
_DROP = {ord(c): None for c in ZERO_WIDTH + BIDI}
_DROP.update({cp: None for cp in range(0xE0000, 0xE0080)})  # Unicode tag characters
CONFUSABLES = str.maketrans("аеорсхіѕјԁ", "aeopcxisjd")  # Cyrillic look-alikes of Latin

URL_RE = re.compile(r"https?://[^\s\"'`<>)\]|\\]+", re.I)
SCHEMELESS_RE = re.compile(r"\b((?:[a-z0-9-]+\.)+[a-z]{2,}|\d{1,3}(?:\.\d{1,3}){3})(?::\d+)?(/[^\s\"'`<>)]*)?", re.I)
_NEGATION = re.compile(
    r"\b(?:never|do\s+not|don'?t|must\s+not|should\s+not|shouldn'?t|avoid)\b"
    r"(?!\s+(?:hesitate|forget|fail|skip|worry|refuse|mention|tell|ask|wait))",
    re.I,
)
_SENTENCE_BREAK = re.compile(r"[.!?:;\n]|\bbut\b|\bthen\b|\binstead\b", re.I)
_USER_TRIGGER = re.compile(r"\b(?:if|when|once)\s+the\s+user\b|\buser\s+(?:asks|requests|runs|chooses|wants)\b", re.I)
_AUTO_TRIGGER = re.compile(r"\b(?:always|automatically|every\s+(?:time|session|turn)|on\s+(?:startup|activation)|before\s+(?:anything|every))\b", re.I)

SECRET_PATTERNS = [
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"\bpat[A-Za-z0-9]{14}\.[a-f0-9]{32,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
_ASSIGNED_SECRET = re.compile(
    r"((?:password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)"
    r"[\"']?\s*[=:]\s*[\"']?)([^\s\"'`,;]{4,})",
    re.I,
)
_CONN_STRING = re.compile(r"\b([a-z][a-z0-9+]*://[^\s:/@]+:)([^\s@/]+)(@)", re.I)
PLACEHOLDER = re.compile(
    r"^(?:\$|\{|<|\[|%)|x{3,}|\.\.\.|example|placeholder|your|changeme|redacted|dummy|fake|test|sample|synthetic|none|null",
    re.I,
)


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text.translate(_DROP)).translate(CONFUSABLES)


def is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER.search(value))


def redact(text: str) -> str:
    """Remove secret-shaped values from anything that will be displayed."""
    for pat in SECRET_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    text = _CONN_STRING.sub(lambda m: f"{m.group(1)}[REDACTED]{m.group(3)}", text)
    return _ASSIGNED_SECRET.sub(
        lambda m: m.group(0) if is_placeholder(m.group(2)) else f"{m.group(1)}[REDACTED]", text
    )


def line_of(f: SkillFile, offset: int) -> int:
    return bisect.bisect_left(f.newlines, offset) + 1


def line_text(f: SkillFile, line: int) -> str:
    return f.lines[line - 1] if 0 < line <= len(f.lines) else ""


def evidence_for(f: SkillFile, line: int, max_len: int = 180) -> str:
    """The raw line, redacted, with invisible characters made visible and trimmed for display."""
    raw = line_text(f, line).strip()
    shown = "".join(
        f"\\u{ord(c):04x}" if c in ZERO_WIDTH + BIDI or 0xE0000 <= ord(c) <= 0xE007F else c for c in raw
    )
    shown = redact(shown)
    return shown if len(shown) <= max_len else shown[: max_len - 1] + "…"


def host_of(url: str) -> str:
    m = re.match(r"(?:[a-z+]+://)?(?:[^/@\s]*@)?([^/:?#\s]+)", url.strip(), re.I)
    return m.group(1).lower().rstrip(".") if m else ""


def is_first_party(destination: str, publisher_domain: str) -> bool:
    if not destination or not publisher_domain:
        return False
    host = host_of(destination)
    domain = publisher_domain.lower().lstrip(".")
    return host == domain or host.endswith("." + domain)


def destination_in(text: str) -> str:
    m = URL_RE.search(text)
    if m:
        return m.group(0).rstrip(".,;:")
    m = SCHEMELESS_RE.search(text)
    return m.group(0).rstrip(".,;:") if m else ""


def is_negated(f: SkillFile, start: int) -> bool:
    """True when the match sits in a sentence that forbids it, e.g. 'Never log tokens'."""
    prefix = f.norm[max(0, start - 120) : start]
    parts = _SENTENCE_BREAK.split(prefix)
    return bool(_NEGATION.search(parts[-1])) if parts else False


def trigger_for(f: SkillFile, line_str: str) -> str:
    if _USER_TRIGGER.search(line_str):
        return USER_TRIGGERED
    if _AUTO_TRIGGER.search(line_str):
        return AUTOMATIC
    return CONDITIONAL


@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    severity: Severity
    pattern: str
    explanation: str
    tags: tuple = ()
    data_flow: str = DESCRIPTIVE
    data_at_risk: str = ""
    negatable: bool = True
    kinds: tuple = ()  # empty means every text file
    wants_destination: bool = False
    flags: int = re.I

    def compiled(self):
        return _compile(self.pattern, self.flags)


_CACHE: dict = {}


def _compile(pattern, flags):
    key = (pattern, flags)
    if key not in _CACHE:
        _CACHE[key] = re.compile(pattern, flags)
    return _CACHE[key]


def scan(f: SkillFile, rules) -> list:
    findings = []
    for rule in rules:
        if rule.kinds and f.kind not in rule.kinds:
            continue
        for m in rule.compiled().finditer(f.norm):
            line = line_of(f, m.start())
            line_str = _norm_line(f, line)
            negated = rule.negatable and is_negated(f, m.start())
            dest = ""
            if rule.wants_destination:
                dest = destination_in(m.group(0)) or destination_in(line_str)
            explanation = rule.explanation
            if negated:
                explanation = "Stated as a prohibition, not an instruction to do this. " + explanation
            findings.append(
                Finding(
                    rule_id=rule.id,
                    category=rule.category,
                    severity=Severity.LOW if negated else rule.severity,
                    file=f.rel,
                    line=line,
                    evidence=evidence_for(f, line),
                    explanation=explanation,
                    destination=redact(dest),
                    data_at_risk=rule.data_at_risk,
                    trigger=trigger_for(f, line_str),
                    data_flow=rule.data_flow,
                    tags=frozenset(() if negated else rule.tags),
                    negated=negated,
                )
            )
    return findings


def _norm_line(f: SkillFile, line: int) -> str:
    start = f.newlines[line - 2] + 1 if line >= 2 else 0
    end = f.newlines[line - 1] if line - 1 < len(f.newlines) else len(f.norm)
    return f.norm[start:end]
