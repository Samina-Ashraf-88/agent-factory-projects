# Third-Party Skill Security Audit

> **Verdict: CAUTION — REVIEW REQUIRED.** Findings need review (0 CRITICAL, 0 HIGH, 10 MEDIUM, 15 LOW).
>
> This skill teaches Claude Code to read and change your Airtable data with Airtable's airtable-mcp command-line tool, and yes, it reaches outside your machine and Claude account: your Airtable token and whatever records Claude sends go to Airtable's servers (mcp.airtable.com), and installing the tool downloads it from the npm registry.

## 1. Skill Information

- **Skill name:** `airtable-cli`
- **Original author or publisher:** Airtable (from catalog)
- **Official repository or directory:** https://github.com/Airtable/skills.git (from local checkout)
- **Version or commit identifier:** 812ee67f1fd3d76fb45ff8df40afaa0448602ba8 (from local checkout)
- **Installation location:** C:\Users\AKE\.claude\plugins\cache\claude-plugins-official\airtable\0.1.0 (local scope)
- **Audit date:** 2026-10-30
- **Source verification:** MATCHES CATALOG
  - Local checkout HEAD: 812ee67f1fd3d76fb45ff8df40afaa0448602ba8
  - Local checkout origin: https://github.com/Airtable/skills.git
  - Catalog 'claude-plugins-official' lists plugin 'airtable': author Airtable, source https://github.com/Airtable/skills.git, path plugins/airtable, pinned sha 812ee67f1fd3d76fb45ff8df40afaa0448602ba8
  - Checkout commit and origin match the catalog's pin.
  - Listed in the official catalog anthropics/claude-plugins-official (GitHub organization: anthropics; marketplace name reserved for Anthropic per the Claude Code plugin security docs). The local catalog copy was at snapshot f8c5e7a1dcb71b10cb74586224b5401f3de5db28.
  - Publisher repository Airtable/skills belongs to the GitHub organization Airtable, which GitHub marks as verified for airtable.com. The repo is not a fork and is MIT licensed.
  - The commit's signature could not be checked locally (git reports status E, signing key unavailable), so commit authorship is not cryptographically confirmed here.
  - After your approval, installed with claude plugin install airtable@claude-plugins-official --scope local. A byte-for-byte comparison found the installed plugin identical to the audited commit, apart from an empty .in_use marker folder, and auditing the installed skill produced the same file fingerprint. The skill was not run.
  - A catalog listing shows who publishes the entry, not that the code is safe. Anthropic's own trust warning says it cannot verify that plugins work as intended or won't change.
- **Fingerprint of audited files (SHA-256):** `acd66aef9d69c96281c93da2a2f18a0bf86e9bd8ff3ee878b4d0a1ef8c721f12`

## 2. What This Skill Does

- **Main purpose:** A reference guide for using Airtable's airtable-mcp command-line tool: finding bases, reading, filtering, searching, and updating records.
- **When it activates:** Claude Code loads it when a task involves Airtable data or mentions airtable-mcp, bases, tables, records, or fields. It declares no special permissions and no hooks.
- **What it tells Claude Code to do:** Install the tool with npm, sign in with an Airtable personal access token, list the available commands, check each command's access level, confirm with you before destructive commands, then run the command.
- **Tools it may use:** It declares no allowed-tools, so it grants itself no extra permissions and your Claude Code permission settings still apply to its shell commands. In practice it uses the shell to run npm and airtable-mcp. The plugin that ships it also connects Claude Code to Airtable's remote MCP server.
- **Output:** Formatted JSON from the Airtable tool, which Claude uses to answer you. The skill itself creates no files, but the tool can save a token and a command cache under ~/.airtable.

## 3. External Connections

- **Network activity instructed:** yes.

