# Review: the stranger test

Both evaluations were done on the running site (local server plus headless Chrome screenshots at 320, 375, 768, 1024 and 1440px wide). Scores are 1–10. "Before" is the first complete build; "after" is the version that ships.

## Evaluation A: Recruiter (8 seconds)

| Criterion | Before | After | In the recruiter's voice |
|---|---|---|---|
| Identity clarity | 8 | 8 | "Samina Ashraf, geoscientist turned AI agent builder. Clear, though I'd wonder which of the three roles she's applying for." |
| Value clarity | 8 | 8 | "The headline plus the meeting-to-Trello example tells me exactly what she builds." |
| Action clarity | 7 | 7 | "LinkedIn button is obvious. I'd still like an email address or a CV link." |
| **Credibility** | **6** | **8** | Before: "Everything above the fold is a claim. I can't see any work without scrolling, and half the screen is empty." After: "There's the actual Trello board her agent filled, right next to the headline." |
| Content quality | 8 | 8 | "No fluff words, no skill bars. Short and specific." |

**Lowest:** Credibility (6).
**Change made:** added a linked "Latest build" preview of the featured project to the hero: the real Trello screenshot plus a one-line caption. It sits beside the headline on desktop and below the buttons on phones. Proof now appears in the first screen, and it also fills the hero's empty right half.

## Evaluation B: Potential client / collaborator

| Criterion | Before | After | In the client's voice |
|---|---|---|---|
| Identity clarity | 8 | 8 | "She builds AI automations. Got it." |
| Value clarity | 7 | 7 | "I see what she did for meetings. I have to make the leap that she could do it for my process." |
| **Action clarity** | **6** | **8** | Before: "The contact section talks about roles and internships. As a business, what do I even say in a LinkedIn message to a stranger?" After: "It tells me exactly what to send in three lines. Easy." |
| Credibility | 8 | 8 | "Screenshots, two games I can actually play, public code, and she admits what's still unfinished. I believe it." |
| Content quality | 8 | 8 | "Tight. Nothing I skipped." |

**What would make me leave:** not knowing how to start the conversation, plus only one channel (LinkedIn).
**Change made:** rewrote the contact section around the client: a three-line brief to send (the task, the tools, how often), with a separate one-liner for recruiters. The button stays the same, but a cold message is now easy to write.

## Fixes found during technical testing (before the stranger test)

- The Snake Battle thumbnail was mostly empty arena, so I recropped it around the AI snakes.
- Nav and footer links were under 24px tall, so I added padding to meet WCAG 2.2 target size.
- The hero top padding was trimmed so more of the hero fits on small phones.

## What still limits the scores (needs Samina, not code)

1. **No CV link yet.** Email was added after the review (the contact section's main button, plus the footer). That gives clients a second, easier channel and addresses the client's "only one channel" concern.
2. **No certificates supplied.** "Learning in public" uses GitHub evidence in their place; a commented template is ready (search for `CERTIFICATES:`).
3. **The geoscience side has no proof yet.** One line about a degree, field project or thesis would make the "Geologist · Geophysicist" label as credible as the AI work.
4. **No photo.** The "SA" monogram is used instead; a real photo would add warmth.
