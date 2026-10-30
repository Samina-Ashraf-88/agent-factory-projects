---
name: tidy-text
description: Tidies pasted text by trimming spaces and normalizing line breaks. Use when the user asks to clean up text.
---

# Tidy Text

Take the text the user pasted and return a tidied copy.

1. Trim spaces at the end of each line.
2. Collapse runs of blank lines into one.
3. Return the result in a code block.

Formatting follows the conventions at https://commonmark.org/.
