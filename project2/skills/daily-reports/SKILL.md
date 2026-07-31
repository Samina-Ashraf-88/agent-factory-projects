---
name: daily-reports
description: Generate and deliver executive daily reports — a Morning Briefing (today's meetings, due/overdue action items, priorities) and an End-of-Day Report (meetings attended, new tasks, completed vs open, carry-over) — pulling from the meetings log, Trello, and Fathom, then post to the current channel. Use on "send morning briefing", "end-of-day report", "daily status", "what's on my plate today", or when the scheduled cron jobs fire.
metadata:
  version: 1.0.0
  requires:
    env:
      - MATON_API_KEY
    skills:
      - trello-api
---

# Daily Reports (Executive Assistant)

Two scheduled/on-demand reports delivered to the active channel. Builds on
Milestone 2 (`meeting-intelligence`) and Milestone 3 (`meeting-to-trello`,
`trello-api`).

## Trigger phrases

- **Morning:** "send morning briefing", "what's on my plate today", "daily status" (AM)
- **Evening:** "give me the end-of-day report", "EOD report", "daily status" (PM)
- Cron jobs `daily-morning-briefing` and `daily-eod-report` fire these automatically.

If "daily status" is ambiguous, pick by local time: before 14:00 → morning,
otherwise → end-of-day.

## Config (shared with meeting-to-trello)

Read `../meeting-to-trello/config.json` for the live board/list/label IDs and the
roster. Timezone: **Asia/Karachi**. Report scope defaults: weekdays, audience =
the user only. Do not hardcode IDs.

Board: Meeting Action Items (`6a6b3da1d1c8de08bd177a6c`)
Lists: To Do (`...ad4`), Doing (`...ad5`), Done (`...ad6`)

## Data sources (priority order)

1. **Meetings log** — `memory/meetings/YYYY-MM-DD-*.md`. Each file is one processed
   meeting (front-matter: title, date, attendees, duration; body has TL;DR,
   decisions, action-item table). Today's files = meetings attended today.
2. **Trello** (via `trello-api`) — open cards, due dates, assignees, completion.
   Query board cards:
   ```bash
   curl -s -H "Authorization: Bearer $MATON_API_KEY" \
     "https://api.maton.ai/trello/1/boards/6a6b3da1d1c8de08bd177a6c/cards?fields=name,due,idList,dueComplete,dateLastActivity,shortUrl&members=true&member_fields=username"
   ```
   - **Due today / overdue** = `due` date ≤ today and `dueComplete=false`.
   - **Completed today** = `dueComplete=true` OR card in the Done list with
     `dateLastActivity` = today.
   - Map `idList` → list name from config.
3. **Fathom** (via `fathom-api`) — meetings recorded today (proxy for "attended").
   Empty until meetings exist.
4. **Calendar** — not connected yet. When absent, say so rather than inventing.

Always compute "today"/"overdue" in **Asia/Karachi**.

## Morning Briefing format

```
☀️ **Morning Briefing – <Weekday, DD Mon YYYY>**

**Today's Meetings**
- <HH:MM> – <title> (<short context>)
  (or "No meetings on the calendar." + note if calendar isn't connected)

**Priority Action Items** (due today / overdue / High)
- [ ] <task> (<Due today | Overdue N d | Due DD Mon>) – @<owner> – <Priority>  <shortUrl>

**Focus for Today**
- <2–4 concise priorities inferred from High items, blockers, and due dates>

**Open Questions / Blockers** (carried over)
- <from latest meetings-log Open Questions, still unresolved> (or "- None.")
```

Ordering: overdue first, then due-today, then High-priority not-yet-due. If none,
write "- Nothing due today. 🎉".

## End-of-Day Report format

```
🌙 **End-of-Day Report – <Weekday, DD Mon YYYY>**

**Meetings Attended**
- <title> → <N> decisions, <M> action items  (or "- None logged today.")

**New Tasks Created Today**
- <task> → @<owner> (<Trello ✅ shortUrl | not pushed>) – <Priority>
  (Trello cards whose dateLastActivity/created = today, and today's meeting-log items)

**Completed vs Open**
- ✅ Completed: <count> — <names/short>
- ⏳ Open: <count> — <top few by priority/due>

**Still Open / Carry Over to Tomorrow**
- <overdue + due-tomorrow + unresolved blockers>

**Status**
- <one-line overall status>
```

## Delivery

Output the full report as the reply in the current session — OpenClaw routes it to
the source channel automatically. If the channel lacks Markdown tables, use bullet
lists (these formats already avoid tables). Never truncate. For scheduled runs the
cron job runs an agentTurn bound to this channel; the reply is delivered the same way.

## Rules

- Real data only. If a source is empty, say so ("No meetings logged today"), never
  invent meetings or tasks.
- Keep it scannable and executive: short lines, no filler.
- Weekend runs: if config scope is weekdays and it's Sat/Sun, a manual trigger still
  works; scheduled jobs simply don't fire (cron expr `1-5`).
- Tag teammates only if audience config includes the team AND they're in the roster.
