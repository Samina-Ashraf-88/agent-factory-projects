"""Discover and read a skill's files as inert data. Nothing here executes or imports them."""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from .models import Finding, Severity, Skill, SkillFile
from .scanning import normalize

MAX_FILE_BYTES = 2_000_000
MAX_FILES = 5000
SKIP_DIRS = {".git"}

INSTRUCTION_EXT = {".md", ".mdx", ".markdown", ".txt", ".rst"}
SCRIPT_EXT = {".sh", ".bash", ".zsh", ".fish", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".ps1", ".psm1",
              ".bat", ".cmd", ".rb", ".pl", ".php", ".lua"}
CONFIG_EXT = {".json", ".jsonc", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env", ".lock", ".svg", ".html", ".xml"}
IMAGE_MAGIC = {
    ".png": (b"\x89PNG",), ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF8",), ".webp": (b"RIFF",), ".ico": (b"\x00\x00\x01\x00",),
}
EXEC_MAGIC = (b"MZ", b"\x7fELF", b"\xfe\xed\xfa", b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe")
ARCHIVE_EXT = {".zip", ".tar", ".gz", ".tgz", ".whl", ".jar", ".mcpb", ".7z", ".rar"}
# Plugin parts that run code or connect to services whichever skill you came for.
PLUGIN_SURFACES = ("hooks", "bin", "monitors", "mods", "agents", "commands")
PLUGIN_FILES = (".mcp.json", ".lsp.json", ".claude-plugin/plugin.json")

_FM_KEY = re.compile(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$")


def parse_frontmatter(lines: list) -> tuple:
    """Return (values, key -> line number, closed). Minimal on purpose: no YAML tags, no code paths."""
    if not lines or lines[0].strip() != "---":
        return {}, {}, False
    values, where, key = {}, {}, None
    for i, raw in enumerate(lines[1:], start=2):
        if raw.strip() == "---":
            return values, where, True
        m = _FM_KEY.match(raw)
        if m and not raw.startswith((" ", "\t")):
            key = m.group(1)
            where[key] = i
            values[key] = m.group(2).strip().strip("'\"")
            if values[key] in (">", "|", ">-", "|-"):
                values[key] = ""
        elif key and raw.strip():
            values[key] = f"{values[key]} {raw.strip()}".strip()
    return values, where, False


def _decode(data: bytes):
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    if b"\x00" in data[:8192]:
        return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None


def _kind(rel: str, text) -> str:
    path = Path(rel)
    ext = path.suffix.lower()
    if text is None:
        return "binary"
    if ext in SCRIPT_EXT or text.startswith("#!") or "bin" in path.parts[:-1]:
        return "script"
    if ext in INSTRUCTION_EXT:
        return "instruction"
    if ext in CONFIG_EXT or path.name in {"Dockerfile", "Makefile", ".npmrc", ".env"}:
        return "config"
    return "other"


def _read(path: Path, rel: str, skill_findings: list, skill: Skill):
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        skill.not_analysed.append((rel, f"larger than {MAX_FILE_BYTES} bytes; not read"))
        skill.incomplete = True
        skill_findings.append(Finding(
            "LOAD_OVERSIZED", "script", Severity.MEDIUM, rel, 0, f"{size} bytes",
            "File is too large to inspect automatically, so its contents are unknown. Review it by hand."))
        return None
    try:
        data = path.read_bytes()
    except OSError as exc:
        skill.not_analysed.append((rel, f"unreadable: {exc.__class__.__name__}"))
        skill.incomplete = True
        return None
    digest = hashlib.sha256(data).hexdigest()
    text = _decode(data)
    kind = _kind(rel, text)
    f = SkillFile(rel=rel, path=str(path), size=size, sha256=digest, kind=kind)
    ext = path.suffix.lower()
    if text is None:
        _classify_binary(f, data, ext, skill_findings, skill)
        return f
    f.text = text.replace("\r\n", "\n").replace("\r", "\n")
    f.lines = f.text.split("\n")  # str.splitlines would also split on \f, \v and U+2028 and skew line numbers
    f.norm = normalize(f.text)
    f.newlines = [i for i, c in enumerate(f.norm) if c == "\n"]
    return f


def _classify_binary(f: SkillFile, data: bytes, ext: str, findings: list, skill: Skill) -> None:
    if data.startswith(EXEC_MAGIC):
        f.note = "executable binary"
        skill.incomplete = True
        skill.not_analysed.append((f.rel, "executable binary; opaque to static text analysis"))
        findings.append(Finding(
            "BIN_EXECUTABLE", "script", Severity.HIGH, f.rel, 0, f"sha256 {f.sha256[:16]}…",
            "Compiled program. Its behavior cannot be read here and it would run with your privileges.",
            tags=frozenset({"opaque"})))
    elif ext in IMAGE_MAGIC:
        if data.startswith(IMAGE_MAGIC[ext]):
            f.kind = "asset"
            f.note = "image; file signature checked, content not analysed"
            skill.not_analysed.append((f.rel, f.note))
        else:
            skill.incomplete = True
            skill.not_analysed.append((f.rel, "image extension but wrong file signature"))
            findings.append(Finding(
                "BIN_DISGUISED", "script", Severity.HIGH, f.rel, 0, f"first bytes {data[:4].hex()}",
                "The file claims to be an image but its signature does not match, which can hide a payload."))
    else:
        skill.incomplete = True
        reason = "archive; not extracted" if ext in ARCHIVE_EXT else "unrecognized binary"
        skill.not_analysed.append((f.rel, reason))
        findings.append(Finding(
            "BIN_OPAQUE", "script", Severity.HIGH, f.rel, 0, f"{reason}; sha256 {f.sha256[:16]}…",
            "Opaque file that static text analysis cannot inspect. It may contain code or data."))


def _walk(top: Path, base: Path, skill: Skill) -> list:
    """All regular files under top, never following links. Hidden files are included."""
    found = []
    for current, dirs, names in os.walk(top, followlinks=False):
        current_p = Path(current)
        for d in list(dirs):
            p = current_p / d
            if d in SKIP_DIRS:
                dirs.remove(d)
            elif p.is_symlink() or p.is_junction():
                dirs.remove(d)
                _record_link(p, base, skill)
        for n in names:
            p = current_p / n
            if p.is_symlink():
                _record_link(p, base, skill)
            else:
                found.append(p)
    return found


def _record_link(p: Path, base: Path, skill: Skill) -> None:
    rel = p.relative_to(base).as_posix()
    try:
        target = os.readlink(p)
    except OSError:
        target = "unknown target"
    skill.not_analysed.append((rel, "link; not followed"))
    skill.incomplete = True
    skill.load_findings.append(Finding(
        "LOAD_SYMLINK", "privacy", Severity.HIGH, rel, 0, f"-> {target}",
        "A link can make the skill read or overwrite a file outside its own folder, such as a credentials file."))


def find_plugin_root(start: Path, limit: int = 4):
    current = start
    for _ in range(limit):
        if (current / ".claude-plugin" / "plugin.json").is_file():
            return current
        if current.parent == current:
            return None
        current = current.parent
    return None


def load_skill(path: str) -> Skill:
    root = Path(path).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Not a directory: {path}")

    is_skill_dir = (root / "SKILL.md").is_file()
    plugin_root = find_plugin_root(root)
    mode = "skill" if is_skill_dir else "plugin"
    skill = Skill(root=str(root), mode=mode, name=root.name, frontmatter={}, frontmatter_lines={}, files=[],
                  plugin_root=str(plugin_root) if plugin_root else "")
    base = plugin_root if plugin_root and plugin_root != root else root

    paths = _walk(root, base, skill)
    if is_skill_dir and plugin_root and plugin_root != root:
        # Installing a skill means installing its plugin, so its executable surfaces are in scope.
        for name in PLUGIN_FILES:
            p = plugin_root / name
            if p.is_file():
                paths.append(p)
        for name in PLUGIN_SURFACES:
            d = plugin_root / name
            if d.is_dir():
                paths.extend(_walk(d, base, skill))
        skills_dir = plugin_root / "skills"
        if skills_dir.is_dir():
            skill.out_of_scope = sorted(
                d.name for d in skills_dir.iterdir() if d.is_dir() and d.resolve() != root)

    if len(paths) > MAX_FILES:
        skill.incomplete = True
        skill.not_analysed.append((f"{len(paths) - MAX_FILES} files", f"exceeded the {MAX_FILES} file limit"))
        paths = paths[:MAX_FILES]

    for p in sorted(set(paths)):
        rel = p.relative_to(base).as_posix()
        f = _read(p, rel, skill.load_findings, skill)
        if f:
            skill.files.append(f)

    main = next((f for f in skill.files if Path(f.path).resolve() == root / "SKILL.md"), None)
    if main:
        values, where, closed = parse_frontmatter(main.lines)
        skill.frontmatter, skill.frontmatter_lines = values, where
        skill.name = values.get("name") or root.name
        if not closed:
            skill.load_findings.append(Finding(
                "LOAD_NO_FRONTMATTER", "injection", Severity.MEDIUM, main.rel, 1,
                main.lines[0][:120] if main.lines else "",
                "SKILL.md has no well-formed frontmatter, so its activation conditions are unclear."))
    elif mode == "plugin" and not any(f.rel.endswith("SKILL.md") for f in skill.files):
        skill.load_findings.append(Finding(
            "LOAD_NO_SKILL", "script", Severity.MEDIUM, ".", 0, "no SKILL.md found",
            "No SKILL.md in this directory. Check that the path points at the skill you meant to audit."))

    if plugin_root:
        manifest = plugin_root / ".claude-plugin" / "plugin.json"
        skill.plugin_manifest = _safe_json(manifest)
    return skill


def _safe_json(path: Path) -> dict:
    import json
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}
