# Design Optimization Skill

## Description
Optimizes visual assets according to a modern tech‑brand guideline. The skill takes a LinkedIn post (or any short narrative) and produces a design brief that defines colors, typography, layout, and visual hierarchy. The output can be fed directly to a design generation pipeline (e.g., Canva MCP) to create a matching image, carousel, or infographic that reinforces the post’s tone and message.

## Triggers
- “optimize design"
- “design optimization for *"  
- “create visual for LinkedIn post"
- “generate design brief"
- “apply brand guidelines"

## Guidelines
- **Brand Identity** – Modern professional tech/innovation brand. Use the primary LinkedIn Blue `#0077B5` as the dominant hue, with teal/cyan accents (`#00BFA5`), neutral grays, and generous white space.
- **Design Principles**  
  - *Clean & Minimalist*: Remove unnecessary ornamentation.
  - *High Visual Hierarchy*: Headline size > sub‑headline > body.
  - *Scannable*: Use clear sections, icons, or bullet graphics to guide the eye.
  - *Mobile‑First*: All elements must stay legible on a 360 px width viewport.
- **Visual Style** – Bold sans‑serif headings (Montserrat, Inter, or similar), clean body text, balanced composition, energetic accent blocks that match the post’s emotional tone (dynamic layout for enthusiastic posts, calm grid for thoughtful posts).
- **Output Compatibility** – The brief must be a JSON‑compatible structure that can be passed directly to Canva’s MCP “Create Design” endpoint or any template‑based generator.
- **Accessibility** – Ensure contrast ratio ≥ 4.5:1 for text vs. background; avoid color‑only cues.
- **Brand Message Inclusion** – Append the exact brand sentence (see LinkedIn Post skill) to the design brief’s `copy_notes` field.

## Input Requirements
- `post_text` (string) – The fully‑generated LinkedIn post (plain text).
- `post_tone` (enum: *energetic*, *thoughtful*, *neutral*) – Determines layout dynamism.
- `desired_format` (enum: *single‑image*, *carousel*, *infographic*) – Target output type.
- `custom_assets` (optional list of URLs) – Specific images or icons the user wants incorporated.
- `size` (optional string, default `1080x1080`) – Desired canvas dimensions (e.g., `1080x1080`, `1200x628` for LinkedIn sharing).

## Output Format
The skill returns a **Design Brief** JSON object with the following schema:

```json
{\"brand_guidelines\": {\"primary_color\": \"#0077B5\",\"accent_colors\": [\"#00BFA5\", \"#5A6268\"],\"neutral_gray\": \"#F5F5F5\",\"font_headings\": \"Montserrat\",\"font_body\": \"Inter\"},\"layout\": {\"type\": \"<desired_format>\", // \"single-image\" | \"carousel\" | \"infographic\"\"canvas_size\": \"<size>\", // e.g., \"1080x1080\"\"structure\": [\"header\", \"visual\", \"body\", \"cta\"],\"visual_hierarchy\": {\"header\": {\"font_size\": 48, \"color\": \"#0077B5\"},\"subheader\": {\"font_size\": 32, \"color\": \"#00BFA5\"},\"body\": {\"font_size\": 20, \"color\": \"#333333\"}}},\"content\": {\"headline\": \"<extracted hook>\",\"subheadline\": \"<optional derived from insight>\",\"body_points\": [\"<point 1>\", \"<point 2>\", \"...\"],\"cta\": \"<final CTA sentence>\"},\"assets\": {\"custom_urls\": [\"<url-1>\", \"<url-2>\"],\"suggested_icons\": [\"lightbulb\", \"rocket\", \"chart\"]},\"copy_notes\": \"I connected the Canva MCP Server to my coding agent, created specialized LinkedIn Post Generation and Design Optimization skills, and used them to generate this content and its matching visual design.\"}\n```

All fields must be present; optional fields may be empty arrays.

## Examples

**Example 1 – Energetic Carousel for AI Automation Post**

*Input*
```json
{\"post_text\": \"🚀 How can you slash design turnaround time by 70% without hiring more staff?\nLast month I wired the Canva MCP Server to my coding agent, built \"LinkedIn Post Generation\" and \"Design Optimization\" skills, and ran them end‑to‑end on a new AI‑driven workflow.\n- Integrated the MCP API directly into our CI pipeline → zero manual export steps.\n- Automated visual asset generation with a single prompt → 5× faster mockup delivery.\n- Empowered the product team to iterate on branding in real time.\n💡 What’s the biggest bottleneck in your design process today?\n#AI #DesignAutomation #Productivity #TechInnovation #CanvaMCP\",\"post_tone\": \"energetic\",\"desired_format\": \"carousel\",\"size\": \"1080x1080\"}\n```

