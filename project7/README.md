# 🐹 Critter Bonk

A cozy, fast-paced whack-a-critter game for the browser. Cute animals pop out of a 3×3 garden: **bonk them before they duck back down**. Every bonk makes them faster.

The whole game is one self-contained `index.html` file: no build step, no dependencies, no backend, no external assets. It runs on desktop, tablet, and mobile.

---

## Features

- **3×3 garden board** with layered holes (shadow → dirt rim → dark opening → critter → front lip). Critters climb *out of* the hole and are clipped by its front edge.
- **Three themes**, chosen on the start screen and remembered:
  - 🌙 **Twilight Garden** (default): midnight sky, twinkling stars, fireflies, emerald grass, gold accents. Critters: 🐹 🐻 🐸 🐵 🐰 🦊
  - 👻 **Monster Mash**: purple night, slime-green glow. Critters: 👻 👾 🧟 🎃 🦇 👹
  - 🌞 **Sunny Farm**: blue sky, clouds, sunshine. Critters: 🐮 🐷 🐔 🐑 🐴 🐶
- **30-second rounds** with three difficulties (Easy / Normal / Hard).
- **Score-driven speed tiers**: Easy → ⚡ Fast → 🔥 Frenzy, each announced with a banner and sound.
- **Decoys** from the Fast tier onward (🦔 / 💣 / 🐝 depending on theme), marked with a pulsing red rim. Don't bonk them!
- **Juicy hit feedback**: particle burst, shockwave ring, mallet swing, floating `+1`, hit flash, dizzy stars, screen shake, and a synthesized "bonk".
- **Streaks**: a 🔥 streak counter in the HUD plus a celebration every 5 hits in a row.
- **HUD**: score, best, time, speed tier, "next tier at…" hint, streak, color-coded progress bar, pause and sound buttons.
- **Final-5-seconds drama**: red pulsing timer, ticking sound, and a glowing red board edge.
- **Results screen**: animated score count-up, a New High Score badge (only when genuinely earned), hits, accuracy, hits/min, best streak, escaped critters, top speed reached, and confetti.
- **Accessibility**: full keyboard play, visible focus rings, ARIA labels, a screen-reader live region, reduced-motion support, and touch targets of at least 84px even on a 320px-wide phone.
- **Robustness**: one game loop driven by real elapsed time, auto-pause when the tab is hidden or the window loses focus, error-safe audio and storage, and no leaked timers or DOM nodes across restarts.

## Run it locally

Double-click **`index.html`**, or open it in any modern browser (Chrome, Edge, Firefox, Safari). That's it.

Optionally, serve it over HTTP instead (useful for testing on a phone on the same Wi-Fi):

```bash
npx serve .            # or: python -m http.server 8000
```

## Controls

| Action | Mouse / touch | Keyboard |
|---|---|---|
| Bonk a hole | Click / tap the critter | <kbd>1</kbd>–<kbd>9</kbd> (top-left = 1, reading order); also <kbd>Enter</kbd> on a focused hole |
| Pause / resume | ⏸️ button | <kbd>Space</kbd>, <kbd>P</kbd>, <kbd>Esc</kbd> (Esc pauses only) |
| Mute / unmute | 🔊 button | <kbd>M</kbd> |
| Start / play again | Buttons | <kbd>Enter</kbd> |

Holes show their number key on devices with a mouse. Holding a key down counts as one swing (auto-repeat is ignored).

## Scoring rules

- Each successful bonk = **+1 point**. Score updates instantly.
- A critter can be scored **once**: it locks on the first hit, so rapid clicks or overlapping touch, mouse, and keyboard events can never double-score.
- **Misses**: swinging at an empty hole, at a critter that has already ducked away ("Too slow!"), or at a decoy ("Ouch!"). Misses never cost points, but they reset your streak and lower your accuracy.
- **Escaped**: real critters that ducked away un-bonked. Avoided decoys don't count.
- **Accuracy** = hits ÷ (hits + misses). **Hits/min** uses the actual elapsed round time. Both show 0 when there's nothing to divide (no NaN).
- **Best score** is kept separately for each difficulty.

## Difficulty progression

Speed is driven **only by your score** (successful hits), never by elapsed time. Thresholds are documented in code (`DIFFICULTIES` / `TIERS` in `index.html`):

| Difficulty | Easy tier | ⚡ Fast at | 🔥 Frenzy at | Speed multiplier |
|---|---|---|---|---|
| Easy | 0–9 | 10 | 22 | 1.00 (first critter visible **2.5 s**) |
| Normal | 0–7 | 8 | 18 | 0.86 |
| Hard | 0–5 | 6 | 14 | 0.74 |

| Tier | Visible time* | Gap between spawns* | Max critters at once | Decoy chance |
|---|---|---|---|---|
| Easy | 2.5 s → 1.9 s | 0.95 s → 0.76 s | 1 | none |
| Fast | 1.65 s → 1.25 s | 0.70 s → 0.52 s | 2 | 10% → 14% |
| Frenzy | 1.15 s → 0.85 s | 0.46 s → 0.32 s | 3 | 15% → 20% |

\* Values shrink gradually as your score climbs through each tier, then are multiplied by the difficulty's speed multiplier. Frenzy keeps tightening for 16 more hits, then plateaus. A critter is never visible for less than 0.6 s. Each new tier is announced with a banner and gets a short breather before the faster pace starts. Critters wiggle nervously in their last 0.3 s as a fair warning.

