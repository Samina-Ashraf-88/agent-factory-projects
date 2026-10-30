"""External communication: commands, libraries, webhooks, installs, uploads, remote code."""
from __future__ import annotations

import re

from .models import EXTERNAL, Finding, Severity, SkillFile
from .scanning import URL_RE, Rule, evidence_for, line_of, redact, scan

REGISTRIES = (("npm|npx|pnpm|yarn", "registry.npmjs.org"), ("pip3?|pipx|uv|uvx", "pypi.org"),
              ("gem", "rubygems.org"), ("cargo", "crates.io"))
SINK = ("net_sink",)
_DEST = {"wants_destination": True, "data_flow": EXTERNAL}

RULES = [
    Rule("NET_COMMAND", "network", Severity.MEDIUM,
         r"(?<![\w-])(?:curl|wget|Invoke-WebRequest|Invoke-RestMethod|iwr|irm|scp|sftp|rsync|ncat|nc|ftp)\s+[^\n]{0,200}",
         "Command that contacts another machine. Check what it sends and where.", tags=SINK, **_DEST),
    Rule("NET_PY_LIB", "network", Severity.MEDIUM,
         r"\b(?:requests|httpx|aiohttp)\.(?:get|post|put|patch|delete|request|Client|AsyncClient|ClientSession)\b"
         r"|\burllib\.request\b|\burlopen\s*\(|\bhttp\.client\b|\bsocket\.(?:socket|create_connection)\b|\bsmtplib\b|\bftplib\b",
         "Python networking code. Runs if this script is executed.", tags=SINK, **_DEST),
    Rule("NET_JS_LIB", "network", Severity.MEDIUM,
         r"(?<![\w.])fetch\s*\(|\baxios\b|\bXMLHttpRequest\b|\bhttps?\.(?:request|get)\s*\(|\bnew\s+WebSocket\b"
         r"|\bsendBeacon\b|\bnode-fetch\b|\bundici\b|\bnet\.connect\b",
         "JavaScript networking code. Runs if this script is executed.", tags=SINK, **_DEST),
    Rule("NET_BROWSER", "network", Severity.MEDIUM,
         r"\b(?:playwright|puppeteer|selenium|chromedriver)\b",
         "Browser automation can load any site and act with whatever sessions that browser holds.",
         data_at_risk="browser pages and sessions", **_DEST),
    Rule("NET_COLLECTOR", "network", Severity.HIGH,
         r"\b(?:webhook\.site|requestbin\.\w+|pipedream\.net|ngrok(?:-free)?\.(?:io|app|dev)|transfer\.sh|pastebin\.com|"
         r"oast\.\w+|interact\.sh|burpcollaborator\.net|hooks\.slack\.com|discord(?:app)?\.com/api/webhooks)\S*",
         "Service commonly used to catch data sent from another machine. Rarely needed by a legitimate skill.",
         tags=SINK, **_DEST),
    Rule("NET_WEBHOOK", "network", Severity.LOW, r"\bwebhooks?\b",
         "Mentions webhooks. A mention sends nothing; a real send is flagged separately.", negatable=False),
    Rule("NET_MCP_MENTION", "network", Severity.LOW, r"\bMCP\s+server\b",
         "Mentions an MCP server. Servers that are actually configured are reported from .mcp.json.", negatable=False),
    Rule("NET_PACKAGE", "network", Severity.MEDIUM,
         r"(?<![\w-])(?:npm\s+(?:install|i|add)|pnpm\s+(?:add|install)|yarn\s+(?:global\s+)?add|npx|bunx|uvx|"
         r"pip3?\s+install|pipx\s+(?:install|run)|uv\s+(?:add|pip\s+install|tool\s+install)|gem\s+install|cargo\s+install|"
         r"go\s+install|brew\s+install|apt(?:-get)?\s+install|winget\s+install|choco\s+install)\s+[^\n|&;]{0,120}",
         "Downloads and installs third-party code from a registry. The package's contents are not part of this audit.",
         data_flow=EXTERNAL, wants_destination=False, tags=("package",)),
    Rule("NET_GIT", "network", Severity.MEDIUM, r"\bgit\s+(?:clone|pull|fetch|submodule\s+add)\s+[^\n]{0,160}",
         "Downloads code from a remote repository at run time.", **_DEST),
    Rule("NET_UPLOAD", "network", Severity.HIGH,
         r"\b(?:upload|send|post|put|transmit|forward|exfiltrate|submit|sync|copy)\b[^.\n]{0,140}?\b(?:to|at|into)\b[^.\n]{0,60}?https?://[^\s\"'`)]+",
         "Instructs sending data to a remote address.", tags=SINK + ("upload",), **_DEST),
    Rule("NET_CURL_DATA", "network", Severity.HIGH,
         r"(?<![\w-])(?:curl|wget)\s(?:[^\n]{0,200}?\s)?(?:-F\s|-T\s|--form\b|--upload-file\b|--data(?:-binary|-raw|-urlencode)?\b|-d\s|--post-file\b)[^\n]{0,200}",
         "Network command that sends data, not just fetches it.", tags=SINK + ("upload",), **_DEST),
    # Remote code execution
    Rule("RCE_PIPE_SHELL", "script", Severity.HIGH,
         r"(?:curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\b[^\n]{0,200}\|\s*(?:sudo\s+)?(?:ba|z|da|k)?sh\b"
         r"|(?:curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\b[^\n]{0,200}\|\s*(?:python3?|node|ruby|perl|iex|Invoke-Expression|pwsh|powershell)\b"
         r"|(?:ba)?sh\s+(?:-c\s+)?[\"']?(?:<\(|\$\()\s*(?:curl|wget)\b[^\n]{0,200}"
         r"|(?:iex|Invoke-Expression)\b[^\n]{0,80}(?:iwr|irm|Invoke-WebRequest|Invoke-RestMethod|DownloadString)\b[^\n]{0,200}",
         "Downloads code from the internet and runs it immediately, with no chance to inspect it first.",
         tags=("rce",), **_DEST),
    Rule("RCE_DYNAMIC_FETCH", "script", Severity.HIGH,
         r"\b(?:exec|eval)\s*\([^\n]{0,120}(?:urlopen|requests\.get|httpx\.get|fetch\s*\()[^\n]{0,120}",
         "Runs code fetched from the network as part of one expression.", tags=("rce",), **_DEST),
]

