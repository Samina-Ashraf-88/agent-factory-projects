---
name: meeting-intelligence
description: Turn a meeting transcript (Fathom/Otter API, local file path, or pasted text) into a structured summary with key decisions, an action-item table (owner + deadline + priority), open questions, and next steps — then deliver it to the current channel. Use when the user says "process my last meeting", "summarize the <name> transcript", "get the latest Fathom/Otter transcript and process it", or pastes/points to a transcript.
metadata:
  version: 1.0.0
  outputs: [markdown]
---

# Meeting Intelligence

Convert any meeting transcript into a clean, scannable brief and send it to the
active communication channel.

## When to use

Trigger on any of:

- "Process my last meeting" / "process my latest meeting"
- "Summarize the <meeting name> transcript"
- "Get the latest Fathom/Otter transcript and process it"
- User pastes a raw transcript
- User gives a local file path to a transcript
- "Meeting summary for <date/title/ID>"

## Step 1 — Get the transcript

Resolve the transcript from whichever source applies, in this priority order:

1. **Pasted text** — if the user pasted transcript content, use it directly.
2. **Local file** — if the user gave a path, read the file at that path.
3. **Fathom** — if the `fathom-api` skill is installed and the user asked for a
   Fathom/latest meeting: use it to list recent meetings and fetch the
   transcript (by most-recent, or by ID/title/date the user specified).
4. **Otter** — if the `otterai-cli` skill is installed and the user asked for
   Otter: use it to find and export the transcript.

If the user says "my last meeting" and more than one retrieval source is
configured, prefer Fathom, then Otter. If none is configured and nothing was
pasted, ask the user to paste the transcript, give a file path, or install a
retrieval skill.

Always read the **full** transcript before summarizing — do not sample.

## Step 2 — Produce the brief

Output in this EXACT format (Markdown). Omit a field's value only if truly
unavailable; never drop a section heading.

```
**Meeting Summary**
- **Title / Topic:**
- **Date:**
- **Attendees:**
- **Duration:** (if available)

**TL;DR**
(2–4 sentence high-level overview)

**Key Decisions**
- Bullet list of explicit decisions made

**Action Items**
| # | Task | Owner | Deadline | Priority |
|---|------|-------|----------|----------|
| 1 | ... | ... | ... | High/Med/Low |

**Open Questions / Blockers**
- List any unresolved items

**Next Steps**
- Short list of follow-up actions
```

## Step 3 — Extraction rules

- **Action items** — scan for commitment/assignment cues:
  "I'll…", "I will…", "[Name] will…", "[Name] is going to…", "Action item:",
  "We need to…", "Can you…", "Could you…", "Let's…", "make sure to…",
  "follow up on…", "take ownership of…", "by <day/date>".
- **Owners** — assign from the speaker label of the person committing, or from an
  explicit mention ("Sarah will…"). If the owner is unclear, use **Unassigned**.
- **Deadlines** — capture any stated date/time ("by Friday", "end of Q3",
  "next standup", "before launch"). Normalize relative dates against the meeting
  date when known. If none is stated, use **TBD**.
- **Priority** — infer High/Med/Low from urgency language ("urgent", "blocker",
  "ASAP", "critical" → High; "nice to have", "eventually", "when we get a chance"
  → Low; default **Med**). If ambiguous, use Med.
- **Key Decisions** — only include explicit decisions ("we decided", "we're going
  with", "approved", "final call"), not open discussion.
- **Open Questions / Blockers** — anything left unresolved, awaiting input, or
  flagged as blocking. If none, write "- None raised."
- Keep language concise and professional. No filler, no invented details. If the
  transcript lacks a piece of info (e.g. attendees), write "Not specified".

## Step 4 — Deliver

After generating the brief, send the full formatted result to the current
communication channel (the session the user is talking to you in). In OpenClaw,
replying in the current session routes to the source channel automatically —
just output the brief as your reply. Do not truncate the action-item table.

If the target channel does not support Markdown tables (e.g. WhatsApp/Discord),
render Action Items as a numbered bullet list instead:
`1. <Task> — Owner: <owner> — Deadline: <deadline> — Priority: <priority>`.

## Step 5 — Persist (for daily reports)

After delivering, save the brief to `memory/meetings/YYYY-MM-DD-<slug>.md` (date =
meeting date; slug = kebab-cased title). Include front-matter
(`title, date, attendees, duration, trello_pushed`) followed by the TL;DR,
Key Decisions, and the Action Items table. This is the durable source the
`daily-reports` skill (Milestone 4) reads for meetings attended and new action
items. Skip only if the user explicitly says not to save.

## Retrieval helper commands

Fathom (if `fathom-api` installed): follow that skill's SKILL.md to list recent
meetings and fetch a transcript. Typical flow: list meetings → pick most recent
or match by ID/title/date → fetch transcript text → feed into Step 2.

Otter (if `otterai-cli` installed): follow that skill's SKILL.md to search and
export the transcript, then feed the exported text into Step 2.

## Phrases the user can say

- "Process my last meeting"
- "Summarize the <meeting name> transcript"
- "Get the latest Fathom transcript and process it"
- "Process this transcript: <paste>"
- "Process the transcript at <file path>"
- "Meeting summary for <ID/title/date>"
