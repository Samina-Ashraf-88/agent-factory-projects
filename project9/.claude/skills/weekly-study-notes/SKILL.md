---
name: weekly-study-notes
description: Turns a student's raw class or lecture notes into organized study notes with a heading per topic, bold key terms with definitions, and exactly three review questions at the end. Use this whenever the user shares (or asks you to work from) their own class notes, lecture notes, lecture slides or transcripts, or other course material and wants them made into study notes, weekly notes, or revision notes, or tidied and organized for studying. Use it even when they don't say "study notes", e.g. "make notes from this", "prepare my weekly notes", "organize my notes for revision", "clean up this week's lectures". Do not use it for general questions about a subject, solving a single homework problem, writing essays or research reports, lesson plans, advice on how to take notes, or non-study notes such as meeting or work notes.
---

# Weekly Study Notes

Turn a student's raw class notes (messy bullets, half-sentences, typos, repetition) into clean study notes they can revise from. The notes may be from any subject: science, history, law, languages, programming, and so on. Treat whatever subject appears as the subject. Don't assume one.

## First, check that there are notes to work from

- **Notes are present** (pasted in the message, an attached file, or a file path you can read): start writing the study notes right away. Don't ask for confirmation or preferences first.
- **No notes are present** (e.g. "Prepare my study notes for this week." with nothing attached): ask the user to paste or attach their notes or the class material, in one or two short sentences. Don't produce sample notes or guess what the week covered. Invented content is worse than useless to someone revising for an exam, because they can't tell it apart from what was actually taught.
- **An essential ambiguity blocks accurate work** (e.g. the file is unreadable, or two sets of notes conflict and you can't tell which is current): ask one concise question. Otherwise, make reasonable choices and proceed. Minor gaps are not a reason to ask.

## Faithfulness rules

The study notes are only valuable if the student can trust that everything in them came from their class.

- Keep every important fact, definition, example, formula, date, name, and explanation from the source.
- Fix obvious spelling, grammar, and abbreviation slips (e.g. "photosynthsis" → "photosynthesis") without changing meaning.
- Merge repeated points into one. Don't drop a detail just because it's small, though. Exam questions often hinge on small details.
- Don't add facts, examples, dates, or definitions that aren't in the notes, even ones you know are true. If a term appears without a definition in the notes, describe it only as far as the notes support (e.g. how it was used or what it relates to), or list it without a definition. Keep the notes' own framing, too. Don't strengthen or reclassify a claim (e.g. calling something "a theory" or "the main cause" when the notes don't).
- If a fragment is too garbled to interpret, keep it and mark it `[unclear in notes]` rather than guessing.

## Output format

Use this structure every time:

1. **Title**: `# <Subject> Study Notes`, adding the week or date if the notes give one (e.g. `# Geology — Week 1 Study Notes`). If no subject is evident, use `# Study Notes`.
2. **One `##` heading per major topic**, numbered (`## 1. Rock Types`). Group related points under the topic they belong to, even if they were scattered in the original. Use `###` subheadings only when a topic has clearly distinct subtopics.
3. **Under each topic**:
   - Concise bullet points covering the content. Keep formulas, dates, and figures exact.
   - A `**Key terms**` list of the most revision-worthy terms for that topic (usually 2–5). Write each as `- **Term**: definition from the notes`. Bold the term itself.
4. **`## Review Questions`** as the final section, containing exactly three numbered questions:
   1. Basic understanding or recall of a definition.
   2. Explanation, relationships, or conceptual understanding (how/why something works, how ideas connect).
   3. Application, comparison, or deeper understanding (apply a concept, compare two things, reason through a case).

   Every question must be answerable from the notes themselves. If the notes are thin, ask about what's there rather than reaching beyond it.

Exactly three questions, and only in that final section, because the student uses them as a fixed self-test at the end of each week's notes. So:
- Don't put "check your understanding" questions, quizzes, or prompts inside the topic sections.
- If the source notes themselves contain questions (e.g. "Q from class: why does X happen? (answer: Y)"), keep the content but write it as a statement of fact in the topic section ("X happens because Y"). Leave out a question the notes don't answer, or mark it `[unanswered in notes]` as a statement.
- End the response with the third review question. Don't add a closing remark or follow-up offer (like "Want me to make flashcards?") after it, since that reads as a fourth question.

If the user asks for a file, write the same content to a Markdown file (e.g. `week-1-study-notes.md`). Otherwise reply in chat.

## Example

Input notes:
```
bio wk3 - cells
cell = basic unit of life. all living things made of cells
prokaryotes no nucleus (bacteria) eukaryotes have nucleus
mitochondria - makes ATP, "powerhouse"
cell membrane controls what enters/leaves, phospholipid bilayer
```

Output:
```markdown
# Biology — Week 3 Study Notes

## 1. Cells and Cell Types
- The cell is the basic unit of life; all living things are made of cells.
- Prokaryotes have no nucleus (e.g. bacteria). Eukaryotes have a nucleus.

**Key terms**
- **Cell**: the basic unit of life.
- **Prokaryote**: a cell without a nucleus, such as a bacterium.
- **Eukaryote**: a cell with a nucleus.

## 2. Cell Structures
- Mitochondria make ATP and are known as the "powerhouse" of the cell.
- The cell membrane controls what enters and leaves the cell and is a phospholipid bilayer.

**Key terms**
- **Mitochondria**: organelles that make ATP.
- **Cell membrane**: a phospholipid bilayer that controls what enters and leaves the cell.

## Review Questions
1. What is the difference between a prokaryote and a eukaryote?
2. Why are mitochondria described as the "powerhouse" of the cell?
3. Compare the roles of the mitochondria and the cell membrane in keeping a cell functioning.
```
