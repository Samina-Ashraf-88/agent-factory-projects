"""Check what can be checked about provenance using local files only.

Never contacts the network and never shells out to git, since a repository's own
config can make git run commands. Claims the user supplies stay labeled as claims.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .models import Finding, Severity, Skill, SourceInfo

RESERVED_MARKETPLACES = {"claude-plugins-official", "claude-code-marketplace", "claude-code-plugins",
                         "anthropic-marketplace", "anthropic-plugins", "agent-skills", "anthropic-agent-skills"}


def tree_digest(skill: Skill) -> str:
    h = hashlib.sha256()
    for f in sorted(skill.files, key=lambda x: x.rel):
        h.update(f"{f.sha256}  {f.rel}\n".encode())
    return h.hexdigest()


def read_git_head(start: str):
    """(commit, remote url) from .git as plain text, or (None, None) when not in a checkout."""
    current = Path(start).resolve()
    for candidate in [current, *current.parents]:
        git = candidate / ".git"
        if git.is_dir():
            return _resolve_head(git), _origin_url(git)
    return None, None


def _resolve_head(git: Path):
    try:
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
        if not head.startswith("ref:"):
            return head
        ref = head.split(None, 1)[1]
        ref_file = git / ref
        if ref_file.is_file():
            return ref_file.read_text(encoding="utf-8").strip()
        packed = git / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="utf-8").splitlines():
                if line.endswith(" " + ref):
                    return line.split()[0]
    except OSError:
        return None
    return None


def _origin_url(git: Path):
    try:
        text = (git / "config").read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r'\[remote "origin"\][^\[]*?url\s*=\s*(\S+)', text)
    return m.group(1) if m else None


def _canon(url: str) -> str:
    url = re.sub(r"^git@([^:]+):", r"https://\1/", (url or "").strip())
    url = re.sub(r"\.git$", "", url.rstrip("/"))
    return url.lower()


def verify(skill: Skill, publisher=None, source=None, commit=None, install_location=None,
           marketplace_file=None, plugin_name=None) -> tuple:
    """Return (SourceInfo, findings)."""
    info = SourceInfo(publisher=publisher or "not supplied", source=source or "not supplied",
                      commit=commit or "not supplied",
                      install_location=install_location or "not installed; inspected as a source checkout",
                      tree_sha256=tree_digest(skill))
    findings = []
    head, origin = read_git_head(skill.root)

    if head:
        info.details.append(f"Local checkout HEAD: {head}")
        if commit and not head.lower().startswith(commit.lower()):
            findings.append(_mismatch(f"commit {commit} supplied, but the checkout is at {head}",
                                      "The files audited are not the version you named."))
        elif not commit:
            info.commit = f"{head} (from local checkout)"
    if origin:
        info.details.append(f"Local checkout origin: {origin}")
        if source and _canon(origin) != _canon(source):
            findings.append(_mismatch(f"source {source} supplied, but origin is {origin}",
                                      "The files audited did not come from the source you named."))
        elif not source:
            info.source = f"{origin} (from local checkout)"

    if marketplace_file:
        findings += _check_catalog(info, Path(marketplace_file), plugin_name or skill.plugin_manifest.get("name"),
                                   head, origin or source)
    elif not findings:
        info.details.append("No marketplace catalog supplied, so publisher and source are unconfirmed claims.")
    if findings:
        info.status = "MISMATCH"
    return info, findings


def _mismatch(evidence, why):
    return Finding("SRC_MISMATCH", "source", Severity.HIGH, ".", 0, evidence, why)


def _check_catalog(info, path, plugin_name, head, origin) -> list:
    try:
        catalog = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        info.details.append(f"Could not read marketplace catalog: {exc.__class__.__name__}")
        return []
    entry = next((p for p in catalog.get("plugins", []) if p.get("name") == plugin_name), None)
    label = catalog.get("name", "unknown")
    if not entry:
        return [_mismatch(f"plugin '{plugin_name}' not listed in catalog '{label}'",
                          "The catalog you named does not list this plugin.")]
    src = entry.get("source") if isinstance(entry.get("source"), dict) else {}
    pinned, url = src.get("sha"), src.get("url") or src.get("repo")
    author = (entry.get("author") or {}).get("name")
    info.details.append(f"Catalog '{label}' lists plugin '{plugin_name}': author {author}, source {url}, "
                        f"path {src.get('path', '')}, pinned sha {pinned}")
    if author and info.publisher == "not supplied":
        info.publisher = f"{author} (from catalog)"
    problems = []
    if pinned and head and pinned.lower() != head.lower():
        problems.append(_mismatch(f"catalog pins {pinned}, checkout is at {head}",
                                  "The files audited are not the version this catalog would install."))
    if url and origin and _canon(url) != _canon(origin):
        problems.append(_mismatch(f"catalog source {url}, checkout origin {origin}",
                                  "The files audited came from a different repository than the catalog names."))
    if not problems:
        if pinned and head:
            info.status = "MATCHES CATALOG"
            info.details.append("Checkout commit and origin match the catalog's pin.")
        else:
            info.details.append("Catalog lists the plugin, but no commit pin could be compared.")
    return problems