| Location | Instruction | Destination | Data that may be sent | When |
|---|---|---|---|---|
| `.mcp.json:4` | `"url": "https://mcp.airtable.com/mcp"` | https://mcp.airtable.com/mcp | whatever is passed to this server's tools | automatic |
| `skills/airtable-cli/SKILL.md:22` | `Tool names, arguments, and output shapes can change between server releases` | https://mcp.airtable.com/mcp | see explanation | conditional |
| `skills/airtable-cli/SKILL.md:27` | `npm install -g @airtable/mcp-cli` | registry.npmjs.org | the package request; no private data by itself | conditional |
| `skills/airtable-cli/SKILL.md:76` | `airtable-mcp <tool> --flagName value` | https://mcp.airtable.com/mcp | your Airtable token, plus record data and queries in the command | conditional |

**Mentioned URLs, not endpoints (5):**

- https://airtable.com/create/tokens (`skills/airtable-cli/SKILL.md:139`)
- https://airtable.com/create/tokens (`skills/airtable-cli/SKILL.md:46`)
- https://github.com/airtable/skills (`.claude-plugin/plugin.json:10`)
- https://www.airtable.com (`.claude-plugin/plugin.json:7`)
- https://www.airtable.com (`.claude-plugin/plugin.json:9`)

**Reviewer notes:**

- Reaches Airtable: every airtable-mcp command sends your token and that command's arguments, including any record data, to https://mcp.airtable.com/mcp by default. Only happens when a command runs.
- Reaches npm: registry.npmjs.org, when the tool is installed. Only the package request is sent.
- Mentioned only, nothing sent by the skill: airtable.com/create/tokens is where you create a token by hand.
- No webhook, upload, or data-collection endpoint appears in the inspected skill files.

## 4. Credentials and Permissions

- **Passwords or tokens handled:** yes, see below.
- **Environment variables referenced:** yes: `` 1. **Auth** — set `AIRTABLE_TOKEN` or run `airtable-mcp configure` `` at `skills/airtable-cli/SKILL.md:72`, `` \| `Authentication failed`                      \| Token expired, revoked, or wrong                                   \| Run `airtable-mcp configure` or check `AIRTABLE_TOKEN`       … `` at `skills/airtable-cli/SKILL.md:138`, `` `AIRTABLE_TOKEN` takes precedence over saved profiles when no `--profile` flag is set. Never log or echo tokens. `` at `skills/airtable-cli/SKILL.md:48`, `export AIRTABLE_TOKEN=pat_xxx` at `skills/airtable-cli/SKILL.md:37`.
- **Sensitive files named:** yes: `skills/airtable-cli/SKILL.md:40`.
- **Passing mentions or prohibitions (not behavior):** 6.
- Credential values are never shown in this report.

**Reviewer notes:**

- The skill does handle a credential: an Airtable personal access token, from AIRTABLE_TOKEN or ~/.airtable/cli.json. No other service's credential is referenced, and it does not ask Claude to read SSH keys, cloud credentials, .env files, or browser data.
- The skill says 'Never log or echo tokens', and airtable-mcp configure reads the token at the tool's own terminal prompt (bin.js:25748) rather than through the conversation. Whether that prompt hides what you type was not checked.
- The AIRTABLE_TOKEN=pat_xxx value in the skill is a placeholder, not a real secret. No real secret was found.
- Least privilege is up to you: the token's scopes decide what the skill can reach. Create one limited to the bases and scopes you need.

## 5. Data Privacy

- **Private data categories referenced:** no evidence found in the inspected files.
- **Private data sent to a separate service:** no evidence found in the inspected files.
- **AI provider:** anything Claude reads while using a skill, including the skill's own text, goes through your configured AI provider. That is how Claude Code works and is not specific to this skill.

**Reviewer notes:**

