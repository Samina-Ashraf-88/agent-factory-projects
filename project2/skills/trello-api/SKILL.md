---
name: trello-api
description: |
  Trello API integration via Maton managed OAuth. List boards/lists/members, create and update cards, assign members, set due dates, and apply labels. Use when the user wants to create or manage Trello cards — especially pushing meeting action items to a board. Auth is the same MATON_API_KEY used by the fathom skill; no separate TRELLO_API_KEY/TRELLO_TOKEN needed.
compatibility: Requires network access and a valid MATON_API_KEY with an ACTIVE Trello connection
metadata:
  author: local
  version: "1.0"
  requires:
    env:
      - MATON_API_KEY
---

# Trello (via Maton)

Access the Trello REST API through Maton's managed-OAuth proxy. Maton injects the
OAuth token, so you only need `MATON_API_KEY`.

## Base URL

```
https://api.maton.ai/trello/{native-trello-path}
```

Maton proxies to `api.trello.com/1/...`. So the native path `1/boards/{id}/lists`
becomes `https://api.maton.ai/trello/1/boards/{id}/lists`.

## Authentication

Every request needs the Maton key:

```
Authorization: Bearer $MATON_API_KEY
```

Note: unlike the direct Trello API, you do NOT append `key=` / `token=` query
params — Maton handles auth. If multiple Trello connections exist, add
`Maton-Connection: {connection_id}`.

## Verify connection

```bash
curl -s -H "Authorization: Bearer $MATON_API_KEY" \
  "https://api.maton.ai/connections?app=trello&status=ACTIVE"
```

If none is ACTIVE, create one and open the returned `url` to authorize:

```bash
curl -s -H "Authorization: Bearer $MATON_API_KEY" -H "Content-Type: application/json" \
  -X POST -d '{"app":"trello"}' "https://api.maton.ai/connections"
```

## Common calls

### List my boards
```bash
curl -s -H "Authorization: Bearer $MATON_API_KEY" \
  "https://api.maton.ai/trello/1/members/me/boards?fields=name,url,id"
```

### List a board's lists
```bash
curl -s -H "Authorization: Bearer $MATON_API_KEY" \
  "https://api.maton.ai/trello/1/boards/{board_id}/lists?fields=name,id"
```

### List board members
```bash
curl -s -H "Authorization: Bearer $MATON_API_KEY" \
  "https://api.maton.ai/trello/1/boards/{board_id}/members?fields=fullName,username,id"
```

### Create a board (with default To Do / Doing / Done lists)
```bash
curl -s -H "Authorization: Bearer $MATON_API_KEY" -H "Content-Type: application/json" \
  -X POST -d '{"name":"Meeting Action Items","defaultLists":true}' \
  "https://api.maton.ai/trello/1/boards"
```

### Create a label
```bash
curl -s -H "Authorization: Bearer $MATON_API_KEY" -H "Content-Type: application/json" \
  -X POST -d '{"name":"High","color":"red","idBoard":"{board_id}"}' \
  "https://api.maton.ai/trello/1/labels"
```

### Create a card
POST `1/cards`. Key fields (send as JSON):
- `name` — card title (required)
- `idList` — target list id (required)
- `desc` — description (Markdown)
- `due` — ISO 8601 due date, e.g. `2026-08-05T17:00:00Z` (omit for no due date)
- `idMembers` — array of member ids to assign
- `idLabels` — array of label ids

```bash
curl -s -H "Authorization: Bearer $MATON_API_KEY" -H "Content-Type: application/json" \
  -X POST -d '{
    "name":"Fix login timeout bug",
    "idList":"{list_id}",
    "desc":"Owner: Alex\nMeeting: V2.1 Sync (2026-07-28)\nDeadline: 2026-08-01",
    "due":"2026-08-01T17:00:00Z",
    "idMembers":["{member_id}"],
    "idLabels":["{high_label_id}"]
  }' "https://api.maton.ai/trello/1/cards"
```

Response includes the new card's `id`, `shortUrl`, and `url`.

### Assign / unassign a member on an existing card
```bash
# add
curl -s -H "Authorization: Bearer $MATON_API_KEY" -X POST \
  "https://api.maton.ai/trello/1/cards/{card_id}/idMembers?value={member_id}"
# remove
curl -s -H "Authorization: Bearer $MATON_API_KEY" -X DELETE \
  "https://api.maton.ai/trello/1/cards/{card_id}/idMembers/{member_id}"
```

## Rules & gotchas

- Only members already on the board can be assigned (`idMembers`). Assigning a
  member id not on the board returns an error — invite them first, or create the
  card unassigned and flag it.
- All write operations (create board/card/label, assign) are real external
  changes. Confirm intent before bulk creation the user did not explicitly ask for.
- Use `-g` with curl if a URL contains brackets.
- Due dates must be ISO 8601. Convert relative deadlines ("by Friday") against the
  meeting date before setting `due`. If a deadline is "TBD", omit `due`.

## Error table

| Status | Meaning |
|--------|---------|
| 400 | Bad request (e.g. member not on board, bad list id) |
| 401 | Invalid/missing MATON_API_KEY |
| 404 | Resource not found or no Trello connection |
| 429 | Rate limited |
