---
name: meeting-to-trello
description: Turn extracted meeting action items into Trello cards — one card per item — with owner assignment, due dates, priority labels, and a source-meeting description, then post a confirmation to the current channel. Use when the user says "create Trello cards from the last meeting action items", "push action items to Trello", or "create Trello cards from these action items: <list>". Chains naturally after the meeting-intelligence skill.
metadata:
  version: 1.0.0
  requires:
    env:
      - MATON_API_KEY
    skills:
      - trello-api
---

# Meeting → Trello

Push meeting action items to Trello as assigned cards, then confirm in-channel.
Builds on `meeting-intelligence` (Milestone 2) and `trello-api`.

## When to use

Trigger on any of:

- "Create Trello cards from the last meeting action items"
- "Push action items to Trello"
- "Create Trello cards from these action items: <list>"
- Immediately after a `meeting-intelligence` run, if the user asks to send items to Trello.

## Config

Read `config.json` in this skill folder. It holds the live board/list/label IDs,
the team `roster` (name → Trello member), `keyword_rules`, and the `fallback`
behavior. Never hardcode IDs — always read them from config so re-pointing the
board is a one-file edit.

## Step 1 — Get action items

Use the action items from the most recent `meeting-intelligence` output in this
session, or the list the user pasted. Each item has: Task, Owner, Deadline,
Priority. Also keep the source meeting **title** and **date** for the description.

## Step 2 — Resolve the assignee (assignment logic)

For each action item, in order:

1. **Explicit owner** — if Owner is a real name, match it (case-insensitive)
   against `roster[].names`. On match, that's the assignee.
2. **Keyword routing** — if Owner is "Unassigned"/unclear, scan the Task text for
   `keyword_rules`. First role whose keyword appears wins; assign the first roster
   member with that role.
3. **Fallback** — if still unresolved:
   - `fallback: "flag"` → leave unassigned, mark ⚠️ in confirmation.
   - `fallback: "<member>"` or `default_assignee` set → assign that member.

**Board-membership check:** Trello only lets you assign members already on the
board (`on_board: true` in roster, or present in a live board-members lookup). If
the resolved member is NOT on the board, create the card **unassigned**, record
the intended owner in the description, and flag it as
"intended: @username — invite to board to activate."

## Step 3 — Create one card per item

POST to `1/cards` (see `trello-api` SKILL). Build each card:

- **name** — concise, verb-first task title derived from the action item.
- **idList** — `default_list.id` from config.
- **desc** (Markdown):
  ```
  **Action item:** <full task text>
  **Owner (from meeting):** <original owner name>
  **Source meeting:** <title> (<date>)
  **Deadline:** <deadline or TBD>
  **Priority:** <High/Medium/Low>
  ```
  If the resolved member isn't on the board, add:
  `**Intended assignee:** @username (not yet on board)`
- **due** — if Deadline is a real date, set ISO 8601 (default time 17:00Z);
  normalize relative dates ("by Friday") against the meeting date. If "TBD", omit.
- **idMembers** — `[member_id]` only when the member is on the board; else omit.
- **idLabels** — the priority label id (`High`/`Medium`/`Low`) plus optionally the
  `Meeting` label.

## Step 4 — Confirm in-channel

After creating all cards, reply with a clean confirmation. One line per card:

```
**Trello Cards Created** — <board name>
- ✅ "<card name>" → @<username> (Due: <date or TBD>) – <Priority>  <shortUrl>
- ⚠️ "<card name>" → unassigned (<reason>) (Due: <date or TBD>) – <Priority>  <shortUrl>
```

Use ✅ for successfully assigned cards, ⚠️ for unassigned/flagged. Always include
the card `shortUrl`. End with the board link and a one-line count summary
(e.g. "4 cards created — 1 assigned, 3 flagged").

## Notes

- Card creation is a real external write. If the user triggered this explicitly
  (any trigger phrase, or "yes push to Trello"), proceed without re-confirming.
  For a large/ambiguous batch not explicitly requested, confirm first.
- Keep the roster/board config in `config.json`. Editing the team or moving boards
  should never require touching this SKILL.md.
