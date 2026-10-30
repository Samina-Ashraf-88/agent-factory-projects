"""Credentials and secrets: references, reads, printing, storage, and hardcoded values."""
from __future__ import annotations

import re

from .models import ACCESS_ONLY, Finding, LOCAL, Severity, SkillFile
from .scanning import SECRET_PATTERNS, Rule, _ASSIGNED_SECRET, _CONN_STRING, evidence_for, is_placeholder, line_of, scan

SOURCE = ("cred_source",)
FILE_SOURCE = ("cred_source", "cred_file")
_SECRET_NAME = r"[A-Z][A-Z0-9_]*(?:TOKEN|API_?KEY|SECRET|PASSWORD|PASSWD|PWD|CREDENTIALS?|ACCESS_KEY|PRIVATE_KEY|COOKIE|AUTH)[A-Z0-9_]*"
_CRED_WORDS = (r"(?:api[ _-]?keys?|(?:access|refresh|auth|bearer|session|personal access|oauth)[ _-]?tokens?|tokens?|"
               r"passwords?|passphrases?|credentials?|secrets?|ssh keys?|private keys?|cookies?)")

RULES = [
    Rule("CRED_ENV_NAME", "credentials", Severity.MEDIUM,
         rf"(?:\$\{{?|\$env:|%|getenv\(\s*[\"']|environ(?:\.get\(\s*|\[\s*)[\"']|process\.env\.|process\.env\[\s*[\"'])?\b{_SECRET_NAME}\b",
         "Refers to an environment variable that holds a credential. Check that only the matching service receives it.",
         tags=SOURCE, data_flow=ACCESS_ONLY, data_at_risk="the credential in this variable", flags=0),
    Rule("CRED_ENV_DUMP", "credentials", Severity.HIGH,
         r"(?:^|[|;&\s`(])(?:printenv|env)\s*(?:$|[|>;&)`])|\bos\.environ\b(?!\s*(?:\[|\.get\b))"
         r"|\bprocess\.env\b(?!\s*[.\[])|Get-ChildItem\s+env:|\bdump\b[^.\n]{0,30}\benv|"
         r"\b(?:all|every|entire)\s+(?:the\s+)?environment\s+variables\b",
         "Reads every environment variable at once. These usually include unrelated secrets.",
         tags=FILE_SOURCE, data_flow=ACCESS_ONLY, data_at_risk="all environment variables"),
    Rule("CRED_SENSITIVE_FILE", "credentials", Severity.HIGH,
         r"(?:~|\$HOME|%USERPROFILE%|\$env:USERPROFILE|/home/\w+|/Users/\w+)?[/\\]?"
         r"(?:\.ssh(?:[/\\]\S*)?|id_(?:rsa|ed25519|ecdsa|dsa)\b|\.aws[/\\]credentials|\.netrc\b|\.git-credentials\b|"
         r"\.npmrc\b|\.pypirc\b|\.docker[/\\]config\.json|\.kube[/\\]config|\.config[/\\]gcloud\S*|"
         r"\.claude[/\\]\.credentials\.json|\.gnupg\b|Login Data\b|cookies\.sqlite|Local State\b)",
         "Names a file that commonly stores passwords, keys, or tokens for unrelated services.",
         tags=FILE_SOURCE, data_flow=ACCESS_ONLY, data_at_risk="credentials stored in this file"),
    Rule("CRED_DOTENV", "credentials", Severity.HIGH,
         r"(?<![\w.-])\.env(?:\.[a-z]+)?\b(?!\.)",
         "A .env file usually holds a project's secrets.",
         tags=FILE_SOURCE, data_flow=ACCESS_ONLY, data_at_risk="project secrets"),
    Rule("CRED_APP_FILE", "credentials", Severity.MEDIUM,
         r"(?:~|\$HOME|%USERPROFILE%)[/\\][\w./\\-]*(?:cli|cred\w*|auth\w*|token\w*|config|secrets?)\.(?:json|ya?ml|toml|ini)\b",
         "Names a file in your home folder that may hold saved credentials. Check who reads it and how it is protected.",
         data_flow=ACCESS_ONLY, data_at_risk="saved credentials in this file"),
    Rule("CRED_PRINT", "credentials", Severity.HIGH,
         rf"\b(?:print|echo|display|show|log|output|cat|type|reveal|paste)\b[^.\n]{{0,40}}(?:\$\{{?{_SECRET_NAME}|\b{_CRED_WORDS}\b)",
         "Writes a credential where it can be seen in logs, chat, or terminal history.",
         tags=("cred_print",), data_flow=ACCESS_ONLY, data_at_risk="the credential"),
    Rule("CRED_COPY", "credentials", Severity.HIGH,
         rf"\b(?:copy|extract|harvest|collect|steal|grab|scrape)\b[^.\n]{{0,40}}\b{_CRED_WORDS}\b",
         "Instructs gathering credentials.", tags=SOURCE + ("cred_collect",),
         data_flow=ACCESS_ONLY, data_at_risk="credentials"),
    Rule("CRED_STORE_PLAIN", "credentials", Severity.MEDIUM,
         rf"\b(?:store|save|write|persist)\b[^.\n]{{0,50}}\b{_CRED_WORDS}\b[^.\n]{{0,40}}\b(?:plain\s?text|unencrypted|in\s+(?:a\s+)?(?:file|the\s+repo\w*|git))\b",
         "Stores a credential where others could read it.", data_flow=LOCAL, data_at_risk="the credential"),
    Rule("CRED_ASK_USER", "credentials", Severity.MEDIUM,
         rf"\b(?:ask|prompt|request)\b[^.\n]{{0,30}}\b(?:user|them|you)\b[^.\n]{{0,30}}\b{_CRED_WORDS}\b",
         "Asks for a credential in conversation, where it enters the transcript.",
         data_flow=ACCESS_ONLY, data_at_risk="a credential you type"),
    Rule("CRED_WORD", "credentials", Severity.LOW, rf"\b{_CRED_WORDS}\b",
         "Mentions a kind of credential. No read or send on this line by itself.", negatable=False),
]

