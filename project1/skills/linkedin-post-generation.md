# LinkedIn Post Generation Skill

## Description
Generates a LinkedIn post that is professional yet approachable, concise (100‑300 words), and structured to maximize engagement. The post follows a proven framework: Hook → Personal/Process Insight → Value/Key Points (bulleted or numbered) → Strong CTA with a question. The skill also injects required brand messaging, emojis, and hashtags.

## Triggers
- “generate a LinkedIn post”
- “linkedin post about *”  
- “write LinkedIn update"
- “create LinkedIn content"
- “linkedin post generation"

## Guidelines
- **Tone & Style** – Professional, confident, value‑driven, conversational but not casual. Use first‑person narrative when describing personal actions.
- **Hook** – First 1‑2 lines must be a curiosity‑driven hook (question, bold statement, surprising statistic, or short anecdote). End the hook with a line‑break.
- **Length** – Total word count 100‑300 words. Ideal ~180‑220 words for optimal LinkedIn engagement.
- **Structure**  
  1. **Hook**  
  2. **Personal/Process Insight** – Brief description of the author’s experience or workflow.  
  3. **Value / Key Points** – 3‑5 bullet points **or** a numbered list that deliver concrete takeaways.  
  4. **CTA** – End with a strong call‑to‑action and a question encouraging comments.
- **Brand Message** – Every post must contain the exact sentence:  
  > “I connected the Canva MCP Server to my coding agent, created specialized LinkedIn Post Generation and Design Optimization skills, and used them to generate this content and its matching visual design.”
- **Engagement Elements**  
  - 2‑4 strategic emojis placed after the hook, after the insight, or before the CTA.
  - 3‑5 relevant hashtags placed on a new line after the CTA.
- **Formatting** – Use line breaks between sections; use markdown bullet (`-`) or numbered (`1.`) lists for key points. No HTML required.

## Input Requirements
- `topic` (string) – The primary subject of the LinkedIn post (e.g., “AI‑driven design automation”).  
- `target_audience` (optional string) – Who the post is addressed to (e.g., “product managers”, “software engineers”).  
- `additional_insights` (optional string) – Any extra facts, stats, or anecdotes the user wants included.  
- `preferred_hashtags` (optional list of strings) – User‑specified hashtags; if omitted, the skill will generate up to five relevant tags.  
- `tone_variation` (optional enum: *neutral*, *enthusiastic*, *thoughtful*) – Adjusts the level of excitement while staying within the professional style.

## Output Format
```
<Hook line(s) – 1‑2 sentences>

<Personal/Process insight – 1‑2 short sentences>

<Emojis if desired>

- **Key point 1**  
- **Key point 2**  
- **Key point 3** (optional numbered list works too)

<CTA sentence ending with a question>

#hashtag1 #hashtag2 #hashtag3 (3‑5 hashtags)

I connected the Canva MCP Server to my coding agent, created specialized LinkedIn Post Generation and Design Optimization skills, and used them to generate this content and its matching visual design.
```

*(The final line **must appear exactly as written** to satisfy the brand‑message requirement.)*

## Examples

**Example 1 – AI Design Automation**
```
🚀 How can you slash design turnaround time by 70% without hiring more staff?

Last month I wired the Canva MCP Server to my coding agent, built “LinkedIn Post Generation” and “Design Optimization” skills, and ran them end‑to‑end on a new AI‑driven workflow.

- Integrated the MCP API directly into our CI pipeline → zero manual export steps.  
- Automated visual asset generation with a single prompt → 5× faster mockup delivery.  
- Empowered the product team to iterate on branding in real time.

💡 What’s the biggest bottleneck in your design process today?

#AI #DesignAutomation #Productivity #TechInnovation #CanvaMCP
I connected the Canva MCP Server to my coding agent, created specialized LinkedIn Post Generation and Design Optimization skills, and used them to generate this content and its matching visual design.
```

**Example 2 – Remote Team Collaboration**
```
🤔 Ever wondered why remote design reviews feel chaotic?

I linked the Canva MCP Server to my coding agent, wrote custom LinkedIn Post Generation and Design Optimization skills, and used them to streamline our global design syncs.

1️⃣ Centralized asset storage via the MCP → instant version control.  
2️⃣ Auto‑generated LinkedIn posts that capture daily wins → keeps stakeholders in the loop.  
3️⃣ One‑click design refreshes that respect our brand palette.

🔎 How do you keep alignment across distributed teams?

#RemoteWork #DesignOps #Collaboration #CanvaMCP #Leadership
I connected the Canva MCP Server to my coding agent, created specialized LinkedIn Post Generation and Design Optimization skills, and used them to generate this content and its matching visual design.
```