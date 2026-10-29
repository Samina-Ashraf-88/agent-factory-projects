Based on the skill definition in `.claude/skills/weekly-study-notes/SKILL.md`:

## When to use it

Use it when you've shared your own class notes, lecture notes or course material and want them turned into organized study or revision notes. The notes can be pasted, attached, or given as a file path. You don't have to say "study notes" for it to apply. Requests like these also count:

- "Make notes from this"
- "Prepare my weekly notes"
- "Organize my notes for revision"
- "Clean up this week's lectures"

It works for any subject (biology, history, law, programming and so on). The output always has the same structure:
- A title, with the subject and week if the notes give them
- A numbered `##` heading for each major topic
- Short bullet points under each topic, plus a **Key terms** list with each term in bold and its definition
- A final **Review Questions** section with exactly three questions: one on recall, one on explanation, and one on application or comparison

## When NOT to use it

- **General questions about a subject**, like "What is photosynthesis?"
- **Solving a single homework problem**
- **Writing essays or research reports**
- **Lesson plans**, which are for teaching rather than revising your own notes
- **Advice on how to take notes**

## Edge cases

- **The request fits but there are no notes**, like "Prepare my study notes for this week" with nothing attached: the skill still applies, but it only asks you to paste or attach the notes. It won't make up content, because you couldn't tell invented material from what was actually taught.
- **The notes are unreadable or contradict each other**: it asks one short question. For minor gaps it makes a reasonable choice and carries on.

The main rule is faithfulness: everything in the output must come from your notes. It fixes typos and merges repeated points, but it doesn't add facts, even true ones. Anything it can't make out is marked `[unclear in notes]` instead of guessed.