*Output*
```json
{\"brand_guidelines\": {\"primary_color\": \"#0077B5\",\"accent_colors\": [\"#00BFA5\", \"#5A6268\"],\"neutral_gray\": \"#F5F5F5\",\"font_headings\": \"Montserrat\",\"font_body\": \"Inter\"},\"layout\": {\"type\": \"carousel\",\"canvas_size\": \"1080x1080\",\"structure\": [\"header\", \"visual\", \"body\", \"cta\"],\"visual_hierarchy\": {\"header\": {\"font_size\": 52, \"color\": \"#0077B5\"},\"subheader\": {\"font_size\": 36, \"color\": \"#00BFA5\"},\"body\": {\"font_size\": 22, \"color\": \"#333333\"}}},\"content\": {\"headline\": \"🚀 How can you slash design turnaround time by 70% without hiring more staff?\",\"subheadline\": \"Last month I wired the Canva MCP Server to my coding agent, built the two new skills, and ran them end‑to‑end.\",\"body_points\": [\"Integrated the MCP API directly into our CI pipeline → zero manual export steps.\",\"Automated visual asset generation with a single prompt → 5× faster mockup delivery.\",\"Empowered the product team to iterate on branding in real time.\"],\"cta\": \"💡 What’s the biggest bottleneck in your design process today?\"},\"assets\": {\"custom_urls\": [],\"suggested_icons\": [\"rocket\", \"lightbulb\", \"chart\"]},\"copy_notes\": \"I connected the Canva MCP Server to my coding agent, created specialized LinkedIn Post Generation and Design Optimization skills, and used them to generate this content and its matching visual design.\"}\n```

**Example 2 – Thoughtful Single‑Image for Remote Collaboration Post**

*Input*
```json
{\"post_text\": \"🤔 Ever wondered why remote design reviews feel chaotic?\nI linked the Canva MCP Server to my coding agent, wrote custom LinkedIn Post Generation and Design Optimization skills, and used them to streamline our global design syncs.\n1️⃣ Centralized asset storage via the MCP → instant version control.\n2️⃣ Auto‑generated LinkedIn posts that capture daily wins → keeps stakeholders in the loop.\n3️⃣ One‑click design refreshes that respect our brand palette.\n🔎 How do you keep alignment across distributed teams?\n#RemoteWork #DesignOps #Collaboration #CanvaMCP #Leadership\",\"post_tone\": \"thoughtful\",\"desired_format\": \"single-image\",\"size\": \"1200x628\"}\n```

*Output*
```json
{\"brand_guidelines\": {\"primary_color\": \"#0077B5\",\"accent_colors\": [\"#00BFA5\", \"#5A6268\"],\"neutral_gray\": \"#F5F5F5\",\"font_headings\": \"Montserrat\",\"font_body\": \"Inter\"},\"layout\": {\"type\": \"single-image\",\"canvas_size\": \"1200x628\",\"structure\": [\"header\", \"visual\", \"body\", \"cta\"],\"visual_hierarchy\": {\"header\": {\"font_size\": 48, \"color\": \"#0077B5\"},\"subheader\": {\"font_size\": 30, \"color\": \"#00BFA5\"},\"body\": {\"font_size\": 20, \"color\": \"#333333\"}}},\"content\": {\"headline\": \"🤔 Ever wondered why remote design reviews feel chaotic?\",\"subheadline\": \"I linked the Canva MCP Server to my coding agent, wrote custom skills, and streamlined global design syncs.\",\"body_points\": [\"Centralized asset storage via the MCP → instant version control.\",\"Auto‑generated LinkedIn posts that capture daily wins → keeps stakeholders in the loop.\",\"One‑click design refreshes that respect our brand palette.\"],\"cta\": \"🔎 How do you keep alignment across distributed teams?\"},\"assets\": {\"custom_urls\": [],\"suggested_icons\": [\"globe\", \"people\", \"layers\"]},\"copy_notes\": \"I connected the Canva MCP Server to my coding agent, created specialized LinkedIn Post Generation and Design Optimization skills, and used them to generate this content and its matching visual design.\"}\n```