# weekly-study-notes: a Claude Code skill

Turns raw class notes (messy bullets, typos, repetition) into clean study notes for revision:

- a numbered heading for each topic
- a **Key terms** list per topic, with terms in bold and definitions taken from your notes
- exactly three review questions at the end (recall → explanation → application)

It works for any subject. It doesn't add facts that aren't in your notes. If you ask for study notes without supplying any, it asks for them instead of making something up.

You don't need to name the skill. Ask naturally:

> Make study notes from this: …
> Prepare my weekly notes. …
> Organize my notes for revision.
> Turn these class notes into study notes.
> Create study notes from this week's lectures.

## Project layout

```
real skill/
├── .claude/skills/weekly-study-notes/   ← the skill (project-level install)
│   ├── SKILL.md                         ← the only file Claude needs
│   └── evals/                           ← 5 test cases (claude plugin eval format)
├── tests/
│   ├── run_cases.py                     ← runs + grades the 5 cases (with/without skill)
│   ├── trigger_eval.py                  ← checks real activation on 20 queries
│   └── trigger_queries.json
├── weekly-study-notes-workspace/        ← test results per iteration (safe to delete)
└── README.md
```

## Installation

The skill is already installed **for this project**. Claude Code loads skills from `.claude/skills/` in the folder where you start it. Start `claude` inside `D:\agent factory\real skill` and the skill is available.

To use it **in every project**, copy it to your personal skills folder (`%USERPROFILE%\.claude\skills\`):

```powershell
Copy-Item -Recurse ".claude\skills\weekly-study-notes" "$env:USERPROFILE\.claude\skills\"
```

(Bash or macOS/Linux: `cp -r .claude/skills/weekly-study-notes ~/.claude/skills/`.) Only `SKILL.md` matters. You can leave `evals/` out of the copy if you want.

No other registration or "Save skill" step is needed for Claude Code. Skills are plain files and are picked up when a session starts.

## Verify Claude Code recognizes it

1. Start a **new** session in the project folder: `claude`
2. Type `/` and look for `weekly-study-notes` in the list, or ask *"What skills do you have available?"*
3. Paste some notes with "Make study notes from this:". The transcript shows the skill being loaded (`Skill(weekly-study-notes)`) before the answer.

Non-interactive check (prints the tools the session used):

```bash
claude -p "Make study notes from this: atom = smallest unit of an element. protons +, electrons -." --output-format stream-json --verbose | grep -o '"name":"Skill","input":{[^}]*}'
```

## Running the tests

These make real, billed Claude calls. Run them from the project folder. Python 3.10+ and the `claude` CLI are required.

```bash
python tests/run_cases.py 7                 # all 5 cases, with and without the skill → weekly-study-notes-workspace/iteration-7/
python tests/run_cases.py 7 missing-notes-request   # one case only
python tests/run_cases.py --regrade 7       # re-score saved outputs, no model calls
python tests/trigger_eval.py                # 20 activation queries x 2 runs
```

| Case | Checks |
|---|---|
| `geology-natural-activation` | Activates when not named, topic headings, bold key terms, all 10 facts kept, exactly 3 questions at the end |
| `weekly-lecture-revision` | Activates on "organize my weekly lecture notes for revision", dates preserved, typos fixed |
| `unrelated-weather-climate` | Does **not** activate; gives a direct short answer |
| `missing-notes-request` | Asks for the notes and doesn't invent content |
| `many-topics-exact-three` | 7-topic notes that contain their own question still end with exactly 3 review questions and no others |

If you have Claude Code v2.1.269 or later, the same cases also run with `claude plugin eval .claude/skills/weekly-study-notes`.

## Changing when it activates

Activation is controlled by the `description:` line at the top of `SKILL.md`.

- **It triggers when it shouldn't:** add the case to the "Do not use it for…" sentence.
- **It doesn't trigger when it should:** add the phrasing to the "e.g." examples or the list of source types.

Keep the description under 1024 characters. After editing, start a new session, since skills load at startup. Add your phrasing to `tests/trigger_queries.json` and run `python tests/trigger_eval.py` to confirm.

## Troubleshooting

| Problem | Fix |
|---|---|
| Skill not listed | Start Claude Code from the project folder, or copy the skill to `~/.claude/skills/`. Restart the session after adding or editing it. |
| Listed but not used | Name it once ("use weekly-study-notes"), then widen the description as described above. |
| `SKILL.md` errors | The file must start with the `---` frontmatter containing `name: weekly-study-notes` and `description:`. The folder name must match `name`. |
| Test scripts can't find `claude` | Make sure `claude --version` works in the same terminal. |

## Using it outside Claude Code

The Claude apps (claude.ai / desktop) have their own skill upload under account settings. This project hasn't been uploaded or registered there. If you want it there, zip the `weekly-study-notes` folder and upload it yourself.
