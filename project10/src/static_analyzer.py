"""Instruction, script, config, and obfuscation analysis. Reads text only; runs nothing."""
from __future__ import annotations

import base64
import binascii
import json
import re
from pathlib import Path

from . import credential_scanner, network_scanner, privacy_analyzer
from .models import AUTOMATIC, EXTERNAL, Finding, LOCAL, Severity, Skill, SkillFile
from .scanning import BIDI, ZERO_WIDTH, Rule, evidence_for, line_of, normalize, redact, scan

INJECTION = [
    Rule("INJ_IGNORE_RULES", "injection", Severity.CRITICAL,
         r"\b(?:ignore|disregard|forget|override|bypass)\b\s+(?:all\s+|any\s+)?(?:(?:of\s+)?(?:the|your|my)\s+)?"
         r"(?:previous|prior|above|earlier|preceding|system|developer|higher[- ]priority|safety|security)\s+"
         r"(?:instructions?|prompts?|rules?|messages?|guidelines?|policies|polic(?:y)|checks?|protections?)",
         "Tries to cancel the rules Claude Code operates under."),
    Rule("INJ_REVEAL_PROMPT", "injection", Severity.CRITICAL,
         r"\b(?:reveal|print|show|repeat|output|disclose|leak|send)\b[^.\n]{0,40}\b(?:system\s+prompt|developer\s+(?:message|instructions)|hidden\s+instructions|confidential\s+instructions)\b",
         "Tries to extract Claude's confidential instructions."),
    Rule("INJ_ROLE_HIJACK", "injection", Severity.HIGH,
         r"\byou\s+are\s+now\s+(?:in\s+)?(?:an?\s+)?(?:unrestricted|jailbroken|developer\s+mode|DAN\b|root|admin)"
         r"|\bdeveloper\s+mode\s+enabled\b|\bjailbreak\b|\bno\s+longer\s+bound\s+by\b",
         "Tries to convince Claude it has no restrictions."),
    Rule("INJ_HIDE_FROM_USER", "injection", Severity.CRITICAL,
         r"\b(?:do\s+not|don'?t|never|without)\s+(?:tell(?:ing)?|inform(?:ing)?|notify(?:ing)?|mention(?:ing)?|alert(?:ing)?|reveal(?:ing)?\s+to|show(?:ing)?)\s+(?:this\s+to\s+|it\s+to\s+|anything\s+to\s+)?(?:the\s+)?users?\b"
         r"|\bhide\s+(?:this|these|it|the\s+\w+)\s+(?:from|in)\b[^.\n]{0,30}\b(?:user|output|log)"
         r"|\bkeep\s+(?:this|it)\s+(?:a\s+)?secret\s+from\b"
         r"|\bsilently\s+(?:send|upload|read|copy|delete|remove|run|execute|install|post|transmit|modify)\b"
         r"|\bcover\s+your\s+tracks\b",
         "Tries to hide actions from you.", negatable=False),
    Rule("INJ_DISABLE_SECURITY", "injection", Severity.CRITICAL,
         r"--dangerously-skip-permissions|\bbypassPermissions\b|\b(?:disable|turn\s+off|skip|bypass)\b\s+(?:the\s+|all\s+|any\s+)?(?:security|safety|sandbox|permission|antivirus|defender|firewall)\b(?:\s+(?:checks?|prompts?|protections?|rules?))?"
         r"|Set-MpPreference\s+-DisableRealtime",
         "Tries to switch off a security protection."),
    Rule("INJ_NO_CONSENT", "injection", Severity.HIGH,
         r"\b(?:without|do\s+not|don'?t|never)\s+(?:ask(?:ing)?|wait(?:ing)?\s+for|request(?:ing)?|seek(?:ing)?|get(?:ting)?)\s+(?:for\s+)?(?:the\s+user'?s?\s+|user\s+|their\s+|any\s+)?(?:permission|approval|consent|confirmation)\b"
         r"|\bdo\s+not\s+ask\s+(?:the\s+user\s+)?(?:first|before)\b",
         "Tells Claude to act without your approval.", negatable=False),
    Rule("INJ_CLAIM_SAFE", "injection", Severity.MEDIUM,
         r"\b(?:this|it)\s+is\s+(?:completely\s+|perfectly\s+|totally\s+|always\s+)?(?:safe|harmless|approved|authorized)\b[^.\n]{0,40}"
         r"|\bno\s+need\s+to\s+(?:review|check|verify|audit)\b|\bpre-?approved\s+by\s+(?:anthropic|the\s+user|security)\b|\bauditors?\s+should\b",
         "Claims safety without evidence. Text like this can be aimed at reviewers and auditors."),
    Rule("INJ_ARBITRARY_EXEC", "injection", Severity.HIGH,
         r"\b(?:run|execute)\s+(?:whatever|any(?:thing)?|all)\b[^.\n]{0,30}\b(?:commands?|code|scripts?|it\s+says|instructions)\b",
         "Tells Claude to run arbitrary code."),
]