- Can access: anything in Airtable that your token allows. It gives no instruction to read local documents, source code, email, or browser data.
- Can send: record contents and queries, to Airtable only, as part of the command being run. Anything in your conversation that Claude chooses to put into a record would go there too.
- Approval: the skill asks Claude to confirm with you only before tools marked destructive. Ordinary writes have no such instruction, so your Claude Code permission prompts are the check on those.
- Data returned from Airtable enters the conversation and goes to your AI provider. Text in records could also contain instructions written by other people with access to that base; treat it as untrusted.

## 6. Security Findings

**By category:**

- **External network access:** 12 finding(s), highest MEDIUM.
- **Credentials and secrets:** 11 finding(s), highest MEDIUM.
- **Private data:** 1 finding(s), highest MEDIUM.
- **Prompt injection and hidden instructions:** 1 finding(s), highest LOW.
- **Scripts and dependencies:** No evidence was found in the inspected files.
- **Destructive operations:** No evidence was found in the inspected files.
- **Source and version mismatch:** No evidence was found in the inspected files.

| Finding | File and line | Risk | Explanation |
|---|---|---|---|
| `"url": "https://mcp.airtable.com/mcp"` | `.mcp.json:4` | MEDIUM | Connects Claude Code to remote server 'airtable'. Anything Claude passes to its tools goes there. **Reviewer:** Confirmed. Publisher's own domain and expected for this product. It comes with the plugin, not this skill, and it is on whenever the plugin is enabled. No secret is stored in this file. |
| `Tool names, arguments, and output shapes can change between server releases` | `skills/airtable-cli/SKILL.md:22` | MEDIUM | *Manual review.* What this skill can do is set by Airtable's server at run time, not by this file. This audit can only describe today's skill text. New or changed server tools would not show up in it. |
| `npm install -g @airtable/mcp-cli` | `skills/airtable-cli/SKILL.md:27` | MEDIUM | Downloads and installs third-party code from a registry. The package's contents are not part of this audit. **Reviewer:** Confirmed. No version is pinned, so a later install can fetch different code from what was reviewed. The current version, 0.2.9, was downloaded without being run: its hash matches the registry's integrity value, it has no install scripts, and its registry entry carries a signature and a provenance attestation (presence checked, neither was cryptographically verified). Declared dependencies clipanion and @modelcontextprotocol/sdk were not separately audited. |
| `export AIRTABLE_TOKEN=pat_xxx` | `skills/airtable-cli/SKILL.md:37` | MEDIUM | Refers to an environment variable that holds a credential. Check that only the matching service receives it. **Reviewer:** Confirmed and expected. The value shown is a placeholder. An exported variable is visible to other programs started from that shell, and a token typed on a command line can land in shell history. |
| `` **Interactive configure (stores token in `~/.airtable/cli.json` with 0600 permissions):** `` | `skills/airtable-cli/SKILL.md:40` | MEDIUM | Names a file in your home folder that may hold saved credentials. Check who reads it and how it is protected. **Reviewer:** Confirmed, with a Windows caveat. The CLI does request 0600 (bin.js:9706), but Windows does not enforce POSIX file modes, so on this machine the token's protection comes from your user profile's folder permissions. The token is stored as readable JSON, not encrypted. Prefer the shortest practical token lifetime and narrow scopes. |
| `` `AIRTABLE_TOKEN` takes precedence over saved profiles when no `--profile` flag is set. Never log or echo tokens. `` | `skills/airtable-cli/SKILL.md:48` | MEDIUM | Refers to an environment variable that holds a credential. Check that only the matching service receives it. |
| `` 1. **Auth** — set `AIRTABLE_TOKEN` or run `airtable-mcp configure` `` | `skills/airtable-cli/SKILL.md:72` | MEDIUM | Refers to an environment variable that holds a credential. Check that only the matching service receives it. |
| `` Confirm with the user before running `destructive` tools. `` | `skills/airtable-cli/SKILL.md:75` | MEDIUM | *Manual review.* A good safeguard with a gap: it relies on the server's access label and covers only destructive tools. Commands labelled write, such as updating records, get no confirmation step from the skill, so overwriting shared data rests on your Claude Code permission prompts. |
| `airtable-mcp <tool> --flagName value` | `skills/airtable-cli/SKILL.md:76` | MEDIUM | *Manual review.* This is the skill's real network activity, and it looks like an ordinary local command. Each run sends the token and its arguments to Airtable. The automated scan cannot know that from the command name; the destination was confirmed by reading the tool's code (bin.js:9727). |
| `` \| `Authentication failed`                      \| Token expired, revoked, or wrong                                   \| Run `airtable-mcp configure` or check `AIRTABLE_TOKEN`       … `` | `skills/airtable-cli/SKILL.md:138` | MEDIUM | Refers to an environment variable that holds a credential. Check that only the matching service receives it. |
| `the user mentions airtable-mcp, bases, tables, records, or fields` | `skills/airtable-cli/SKILL.md:3` | LOW | *Manual review.* Tables, records, and fields are also everyday database words, so this could load during unrelated database work. The effect is limited: it adds guidance text and takes no action by itself. |
| `` CLI only allows HTTPS on `*.airtable.com` `` | `skills/airtable-cli/SKILL.md:148` | LOW | *Manual review.* Mostly accurate but incomplete. The code does enforce HTTPS and an allowlist, yet also permits mcp.hyperbasedev.com, which its comment calls an Airtable-controlled local development host resolving to loopback (bin.js:9728-9733). That DNS claim was not verified. The endpoint can be changed with AIRTABLE_MCP_ENDPOINT, within the same allowlist. |

