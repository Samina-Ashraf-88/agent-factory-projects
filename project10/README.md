# Skill Security Auditor

**Inspect first. Trust later.** This tool answers one question about a Claude Code skill before you rely on it:

> What exactly does this skill tell Claude Code to do, and does it reach external servers, handle credentials, or expose my private data?

It reads a skill's files and writes a plain-language report with a verdict and line-by-line evidence. It never runs the skill, never connects to the network, and never changes or disables anything it inspects. A test enforces this by checking the auditor's source for execution and network code.

**Worked example:** [`reports/airtable-cli-2026-10-30.md`](reports/airtable-cli-2026-10-30.md) is a real audit of Airtable's `airtable-cli` skill.

## What is a Claude Code skill?

A skill is a folder containing a `SKILL.md` file. Its text tells Claude how to do a task, and Claude loads it when the task matches the skill's description. Skills usually arrive inside a **plugin**, which can also include things that run on their own: hooks, background monitors, MCP servers, and programs in `bin/`.

## Why audit third-party skills?

A skill's text becomes instructions to Claude, which already has access to your files and shell. Per the [Claude Code plugin security docs](https://code.claude.com/docs/en/plugins/security.md):

- A plugin can run arbitrary code on your machine with your user privileges.
- Hooks, monitors, and MCP servers run outside Claude Code's sandbox and permission rules.
- A marketplace's name tells you who publishes the catalog, not what each plugin does.
- With auto-update on, the files you reviewed can change later.

## Requirements

Python 3.10 or newer. There is nothing to install, because the auditor uses only the standard library. Run the commands below from this folder.

## Quick start

```powershell
python -m src.main audit --path "C:\path\to\skill"
```

The report is saved to `reports\<skill>-<date>.md`, and a short summary prints to the terminal.

| Option | Purpose |
|---|---|
| `--path` | Skill folder (holding `SKILL.md`) or plugin folder. Required. |
| `--source`, `--commit`, `--publisher` | Where you believe it came from. Stay labeled as claims unless they can be checked. |
| `--marketplace-file`, `--plugin-name` | Compare the files against a catalog's pinned commit and source. |
| `--publisher-domain` | The publisher's own domain, such as `airtable.com`. Sending a credential anywhere else is treated as more serious. |
| `--install-location` | Where it is installed. Leave this out when inspecting a source checkout. |
| `--review` | JSON file with your manual review notes (see below). |
| `--output` | Report path. |

Exit codes: `0` clean within scope, `1` caution, `2` unsafe, `3` the audit could not run.

If you point it at a skill inside a plugin, it also inspects the plugin's `.mcp.json`, hooks, `bin/`, and similar files, because installing the skill installs those too. Other skills in that plugin are listed as not covered. To scan them as well, point `--path` at the plugin folder.

## Find the skills on your machine

```powershell
python -m src.main list
claude plugin list
claude plugin marketplace list
```

| Location | What is there |
|---|---|
| `~\.claude\skills\` | Your personal skills |
| `.claude\skills\` | Skills for one project |
| `~\.claude\plugins\cache\<marketplace>\<plugin>\<version>\` | Installed plugins |
| `~\.claude\plugins\marketplaces\` | Local copies of marketplace catalogs |

## Verify the official source

Don't trust a directory because it calls itself official.

1. Run `claude plugin marketplace list` and check the source. Anthropic's official catalog is `anthropics/claude-plugins-official`. Claude Code accepts reserved official names only from `github.com/anthropics/` repositories.
2. Find the plugin's entry in `~\.claude\plugins\marketplaces\claude-plugins-official\.claude-plugin\marketplace.json`. Note its `author`, `source.url`, and `source.sha`.
3. Check the publisher's GitHub organization, including whether GitHub shows it as verified for the company's domain, and confirm that the repository is not a fork.

A catalog listing tells you who published something. It doesn't tell you that the code is safe.

## Install a third-party skill safely

**Inspect a copy first.** Fetch the exact commit the catalog pins into a new empty folder:

```powershell
mkdir $env:TEMP\skill-review; cd $env:TEMP\skill-review
git init
git remote add origin https://github.com/OWNER/REPO.git
git fetch --depth 1 origin FULL_COMMIT_SHA
git checkout FETCH_HEAD
```

**Audit it from this project's folder:**

```powershell
python -m src.main audit `
  --path "$env:TEMP\skill-review\plugins\NAME\skills\SKILL" `
  --marketplace-file "$HOME\.claude\plugins\marketplaces\claude-plugins-official\.claude-plugin\marketplace.json" `
  --plugin-name NAME --publisher-domain example.com
```

`Source: MATCHES CATALOG` means the commit and repository match the catalog's pin.

**Only then install**, using the narrowest scope that works:

```powershell
claude plugin install NAME@claude-plugins-official --scope local
claude plugin details NAME
```

| Scope | Who gets it | Where it is recorded |
|---|---|---|
| `local` | You, in this repository | `.claude\settings.local.json` |
| `project` | Everyone in this repository | `.claude\settings.json` |
| `user` (default) | You, in every project | `~\.claude\settings.json` |