DESTRUCTIVE = [
    Rule("DES_WIPE_HOME", "destructive", Severity.CRITICAL,
         r"\brm\s+(?:-[a-zA-Z-]+\s+)+(?:--no-preserve-root\s+)?[\"']?(?:~|\$HOME|\$\{HOME\}|/|/\*|/home\b|/Users\b)[/\w.*-]{0,40}[\"']?(?=\s|$|[;&|])"
         r"|\bRemove-Item\b[^\n]{0,80}(?:\$HOME|\$env:USERPROFILE|C:\\Users|~[/\\]?)[^\n]{0,40}"
         r"|\b(?:del|rd|rmdir)\s+/s\b[^\n]{0,60}(?:%USERPROFILE%|C:\\)"
         r"|\bshutil\.rmtree\s*\(\s*(?:os\.path\.expanduser\(|Path\.home\(|[\"']/|[\"']~)"
         r"|\bdd\s+[^\n]{0,60}of=/dev/|\bmkfs(?:\.\w+)?\b|\bformat\s+[a-zA-Z]:",
         "Deletes your home folder or disk, and nothing about a skill needs that."),
    Rule("DES_DELETE", "destructive", Severity.HIGH,
         r"\brm\s+-[a-zA-Z]*[rf][a-zA-Z]*\s+[^\n]{1,80}|\bRemove-Item\b[^\n]{0,40}-Recurse[^\n]{0,60}"
         r"|\bshutil\.rmtree\b|\bfs\.(?:rmSync|rm|rmdirSync)\s*\(|\bshred\b\s+\S+|\bgit\s+clean\s+-[a-z]*f[a-z]*|\bgit\s+reset\s+--hard\b"
         r"|\bgit\s+push\s+[^\n]{0,40}--force\b|\bDROP\s+(?:DATABASE|TABLE)\b|\bTRUNCATE\s+TABLE\b"
         r"|\b(?:delete|erase|wipe|destroy)\s+(?:all\s+)?(?:of\s+)?(?:the\s+)?(?:user'?s?\s+|your\s+)?(?:files|documents|home\s+(?:folder|directory)|data)\b",
         "Permanently removes or overwrites data. Check the target and whether you are asked first."),
]

