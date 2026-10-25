# Delegation Record: 7-day MCP study plan

```
DELEGATION RECORD

Job: 7-day study plan: building MCP servers             Date: 25 Oct 2026

THE BRIEF
Outcome:      A study plan for building MCP servers for the next seven
              days, Mon 26 Oct to Sun 1 Nov 2026.
Context:      About 2 hours a day, evenings 9-11 pm PKT. Finished Agent
              Factory lessons on briefs and the Delegation Record; used
              connectors and skills; basic Python. No MCP server built
              yet. Goal: a small working server by Sunday.
Constraints:  No more than 2 hours a day. One rest day. Topics build in
              order, from what MCP is to a working server.
Authority:    You choose the order of topics. Ask me before including
              anything paid (courses, books, subscriptions, API credits).
Deliverable:  A seven-row table: day (with date), topic, time, resource.
Verification: Every resource must have a link I can open.

THE RUN
Assistant used: Claude                Messages needed: 1
Plan asked for first?  no             Plan changed by me?  no
Where it drifted, and the move that fixed it:
  Direct fetches of the official docs and course pages were blocked.
  The AI found the same pages through search and opened those links,
  so every link in the table was confirmed to load. General search
  results were mostly paid courses and copies of the docs; the AI used
  official sources and left the paid ones out instead of asking.

THE CHECK
Claim 1 that mattered: Anthropic Academy "Introduction to MCP" is free
                       and usable
  Source opened: anthropic.skilljar.com course page
  Finding: Free ("Register | FREE"), Python, ~14 lessons. Page showed
           "video still processing" and "rate limit" errors. Test
           before Sunday; Hugging Face course is the fallback.
Claim 2 that mattered: Claude Desktop runs local MCP servers on my plan
  Source opened: Official "Connect to local MCP servers" page
  Finding: Page gives Windows steps but doesn't say which plans are
           supported. Unverified; test on Wednesday.
Anything AI marked "unverified":
  Claude Desktop plan support for local servers; Anthropic Academy
  video availability. Also flagged: weather tutorial only returns US
  forecasts (free NWS API, no key).

THE DECISION
Accept. Every resource is free and has a working link, the order
builds to the Sunday goal, and the two risks (Academy videos, Claude
Desktop plan support) are named with fallbacks.

THE SECOND RUN (Concept 11)
Assistant:            Finished?    Brief changed?    Where the results differed:
  (not yet done: run the same brief in a different assistant and compare)

WHAT I WILL SAVE FOR NEXT TIME (Concept 8)
Lines that did not change:
  Authority: "Ask me before including anything paid (courses, books,
             subscriptions, paid API credits)."
  Verification: "Every resource must have a link I can open."
  Constraints: "No more than [hours] a day. One rest day."
Lesson for next brief: name a finish line in the Context ("a small
  working server by Sunday"), so the topic order can be judged. Add
  the tools I already have installed (Node, Python, uv), so setup time
  is planned rather than discovered mid-week.
```

## Open actions

- [ ] Wed 28 Oct: test whether Claude Desktop connects to a local server on my plan.
- [ ] Before Sun 1 Nov: open the Anthropic Academy course and check the videos play.
- [ ] THE SECOND RUN: paste the same brief into another assistant and compare.

See [`results/study-plan.md`](results/study-plan.md) for the full table.