## Audio

All sounds are generated live with the **Web Audio API** (no audio files): bonk (pitch rises with your streak), miss thud, decoy "ouch", start jingle, tier-up sweep, 5-in-a-row chime, 10-second warning, final-5-second ticks, game-over tune, and a new-record fanfare.

- No audio is created or played until you interact with the page (browser autoplay rules).
- The sound toggle (start screen, HUD, or <kbd>M</kbd>) is remembered.
- If Web Audio is unavailable or fails, the game continues silently.

## Best-score storage

Best scores (per difficulty) and preferences (sound, difficulty, theme) are saved in **localStorage** under the key `critterBonk:v1`. Restarting or playing again never clears them. If storage is blocked (some private modes), the game still works and just won't remember between visits. To reset, clear site data or run `localStorage.removeItem('critterBonk:v1')` in the browser console.

## Testing

### Automated (headless Chrome)

```bash
cd tests
npm install         # installs puppeteer-core only (uses your installed Chrome/Edge)
npm test            # ~75 s; set CHROME_PATH if Chrome isn't found

# test the published site instead of the local file:
GAME_URL=https://imaginative-frangipane-bbb42f.netlify.app/ npm test
```

70 checks, covering:
- **Start and first critter**: the start screen, and the first critter appearing *and* being bonkable inside the Start click.
- **Input**: exactly +1 under 9 overlapping inputs, real mouse clicks, real touch taps, keys 1–9 mapping to holes 1–9, and key auto-repeat.
- **Difficulty**: tier switches at the exact scores, visibility never increasing, simultaneous-critter growth, and decoy rules.
- **Timer and HUD**: a 30-second wall-clock round and progress-bar colors at 10 s / 5 s.
- **Pause**: freezes the timer, spawns and expiry (3-second check); resumes at the same remaining time; auto-pause on blur.
- **Sound and storage**: sound toggle persistence, audio gated behind the first interaction, best score saved and surviving a reload, and the New High Score badge appearing only when earned.
- **Results and robustness**: results statistics, Play Again, Return to Menu, a single game loop and no DOM growth after 22 restarts, and reduced motion.
- **Layout**: no overlap or sideways scroll, and Start visible without scrolling, at 320×568, 375×667, 412×915, 667×375 landscape, 768×1024 and 1024×768.

Screenshots are written to `tests/screenshots/`.

### Manual checklist (real devices)

- [ ] Sounds are audible and pleasant; mute works (automation can't listen).
- [ ] On a real phone: taps feel instant, the page never scrolls or zooms while playing, and portrait and landscape both fit.
- [ ] iOS Safari: sound starts after tapping Start, even with the ring/silent switch off.
- [ ] Switching apps or tabs mid-game pauses it.
- [ ] Each theme looks right on your device's emoji font.

## Deploy to Netlify (free, no build)

1. Create or sign in to an account at <https://www.netlify.com/>.
2. Open the Netlify dashboard (**Sites** / **Projects**).
3. Choose the manual deploy option: **Add new site → Deploy manually** (the drag-and-drop area, also reachable at <https://app.netlify.com/drop>).
4. Drag the project folder containing `index.html` onto the drop zone. The `tests/` folder is harmless but optional; you can upload a folder with just `index.html`. There's no build command or publish directory to configure.
5. Wait for "Published" (usually a few seconds).
6. Open the generated `https://<random-name>.netlify.app` URL (you can rename it under **Site configuration → Change site name**).
7. Test the game on desktop and on a phone.

**CLI alternative** (needs a one-time browser login):

```bash
npx netlify-cli login
npx netlify-cli deploy --dir . --prod
```

**Live site:** <https://imaginative-frangipane-bbb42f.netlify.app>

**Netlify badge:** free-tier sites get a small "Powered by Netlify" badge injected in the bottom-right corner. The layout keeps every hole and button clear of that corner (in phone landscape the HUD sits on the right, vertically centered; menus have extra bottom padding), so it never blocks play.

### Updating the published version

- **Drag-and-drop sites**: open the site in Netlify → **Deploys** tab → drag the updated folder onto the "Need to update your site? Drag and drop your site output folder here" box. The URL stays the same.
- **CLI**: run `npx netlify-cli deploy --dir . --prod` again from this folder.

Best scores live in each player's browser, so redeploying doesn't reset them.

## Known limitations

- Emoji artwork depends on the device's emoji font, so critters look slightly different on Windows, macOS/iOS, and Android. Very old systems may lack 🦔 (hedgehog, added in 2017).
- High scores are local to one browser on one device; there is no online leaderboard (by design: no backend).
- Difficulty tuning was validated with automated play (bots with 250 ms reaction times) and timing measurements, not with a panel of human testers. Adjust `TIERS` in `index.html` if it feels too easy or hard for your players.
- Sound design was verified to run without errors, but its feel can only be judged by ear on real speakers.
- Only one game mode (30 seconds) is included.

## Project structure

```
critter-bonk/
├── index.html             ← the entire game (HTML + CSS + JS, ~80 KB)
├── README.md
├── .gitignore
└── tests/                 ← optional dev tooling, not needed to play or deploy
    ├── browser-test.js
    └── package.json
```