SCRIPT_RULES = [
    Rule("SCR_PRIV_ESC", "script", Severity.HIGH,
         r"(?<![\w-])sudo\s+\S|\bchmod\s+(?:-R\s+)?(?:777|[ug]\+s)\b|\bchown\s+(?:-R\s+)?root\b|\brunas\s+/|\bSet-ExecutionPolicy\s+(?:Bypass|Unrestricted)"
         r"|-ExecutionPolicy\s+Bypass|\bStart-Process\b[^\n]{0,80}-Verb\s+RunAs",
         "Requests more system privileges than a normal user has."),
    Rule("SCR_PERSIST", "script", Severity.HIGH,
         r"\bcrontab\b|\bschtasks\b|\bRegister-ScheduledTask\b|>>?\s*~?/?\.?(?:bashrc|zshrc|profile|bash_profile)\b|CurrentVersion\\Run\b|\bLaunchAgents\b|\bsystemctl\s+enable\b",
         "Makes something run again later, on its own, after the task is over."),
    Rule("SCR_MODIFY_CLAUDE", "script", Severity.HIGH,
         r"(?:~|\$HOME|%USERPROFILE%)?[/\\]?\.claude[/\\](?:settings(?:\.local)?\.json|CLAUDE\.md|hooks|commands)\b",
         "Touches Claude Code's own configuration, which could widen permissions or add persistent instructions."),
    Rule("SCR_DYNAMIC_EXEC", "script", Severity.MEDIUM,
         r"(?<![\w.])(?:eval|exec)\s*\(|\bnew\s+Function\s*\(|\bos\.system\s*\(|\bsubprocess\.\w+\(|\bchild_process\b|\bInvoke-Expression\b|(?<![\w-])iex\s|\bpickle\.loads\b|\bmarshal\.loads\b|\b__import__\s*\(",
         "Runs dynamically built code or commands. Check that nothing outside the script controls what runs.",
         kinds=("script",)),
    Rule("SCR_OBFUSCATED_DECODE", "script", Severity.HIGH,
         r"\bbase64\s+(?:-d|--decode|-D)\b|\bFromBase64String\b|\batob\s*\(|\bb64decode\b|-(?:EncodedCommand|enc)\s+[A-Za-z0-9+/=]{8,}|\bcodecs\.decode\b|\bxxd\s+-r\b",
         "Decodes hidden content at run time. Legitimate skills rarely need to hide what they do."),
]
_DECODE_TO_EXEC = re.compile(
    r"(?:base64\s+(?:-d|--decode|-D)|FromBase64String|b64decode|atob\s*\(|xxd\s+-r)[^\n]{0,120}"
    r"(?:\|\s*(?:ba|z)?sh\b|\|\s*iex\b|\|\s*python|\bexec\b|\beval\b|Invoke-Expression)"
    r"|(?:\bexec\b|\beval\b|Invoke-Expression|\biex\b)[^\n]{0,120}(?:b64decode|FromBase64String|atob\s*\()"
    r"|-(?:EncodedCommand|enc)\s+[A-Za-z0-9+/=]{8,}", re.I)
_B64_BLOB = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{32,}={0,2}(?![A-Za-z0-9+/=])")
_HEX_ESCAPES = re.compile(r"(?:\\x[0-9a-fA-F]{2}){8,}")
_HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.S)
_INLINE_SHELL = re.compile(r"(?:^|\s)!`([^`\n]+)`", re.M)
_MD_REF = re.compile(r"\]\(([^)#\s]+)\)|`((?:\.{0,2}/)?(?:[\w.-]+/)+[\w.-]+\.\w+)`")
_MIXED_SCRIPT = re.compile(r"\b(?=\w*[a-zA-Z])(?=\w*[\u0400-\u04FF])\w+\b")
_DANGEROUS_TOOLS = re.compile(r"\bBash\s*(?:\(\s*\*?\s*\)|\(\s*\*\s*:?\s*\*?\s*\))?(?:\s*,|\s*$)|^\s*\*\s*$", re.M)


def _f(rule, cat, sev, f, line, why, **kw):
    return Finding(rule, cat, sev, f.rel, line, evidence_for(f, line) if line else kw.pop("evidence", ""), why, **kw)