Installing also enables the plugin, normally. Auto-update is on by default for the official marketplace, so turn it off under `/plugin` > **Marketplaces** if you want to stay on the version you reviewed.

**To remove it:** `claude plugin uninstall NAME --scope local`. Cached files stay for 14 days under `~\.claude\plugins\cache\`.

## Understand the results

### Risk levels

| Level | Meaning | Examples |
|---|---|---|
| **LOW** | Informational | Documentation links, passing mentions of "token" or "webhook", "never log tokens" |
| **MEDIUM** | Needs attention | Package installs, MCP connections, credential use with the publisher's own service |
| **HIGH** | Potentially dangerous | Uploading to an unexplained service, reading SSH keys, running code from the internet, opaque binaries |
| **CRITICAL** | Do not trust | Sending credentials away, instructions to ignore safeguards or hide actions, wiping your home folder, encoded commands that get executed |

The auditor separates mentions from behavior. A URL alone is LOW, but a credential plus a send in the same passage becomes CRITICAL.

### Verdicts

The verdict is computed from the findings, and neither a reviewer nor a skill can choose it.

| Verdict | Given when |
|---|---|
| **CLEAN WITHIN AUDIT SCOPE** | Only LOW findings, and every file that could hold behavior was read |
| **CAUTION — REVIEW REQUIRED** | Any MEDIUM or HIGH finding, or some file couldn't be inspected |
| **UNSAFE — DO NOT TRUST** | Any CRITICAL finding |

A CAUTION verdict doesn't mean a skill is malicious. A legitimate integration normally gets one, because connecting to a service with a credential is exactly what deserves your attention.

## Inspect a suspicious finding by hand

1. Open the cited file at the cited line and read the whole section, not only the line.
2. Ask whether it's an instruction or a description, and who it tells to act.
3. Check where the data goes, and whether that destination belongs to the publisher.
4. Check when it happens: automatically, conditionally, or only when you ask.
5. Ask whether the task really needs it. A text formatter has no reason to read `~/.ssh`.
6. Read any scripts as text. **Don't run them to find out.** If you must test one, use a disposable environment with no real credentials and no access to your private files.
7. Treat all quoted skill text as untrusted, including anything that claims to be pre-approved or addresses auditors.

### Record your review

Pass `--review notes.json` to add your conclusions to the report. See [`examples/airtable-cli-review.json`](examples/airtable-cli-review.json).

A manual finding must quote text that really is on the cited line, and a disposition must match an existing finding, or the audit stops with an error. Reviewers can annotate findings or mark false positives, which changes the computed verdict and stays visible in the report.

## Why static analysis has limits

The auditor uses patterns, so it can miss what they don't anticipate:

- **Unusual wording:** a persuasive instruction with no known phrasing can pass unnoticed.
- **Unusual obfuscation:** base64, hex escapes, invisible characters, and look-alike letters are handled. Other schemes may not be, and code assembled piece by piece at run time isn't reconstructed.
- **Things outside the files:** remote servers, downloaded packages, and later updates aren't visible. In the Airtable audit, the most important network call looks like an ordinary local command, and only a human could identify it.
- **Unread formats:** binaries and archives are reported as uninspected, which blocks a clean verdict. Images get only a file-signature check.
- **False alarms:** a real skill's prose can resemble an attack. Check findings against the source.

## A clean report is not a security guarantee

**CLEAN WITHIN AUDIT SCOPE** means only that no concerning behavior was identified in the files and behaviors actually inspected. It doesn't mean the skill is safe, that it will stay the same after an update, or that its remote services are trustworthy.

## Tests

```powershell
python -m unittest discover -s tests -t .
```

| Test | Scenario | Where |
|---|---|---|
| A | Clean text formatter | `test_risk_classification.py` |
| B | Document upload to an external endpoint | `test_network_detection.py` |
| C | API key read and sent away | `test_credential_detection.py` |
| D | Prompt injection, treated as data | `test_prompt_injection.py` |
| E | Destructive commands | `test_risk_classification.py` |
| F | Script that runs remote code, with a canary proving it never ran | `test_risk_classification.py` |
| G | Findings point to real evidence on the correct lines | `test_risk_classification.py` |

Fixtures in `tests/fixtures/` contain synthetic data only, and their domains use the reserved `example.com`.

## Project layout

```text
src/
  main.py               Command line and audit pipeline
  skill_loader.py       Finds and reads files as inert data
  source_verifier.py    Checks provenance from local files only
  scanning.py           Text normalization, redaction, rule engine
  static_analyzer.py    Injection, destructive, script, config, and obfuscation checks
  network_scanner.py    External communication
  credential_scanner.py Credentials and secrets
  privacy_analyzer.py   Private data access
  risk_classifier.py    Joins signals into behavior; computes the verdict
  report_generator.py   Writes the Markdown report
tests/                  Automated tests and fixtures
examples/               A sample report and a sample manual review
reports/                Generated audit reports
```