AUTH_HEADER = re.compile(r"\bAuthorization\b|\bBearer\b|(?<![\w-])-u\s|--user\b|x-api-key", re.I)


def _hardcoded(f: SkillFile) -> list:
    findings = []
    seen = set()
    def add(match_start, value, rule_id, what):
        line = line_of(f, match_start)
        if (line, rule_id) in seen:
            return
        seen.add((line, rule_id))
        if is_placeholder(value):
            findings.append(Finding(
                "CRED_PLACEHOLDER", "credentials", Severity.LOW, f.rel, line, evidence_for(f, line),
                "Looks like a placeholder, not a real secret."))
        else:
            findings.append(Finding(
                rule_id, "credentials", Severity.HIGH, f.rel, line, evidence_for(f, line),
                f"{what} The value is hidden in this report. If real, revoke it: anyone with these files has it.",
                data_flow=LOCAL, data_at_risk="the embedded secret", tags=frozenset({"secret_value"})))
    for pat in SECRET_PATTERNS:
        for m in pat.finditer(f.text if len(f.text) == len(f.norm) else f.norm):
            add(m.start(), m.group(0), "CRED_HARDCODED", "Text matches the format of a real secret.")
    for m in _ASSIGNED_SECRET.finditer(f.norm):
        add(m.start(), m.group(2), "CRED_HARDCODED", "A secret value appears to be written into this file.")
    for m in _CONN_STRING.finditer(f.norm):
        if not m.group(0).lower().startswith(("http://", "https://")) or not is_placeholder(m.group(2)):
            add(m.start(), m.group(2), "CRED_CONNECTION_STRING", "Connection string with an embedded password.")
    return findings


def analyze(f: SkillFile) -> list:
    return scan(f, RULES) + _hardcoded(f)