def hidden_text(f: SkillFile) -> list:
    out = []
    for i, raw in enumerate(f.lines, start=1):
        tags = [c for c in raw if 0xE0000 <= ord(c) <= 0xE007F]
        bidi = [c for c in raw if c in BIDI]
        zw = [c for c in raw if c in ZERO_WIDTH and c not in "\u200d\ufe0f\ufeff"]
        if tags:
            decoded = "".join(chr(ord(c) - 0xE0000) for c in tags if 0x20 <= ord(c) - 0xE0000 < 0x7F)
            out.append(_f("HID_TAG_CHARS", "injection", Severity.CRITICAL, f, i,
                          f"Invisible text decodes to: {redact(decoded)[:120]!r}. You would not see this, but a model would."))
        if bidi:
            out.append(_f("HID_BIDI", "injection", Severity.HIGH, f, i,
                          "Text-direction control characters can make a line look different from what it really says."))
        if zw:
            out.append(_f("HID_ZERO_WIDTH", "injection", Severity.MEDIUM, f, i,
                          "Invisible characters inside text can split keywords to dodge review."))
        if _MIXED_SCRIPT.search(raw):
            out.append(_f("HID_LOOKALIKE", "injection", Severity.MEDIUM, f, i,
                          "A word mixes Latin and Cyrillic letters, which can disguise a keyword or domain."))
    for m in _HTML_COMMENT.finditer(f.norm):
        body = m.group(1)
        if f.kind == "instruction" and re.search(
                r"\b(?:ignore|send|upload|read|run|execute|must|always|never|do not|curl|token|secret|password)\b", body, re.I):
            out.append(_f("HID_HTML_COMMENT", "injection", Severity.HIGH, f, line_of(f, m.start()),
                          "Instruction-like text inside an HTML comment: hidden in rendered Markdown, visible to a model."))
    return out


def _scan_decoded(text: str) -> list:
    """Run the rules over decoded text in a throwaway record, so hidden payloads get judged as visible ones."""
    probe = SkillFile(rel="<decoded>", path="", size=len(text), sha256="", kind="script")
    probe.text = text.replace("\r\n", "\n")
    probe.lines = probe.text.split("\n")
    probe.norm = normalize(probe.text)
    probe.newlines = [i for i, c in enumerate(probe.norm) if c == "\n"]
    found = network_scanner.analyze(probe) + credential_scanner.analyze(probe) + scan(probe, INJECTION + DESTRUCTIVE)
    return [x for x in found if x.severity >= Severity.MEDIUM]


def encoded_payloads(f: SkillFile) -> list:
    out = []
    for m in _DECODE_TO_EXEC.finditer(f.norm):
        out.append(_f("OBF_DECODE_EXEC", "script", Severity.CRITICAL, f, line_of(f, m.start()),
                      "Decodes hidden content and runs it, which conceals what actually executes.", tags=frozenset({"rce"})))
    for m in _B64_BLOB.finditer(f.norm):
        raw = m.group(0)
        try:
            data = base64.b64decode(raw + "=" * (-len(raw) % 4), validate=True)
            text = data.decode("utf-8")
        except (binascii.Error, ValueError, UnicodeDecodeError):
            continue
        if not text or sum(c.isprintable() or c.isspace() for c in text) / len(text) < 0.85:
            continue
        inner = _scan_decoded(text)
        line = line_of(f, m.start())
        preview = redact(text.replace("\n", " "))[:100]
        if inner:
            rules = ", ".join(sorted({x.rule_id for x in inner}))
            out.append(_f("OBF_ENCODED_PAYLOAD", "script", Severity.CRITICAL, f, line,
                          f"Base64 text decodes to behavior this auditor flags ({rules}). Decoded: {preview!r}"))
        else:
            out.append(_f("OBF_ENCODED_TEXT", "script", Severity.MEDIUM, f, line,
                          f"Base64 text decodes to readable content: {preview!r}. Ask why it is encoded."))
    for m in _HEX_ESCAPES.finditer(f.norm):
        out.append(_f("OBF_HEX", "script", Severity.HIGH, f, line_of(f, m.start()),
                      "Long run of hex-escaped bytes, a common way to hide strings."))
    return out


def analyze_instructions(f: SkillFile) -> list:
    out = []
    for m in _INLINE_SHELL.finditer(f.norm):
        out.append(_f("SKILL_INLINE_SHELL", "script", Severity.HIGH, f, line_of(f, m.start()),
                      "This syntax runs a shell command as soon as the skill loads, before Claude or you review the result.",
                      trigger=AUTOMATIC, data_flow=LOCAL))
    return out