_DOWNLOAD = r"(?:curl|wget|iwr|Invoke-WebRequest)\b[^\n]{0,200}(?:-o\s+|-O\s+|--output\s+|>\s*|-OutFile\s+)([\w./~$\"'-]+)"
DOWNLOAD_THEN_RUN = Rule(
    "RCE_DOWNLOAD_RUN", "script", Severity.HIGH,
    _DOWNLOAD + r"[^\n]*\n(?:[^\n]*\n){0,6}?[^\n]*\b(?:ba|z)?sh\s+\1|" + _DOWNLOAD.replace("([", "(?:[").replace("+)", "+)", 1)
    + r"[^\n]*\n(?:[^\n]*\n){0,6}?[^\n]*(?:chmod\s+\+x|python3?\s+\S*|node\s+\S*)",
    "Saves a file from the internet and then runs it, split over several lines.", tags=("rce",),
    negatable=False, **_DEST)


def _registry_for(command: str) -> str:
    """The default registry; a local config can point the tool elsewhere."""
    for names, host in REGISTRIES:
        if re.search(rf"(?<![\w-])(?:{names})\b", command):
            return host
    return ""


def scan_urls(f: SkillFile, existing: list) -> list:
    """Every other URL is a reference: listed, but not treated as a place data goes."""
    used = {(x.line) for x in existing if x.destination}
    findings = []
    for m in URL_RE.finditer(f.norm):
        line = line_of(f, m.start())
        if line in used:
            continue
        url = redact(m.group(0).rstrip(".,;:"))
        findings.append(Finding(
            "NET_URL_REFERENCE", "network", Severity.LOW, f.rel, line, evidence_for(f, line),
            "URL is only mentioned. No instruction on this line sends anything to it.",
            destination=url))
    return findings


def analyze(f: SkillFile) -> list:
    findings = scan(f, RULES + [DOWNLOAD_THEN_RUN])
    for x in findings:
        if x.rule_id == "NET_PACKAGE":
            x.destination = _registry_for(x.evidence)
            x.data_at_risk = "the package request; no private data by itself"
    findings.extend(scan_urls(f, findings))
    return findings