<details><summary>15 informational (LOW) findings</summary>

| Finding | File and line | Risk | Explanation |
|---|---|---|---|
| `"description": "Airtable is the database and operations layer for your agents — whether running product, marketing, sales, ops, HR, or a custom business app. It combines structure…` | `.claude-plugin/plugin.json:4` | LOW | Mentions an MCP server. Servers that are actually configured are reported from .mcp.json. |
| `"url": "https://www.airtable.com"` | `.claude-plugin/plugin.json:7` | LOW | URL is only mentioned. No instruction on this line sends anything to it. |
| `"homepage": "https://www.airtable.com",` | `.claude-plugin/plugin.json:9` | LOW | URL is only mentioned. No instruction on this line sends anything to it. |
| `"repository": "https://github.com/airtable/skills",` | `.claude-plugin/plugin.json:10` | LOW | URL is only mentioned. No instruction on this line sends anything to it. |
| `Tools are fetched from the MCP server at runtime, so the CLI never has a hardcoded command list. Discover what's available:` | `skills/airtable-cli/SKILL.md:14` | LOW | Mentions an MCP server. Servers that are actually configured are reported from .mcp.json. |
| `The CLI needs an Airtable personal access token (PAT). Two paths:` | `skills/airtable-cli/SKILL.md:32` | LOW | Mentions a kind of credential. No read or send on this line by itself. |
| `Create tokens at https://airtable.com/create/tokens. Ensure the token has the scopes required by the tools being called.` | `skills/airtable-cli/SKILL.md:46` | LOW | Mentions a kind of credential. No read or send on this line by itself. |
| `Create tokens at https://airtable.com/create/tokens. Ensure the token has the scopes required by the tools being called.` | `skills/airtable-cli/SKILL.md:46` | LOW | URL is only mentioned. No instruction on this line sends anything to it. |
| `` `AIRTABLE_TOKEN` takes precedence over saved profiles when no `--profile` flag is set. Never log or echo tokens. `` | `skills/airtable-cli/SKILL.md:48` | LOW | Stated as a prohibition, not an instruction to do this. Writes a credential where it can be seen in logs, chat, or terminal history. |
| `` \| Set up credentials     \| `airtable-mcp configure`                                \| `` | `skills/airtable-cli/SKILL.md:54` | LOW | Mentions a kind of credential. No read or send on this line by itself. |
| `` \| Remove credentials     \| `airtable-mcp logout`                                   \| `` | `skills/airtable-cli/SKILL.md:57` | LOW | Mentions a kind of credential. No read or send on this line by itself. |
| `` \| `Access denied`                              \| Token missing required scopes                                      \| Add scopes at https://airtable.com/create/tokens             … `` | `skills/airtable-cli/SKILL.md:139` | LOW | Mentions a kind of credential. No read or send on this line by itself. |
| `` \| `Access denied`                              \| Token missing required scopes                                      \| Add scopes at https://airtable.com/create/tokens             … `` | `skills/airtable-cli/SKILL.md:139` | LOW | URL is only mentioned. No instruction on this line sends anything to it. |