def analyze_frontmatter(skill: Skill, main: SkillFile) -> list:
    out, fm, where = [], skill.frontmatter, skill.frontmatter_lines
    tools = fm.get("allowed-tools", "")
    if tools:
        broad = _DANGEROUS_TOOLS.search(tools)
        out.append(_f("FM_ALLOWED_TOOLS", "script", Severity.HIGH if broad else Severity.MEDIUM, main,
                      where.get("allowed-tools", 1),
                      "Grants tools without a permission prompt while this skill is active."
                      + (" Includes unrestricted shell or wildcard access." if broad else "")))
    if "hooks" in fm:
        out.append(_f("FM_HOOKS", "script", Severity.HIGH, main, where["hooks"],
                      "The skill defines hooks: shell commands that run automatically while it is active.",
                      trigger=AUTOMATIC))
    desc = fm.get("description", "")
    if re.search(r"\b(?:always|every|all|any)\s+(?:task|request|prompt|message|conversation|time|turn)s?\b", desc, re.I):
        out.append(_f("FM_BROAD_TRIGGER", "injection", Severity.MEDIUM, main, where.get("description", 1),
                      "The description asks to activate on nearly everything, which would load its instructions into unrelated work."))
    if not desc and where:
        out.append(_f("FM_NO_DESCRIPTION", "injection", Severity.LOW, main, 1,
                      "No activation description, so it is unclear when this skill applies."))
    root = Path(skill.root)
    seen = set()
    for m in _MD_REF.finditer(main.norm):
        ref = m.group(1) or m.group(2)
        if re.match(r"[a-z]+:", ref, re.I) or ref in seen:
            continue
        seen.add(ref)
        line = line_of(main, m.start())
        target = (root / ref).resolve()
        if root != target and root not in target.parents:
            out.append(_f("REF_OUTSIDE", "privacy", Severity.MEDIUM, main, line,
                          "References a file outside the skill's folder, which this audit did not cover."))
        elif not target.exists():
            out.append(_f("REF_MISSING", "script", Severity.LOW, main, line,
                          "References a file that is not in the skill. It may be generated or fetched later."))
    return out


def _json_line(f: SkillFile, needle: str) -> int:
    for i, raw in enumerate(f.lines, start=1):
        if needle and needle in raw:
            return i
    return 1


def analyze_manifest_servers(f: SkillFile, servers: dict) -> list:
    out = []
    for name, cfg in (servers or {}).items():
        if not isinstance(cfg, dict):
            continue
        url, command = cfg.get("url"), cfg.get("command")
        if url:
            out.append(_f("MCP_REMOTE", "network", Severity.MEDIUM, f, _json_line(f, str(url)),
                          f"Connects Claude Code to remote server '{name}'. Anything Claude passes to its tools goes there.",
                          destination=redact(str(url)), trigger=AUTOMATIC, data_flow=EXTERNAL,
                          data_at_risk="whatever is passed to this server's tools"))
        if command:
            args = " ".join(str(a) for a in cfg.get("args", []))
            full = f"{command} {args}".strip()
            unpinned = command in {"npx", "uvx", "bunx", "pipx"} and "@" not in args.replace("@modelcontextprotocol", "")
            out.append(_f("MCP_LOCAL", "script", Severity.HIGH if unpinned else Severity.MEDIUM, f,
                          _json_line(f, str(command)),
                          f"Starts local program '{full[:80]}' outside the sandbox when the plugin loads."
                          + (" The version is unpinned, so it can change without notice." if unpinned else ""),
                          trigger=AUTOMATIC, data_flow=LOCAL, tags=frozenset({"unpinned"} if unpinned else ())))
    return out


