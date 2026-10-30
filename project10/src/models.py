"""Shared data structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Severity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Verdict:
    CLEAN = "CLEAN WITHIN AUDIT SCOPE"
    CAUTION = "CAUTION — REVIEW REQUIRED"
    UNSAFE = "UNSAFE — DO NOT TRUST"


# Where the data goes, per the audit's distinctions.
LOCAL = "local processing"
AI_PROVIDER = "through the configured AI provider"
EXTERNAL = "transmission to a separate external service"
ACCESS_ONLY = "data access without transmission"
DESCRIPTIVE = "describes a possible action"

AUTOMATIC = "automatic"
CONDITIONAL = "conditional"
USER_TRIGGERED = "user-triggered"


@dataclass
class Finding:
    rule_id: str
    category: str  # network | credentials | privacy | injection | script | destructive | source
    severity: Severity
    file: str
    line: int  # 1-based; 0 means the finding applies to the whole file
    evidence: str
    explanation: str
    destination: str = ""
    data_at_risk: str = ""
    trigger: str = CONDITIONAL
    data_flow: str = DESCRIPTIVE
    tags: frozenset = frozenset()
    negated: bool = False
    origin: str = "automated"  # automated | manual
    disposition: str = ""  # reviewer note, if any
    false_positive: bool = False

    @property
    def location(self) -> str:
        return f"{self.file}:{self.line}" if self.line else self.file


@dataclass
class SkillFile:
    rel: str
    path: str
    size: int
    sha256: str
    kind: str  # instruction | script | config | other | binary | asset
    text: str = ""  # decoded, newlines unified; empty if not text
    lines: list = field(default_factory=list)  # raw lines, 1-based via index + 1
    norm: str = ""  # normalized for matching; same line structure as text
    newlines: list = field(default_factory=list)  # offsets of "\n" in norm
    note: str = ""


@dataclass
class Skill:
    root: str
    mode: str  # skill | plugin
    name: str
    frontmatter: dict
    frontmatter_lines: dict
    files: list
    plugin_root: str = ""
    plugin_manifest: dict = field(default_factory=dict)
    out_of_scope: list = field(default_factory=list)
    not_analysed: list = field(default_factory=list)  # (rel, reason)
    incomplete: bool = False  # True if something that could hold behavior went unread
    load_findings: list = field(default_factory=list)


@dataclass
class SourceInfo:
    publisher: str = "not supplied"
    source: str = "not supplied"
    commit: str = "not supplied"
    install_location: str = ""
    status: str = "UNVERIFIED"
    details: list = field(default_factory=list)
    tree_sha256: str = ""
