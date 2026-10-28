# Project Brief: Samina Ashraf personal website

## The person

Samina Ashraf is a geologist and geophysicist who is now studying IT and AI and builds AI agents, automations and small web apps.

**Evidence I checked.** Every claim on the site comes from one of these sources:

| Source | What it proves |
|---|---|
| `D:\agent factory\pt-2\` (project summary and screenshots) | The AI Meeting Assistant: 5 custom OpenClaw skills, Fathom and Trello through managed OAuth, a live Trello board, scheduled daily reports |
| GitHub `agent-factory-projects/project2` | Source for the Meeting Assistant |
| GitHub `Hackathon-5` README | Flowbit Customer Success "Digital FTE": OpenAI Agents SDK, FastAPI, Kafka, PostgreSQL + pgvector, Gmail/WhatsApp/web-form channels, pytest suite |
| `D:\agent factory\Snake-battle`, `CRITTER BONK` + live Netlify URLs (both return HTTP 200) | Two shipped browser games, one with a 70-check headless-browser test suite |
| GitHub `agent-factory-projects/project3–5` | Delegation Records: briefing an AI assistant, checking its claims, recording the decision |
| `D:\agent factory\pt-1\` | Canva MCP connected to a coding agent, plus custom LinkedIn-post and design skills |
| GitHub profile (10 public repos) | Python, TypeScript/JavaScript, HTML/CSS, OpenAI Agents SDK work |

**Not available, so not claimed.** No certificates, degree details, employers, dates of experience, location, photo or email address were supplied. The site leaves these out, and the README explains how to add them.

## Primary audience

1. **Recruiters and hiring managers** looking for junior AI / automation talent. They need: who she is, what she can build, proof, and a way to reach her.
2. **Small teams and businesses** that lose time to repetitive work (meeting follow-up, support inboxes). They need: "could she automate this for me?" and an example.

Secondary: classmates, developers, friends and family.

## The one message

> **Samina builds AI agents that turn messy, repetitive work into finished tasks, and she checks that they actually work.**

The geoscience background is the memorable hook. It isn't a detour: it's where the habit of working with data and evidence comes from.

## The one action

**Primary:** reach her on LinkedIn (the only verified contact channel).
**Secondary:** see the featured project, then the source code on GitHub.

## Visual personality

Calm, precise, field-notebook editorial. It should feel like a well-kept lab notebook rather than a startup landing page.

- **Signature motif:** a hand-drawn *seismic trace* (a geophysics wiggle line) under the hero, and thin "strata" rules between sections. It's personal to her background and costs no images.
- **Identity mark:** "SA" monogram (no photo was supplied, so none is invented).

## Colour palette

| Token | Hex | Use |
|---|---|---|
| Paper | `#F7F4EE` | Page background (warm, not stark white) |
| Surface | `#FFFFFF` | Cards, image frames |
| Ink | `#1B2433` | Headings, body text (14.2:1 on paper) |
| Muted ink | `#4E5869` | Secondary text (6.5:1 on paper) |
| Teal (accent) | `#16615C` | Links, primary button, focus ring (6.6:1 on paper) |
| Ochre (sediment) | `#8F4D18` (labels, 5.9:1) · `#A65A1E` (seismic trace) | Small labels and the trace only, never body text |
| Rule | `#DDD6CA` | Borders and strata lines |

## Typography

Two families, both system fonts, so there are **zero font downloads**:

- **Headings:** a serif stack (`Iowan Old Style`, `Palatino Linotype`, `Palatino`, `Georgia`) for an editorial voice.
- **Body/UI:** the system sans stack (`Segoe UI`, `-apple-system`, `Roboto`, `Helvetica Neue`, `Arial`).

Hierarchy: hero headline `clamp(2.1rem → 3.6rem)` · section headings `clamp(1.6rem → 2.2rem)` · body `1.0625rem / 1.65` · labels are `0.78rem` uppercase, tracked.

## Layout

Single column, max content width ~68rem, mobile-first. Sections in order, each kept only if it earns its place:

1. Header: monogram, 3 nav links, "Contact" button
2. Hero: name, specific headline, one-line explanation, LinkedIn CTA + "See the meeting agent", and a linked preview of the featured project (added after the recruiter review)
3. Featured project: AI Meeting Assistant (real screenshots, pipeline, my role, honest status)
4. More work: Flowbit Digital FTE, Snake Battle, Critter Bonk (live demos + code)
5. What I can do for you: 3 capability groups, written as outcomes
6. About: short and human, including the geoscience-to-AI story
7. How I learn: hackathons, delegation records (evidence in place of certificates)
8. Contact: LinkedIn + GitHub (email slot ready but hidden until supplied)
9. Footer

## Credibility evidence

Real screenshots of the Trello board the agent filled and the 5 skills in OpenClaw; two **live, clickable** games; public source code for everything; and a stated limitation on the featured project (Discord delivery awaiting an admin permission). Showing a limitation honestly makes the rest easier to believe.

## Excluded on purpose

- "Passionate", "hardworking", "love learning" and similar adjectives
- Skill bars, percentages and logo walls
- Invented metrics, testimonials or certifications
- A contact form (there is no backend to receive it)
- Resume Builder (its live link returns 404; the source is still on GitHub)
- Heavy animation, gradients, glassmorphism and stock photos
- JavaScript: nothing on the page needs it, so the site ships with **no script at all**