def analyze_config(f: SkillFile) -> list:
    out = []
    name = Path(f.rel).name
    if f.kind in ("config", "other") and name.endswith(".json"):
        try:
            data = json.loads(f.text)
        except ValueError:
            data = None
            if name in {".mcp.json", "hooks.json", "plugin.json", "package.json"}:
                out.append(_f("CFG_UNPARSEABLE", "script", Severity.MEDIUM, f, 1,
                              "This configuration file could not be parsed, so its effect is unknown."))
        if isinstance(data, dict):
            if name == ".mcp.json":
                out += analyze_manifest_servers(f, data.get("mcpServers", data))
            if name == "plugin.json":
                out += analyze_manifest_servers(f, data.get("mcpServers") if isinstance(data.get("mcpServers"), dict) else {})
                for key, label in (("hooks", "hooks"), ("lspServers", "language servers"), ("monitors", "monitors"), ("mods", "mods")):
                    if key in data:
                        out.append(_f("PLG_CODE_SURFACE", "script", Severity.HIGH, f, _json_line(f, f'"{key}"'),
                                      f"The plugin declares {label}, which run code outside Claude Code's sandbox.",
                                      trigger=AUTOMATIC))
            if name == "hooks.json" or Path(f.rel).parts[0] == "hooks" and name.endswith(".json"):
                for needle in _commands(data):
                    out.append(_f("HOOK_COMMAND", "script", Severity.HIGH, f, _json_line(f, needle[:40]),
                                  f"Hook command runs automatically with your full user permissions: {redact(needle)[:100]!r}",
                                  trigger=AUTOMATIC, data_flow=LOCAL))
            if name == "package.json":
                out += _package_json(f, data)
    if name.startswith("requirements") and name.endswith(".txt"):
        out += _requirements(f)
    return out


def _commands(node) -> list:
    found = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "command" and isinstance(v, str):
                found.append(v)
            else:
                found += _commands(v)
    elif isinstance(node, list):
        for v in node:
            found += _commands(v)
    return found


def _package_json(f: SkillFile, data: dict) -> list:
    out = []
    scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
    for hook in ("preinstall", "install", "postinstall", "prepare", "preuninstall", "postuninstall"):
        if hook in scripts:
            out.append(_f("DEP_LIFECYCLE", "script", Severity.HIGH, f, _json_line(f, f'"{hook}"'),
                          f"The {hook} script runs automatically during package installation: {redact(str(scripts[hook]))[:100]!r}",
                          trigger=AUTOMATIC))
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        deps = data.get(section) if isinstance(data.get(section), dict) else {}
        for dep, ver in deps.items():
            ver = str(ver)
            risky = re.match(r"(?:https?:|git|github:|file:)", ver) or ver in ("*", "latest", "")
            out.append(_f("DEP_NODE", "script", Severity.MEDIUM if risky else Severity.LOW, f, _json_line(f, f'"{dep}"'),
                          f"Depends on {dep} {ver}." + (" Unpinned or fetched directly from a URL." if risky else "")))
    return out


def _requirements(f: SkillFile) -> list:
    out = []
    for i, raw in enumerate(f.lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pinned = "==" in line
        direct = "://" in line or line.startswith("-")
        out.append(_f("DEP_PYTHON", "script", Severity.MEDIUM if direct or not pinned else Severity.LOW, f, i,
                      f"Python dependency{' fetched from a URL or custom index' if direct else ''}"
                      f"{', unpinned' if not pinned and not direct else ''}."))
    return out


def analyze_file(f: SkillFile) -> list:
    if not f.norm:
        return []
    findings = network_scanner.analyze(f) + credential_scanner.analyze(f) + privacy_analyzer.analyze(f)
    findings += scan(f, INJECTION + DESTRUCTIVE + SCRIPT_RULES)
    findings += hidden_text(f) + encoded_payloads(f) + analyze_config(f)
    if f.kind == "instruction":
        findings += analyze_instructions(f)
    return findings


def analyze_skill(skill: Skill) -> list:
    findings = list(skill.load_findings)
    for f in skill.files:
        findings += analyze_file(f)
    main = next((f for f in skill.files if f.rel.endswith("SKILL.md") and Path(f.path).parent == Path(skill.root)), None)
    if main:
        findings += analyze_frontmatter(skill, main)
    return findings