</details>

**Automated scan compared with manual review:**

- Agreement: the scanner found the MCP connection, the npm install, the token variable, and the token file. Manual reading confirmed each one, and no automated MEDIUM or higher finding turned out to be false.
- Missed by the scanner, added by hand: airtable-mcp commands are network calls (a pattern scan can't tell), server-defined tools, the write-confirmation gap, the incomplete endpoint claim, and the broad activation words.
- Scanner bugs exposed by real text and fixed before this report: 'find / enrich' in prose read as a disk-wide search, product names like Outlook read as email access, and bare mentions of MCP servers scored MEDIUM. Regression tests now cover these.
- No prompt injection, hidden text, encoded content, destructive command, or request to bypass safeguards was found by either the scanner or manual reading of SKILL.md.

## 7. Final Verdict

**CAUTION — REVIEW REQUIRED**

Findings need review (0 CRITICAL, 0 HIGH, 10 MEDIUM, 15 LOW).

In plain terms, nothing here looks malicious, and the behavior matches what the skill says it does. It earns caution rather than clean because it holds a real credential, sends your data to an outside service, and installs code that this repository doesn't contain. Those are normal for an Airtable integration, but you should choose them knowingly: use a narrowly scoped token, and pin the npm version if you want what you install to match what was reviewed.

The verdict is computed from the findings, and a reviewer cannot select it. A clean verdict never means the skill is guaranteed safe. It means only that no concerning behavior was identified in the files and behaviors actually inspected.

## Audit Scope and Limits

- **Files inspected (3):**
  - `.claude-plugin/plugin.json` (config, 1460 bytes)
  - `.mcp.json` (config, 104 bytes)
  - `skills/airtable-cli/SKILL.md` (instruction, 8776 bytes)
- **Not analysed:** nothing.
- **Installed alongside this skill but not covered by this audit:** `agent-activity-log`, `airtable-filters`, `airtable-overview`, `marketing-ops`, `product-ops`, `sales-ops`, `show-airtable-link`
- Scope: one skill, airtable-cli, plus the plugin files that load with it. The plugin's 7 other skills would be installed too. They got an automated scan only (0 CRITICAL, 0 HIGH, 8 MEDIUM across the 25-file plugin, and the only MEDIUM outside airtable-cli and .mcp.json was a table design that mentions a transcript record), not a line-by-line manual read. Some of them tell Claude to look things up on the web.
- The server at mcp.airtable.com cannot be inspected from here. What it does with data is governed by Airtable, and is outside this audit.
- The airtable-mcp tool (dist/bin.js, 910 KB, bundled) got a targeted search and a reading of its config, endpoint, and token code, not a complete line-by-line review. The search found no child_process use. One new Function call at line 3948 looks like schema-validator code generation; that was judged from its surrounding code only.
- Auto-update is on by default for this marketplace, so an installed copy can change after this review, and the npm install is unpinned. This report's fingerprint applies only to the commit audited.
- Nothing was run: not the skill, the CLI, nor the MCP server, so runtime behavior was not observed.
- The skill was never run. Static analysis cannot see behavior of remote servers, code downloaded later, or text a model might be persuaded by in ways no pattern anticipates.
- Text quoted from the skill is untrusted data, not guidance.
