# Snake Battle

**Play it live:** https://serene-gingersnap-5a0371.netlify.app

An arcade snake survival game for the browser. You face up to seven AI snakes. You grow by eating fruit, and you can trick rivals into crashing into your body. **When any snake dies, its whole body bursts into edible remains**, so every kill turns into a race to the feast. When the battle drags on, sudden death starts and the arena walls close in.

The whole game is one self-contained `index.html` file with HTML5 Canvas, CSS and vanilla JavaScript. It has no dependencies, no build step, no backend and no external assets.

## Features

- **Start screen**: snake colour picker, fruit colour picker with a live animated preview, 1/3/5/7 AI opponents, four speeds (Chill, Normal, Fast, Insane), three AI difficulties (Easy, Medium, Hard), a sound toggle, and the rules and controls.
- **Dead snakes become food**: each body segment of a dead snake turns into a diamond-shaped "remains" piece in that snake's colour. Remains look clearly different from round fruit, and each piece is worth +5 points and +1 length. Each death is processed exactly once.
- **AI rivals that think**:
  - All difficulties: a shared BFS distance field to food, flood-fill dead-end detection, and avoidance of head-ons with bigger snakes.
  - Medium also checks whether it can reach its own tail.
  - Hard also uses one-step lookahead of rival heads, and when it is clearly longer it hunts the player by cutting in front of them.
- **Fair, simultaneous collisions**: all snakes move at the same instant. Walls, self, bodies, same-cell head-ons, head swaps and simultaneous deaths are all handled.
- **Sudden death**: after about 650 ticks (roughly a minute at Normal speed), or once only two snakes remain, the walls close in one ring at a time. A flashing ring warns where the wall will land next. This ends stalemates and makes every match build to a climax.
- **Polish**: smooth interpolated movement, rounded and tapered snakes with eyes that face the direction of travel, glowing fruit, particles, screen shake, a kill feed, floating score text, a wall-proximity warning, and a live leaderboard sorted by length.
- **Game states**: countdown, playing, paused (full freeze), game over (with an option to watch the surviving AIs fight on), victory, instant restart, and return to the menu.
- **Mobile**: an on-screen D-pad with large targets and a pause button in its centre, swipe steering, portrait and landscape layouts, a responsive canvas, and no accidental page scrolling or zooming.
- **Persistence**: the best score, your settings and the "first battle" tutorial flag are saved in `localStorage`.
- **Audio and accessibility**:
  - Sound effects are generated with WebAudio. Audio only starts after you interact with the page, and you can mute it.
  - Every menu control is a real form control, so it works with the keyboard, and focus outlines are visible.
  - The game respects reduced-motion settings and uses high-contrast text.

## Run locally

Open `index.html` in any modern browser by double-clicking it. Nothing else is needed.

If you prefer to use a local server:

```bash
npx serve .        # or: python -m http.server 8000
```

## Controls

| Action  | Keyboard                         | Touch                                   |
|---------|----------------------------------|-----------------------------------------|
| Steer   | Arrow keys or `W` `A` `S` `D`    | Swipe on the arena, or use the D-pad    |
| Pause   | `P`, `Space` or `Esc`            | Pause button (HUD or D-pad centre)      |
| Restart | `R`                              | Restart button                          |
| Sound   | `M`                              | Speaker button                          |

You can buffer two quick turns, such as up then right, within a single move. An instant 180° reversal into your own neck is always ignored.

## Rules

1. **Fruit** (round, in the fruit colour you picked) gives +10 points and +1 length. More fruit appears as the match goes on.
2. A snake dies when its head hits a **wall**, **itself**, or **another snake's body**. Moving into the cell a tail is leaving is allowed.
3. **Takedown**: if a rival crashes into *your* body, you get +50 points.
4. **Head-on collisions** (two heads entering the same cell, or two adjacent heads swapping places): the **longer snake survives**. If both are the same length, both die and nobody gets credit.
5. All moves resolve **simultaneously**. A snake that hits another snake dies even if that other snake also dies on the same tick.
6. **Remains**: a dead snake's body turns into diamond-shaped remains. Each piece is +5 points and +1 length for whoever reaches it first.
7. **Sudden death**: after about a minute, or once only two snakes remain, the walls close in one ring at a time, with a flashing warning first. A head caught by the closing wall is crushed. Body segments caught by it are sliced off.
8. Be the **last snake alive** to win and earn a +100 bonus. If you die, you can watch the rest of the battle play out.

## Customising settings

You change everything on the start screen, and your choices are remembered:

- Your snake colour (8 presets). AI colours are picked automatically so they look different from yours.
- Fruit colour (8 presets).
- Number of opponents: 1, 3, 5 or 7. The arena gets bigger when there are more snakes.
- Speed: Chill 145 ms, Normal 108 ms, Fast 80 ms or Insane 56 ms per move.
- AI difficulty: Easy, Medium or Hard.

The arena's grid shape is chosen when a battle starts, based on the shape of the window (landscape or portrait). Resizing during a battle rescales the arena but keeps the same grid.

## Deploy to Netlify (manual upload, no build step)

1. Open https://www.netlify.com/ and sign in, or create an account.
2. Open the Netlify dashboard (**Sites** / **Projects**).
3. Choose the manual deploy option. In the current interface it is **Add new site → Deploy manually** (sometimes shown as "Deploy manually" or "drag and drop your site output folder").
4. Drag the project folder that contains `index.html` onto the upload area. You can also zip the folder and upload the zip. Netlify serves `index.html` as the home page.
5. Wait for the deploy to finish. It usually takes a few seconds.
6. Open the public `https://<random-name>.netlify.app` URL that Netlify gives you. You can rename it under **Site configuration → Change site name**.
7. Test the live game on a desktop browser and on a phone, in both portrait and landscape.
8. **To update the game**, open the same site in Netlify, go to **Deploys**, and drag the updated folder onto the "Need to update your site? Drag and drop your site output folder here" area. The URL stays the same.

No build command, publish directory, environment variables or redirects are needed.

### Alternative: deploy from Git

1. Put this folder in a Git repository and push it to GitHub, GitLab or Bitbucket.
2. In Netlify choose **Add new site → Import an existing project**, then connect your Git provider and pick the repository.
3. Leave the **build command empty** and set the **publish directory** to the folder that contains `index.html` (`.` if it is at the repository root).
4. Deploy. Every `git push` to the chosen branch will now redeploy the site automatically.

You can also deploy with the Netlify CLI: run `npx netlify-cli deploy --prod --dir .` after `netlify login`.

## Project files

```
Snake-battle/
├── index.html   # the entire game (HTML + CSS + JS, self-contained)
├── README.md
└── .gitignore
```

## Known limitations

- There is no online multiplayer. All opponents are local AI.
- The grid shape is fixed when a battle starts. If you rotate a phone mid-battle, the arena is rescaled to fit, which can leave it smaller than it would be after a restart.
- Swipe steering uses Pointer Events. Very old mobile browsers without Pointer Events can still use the D-pad.
- Sound depends on WebAudio. Browsers that block or lack it simply stay silent.
- On Netlify's free tier, Netlify adds a "Powered by Netlify" badge in the bottom-right corner. The game detects it and moves the touch D-pad up so the badge doesn't cover the Down button. This costs a little arena height on phones.
- The page exposes a small `window.SnakeBattle` object that automated tests use. It has no effect on normal play.
