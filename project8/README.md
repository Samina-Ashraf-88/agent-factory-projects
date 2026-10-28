# Samina Ashraf: personal website

A one-page personal site that tells a visitor, within seconds, who Samina is (a geologist and geophysicist who builds AI agents), what she can do for them, and how to get in touch.

**Live site:** <https://euphonious-rugelach-d164c3.netlify.app>

It's plain HTML and CSS: no JavaScript, no build step, no framework, no external fonts or scripts. The page weighs about 120 KB in total and works in any modern browser, even with JavaScript turned off.

## Folder structure

```
per-site/
├── index.html              ← all page content (edit text and links here)
├── styles.css              ← all styling; colours and fonts are at the top in :root
├── netlify.toml            ← tells Netlify there's no build step
├── assets/
│   ├── favicon.svg         ← "SA" browser-tab icon
│   └── images/
│       ├── meeting-action-items-board.webp   ← featured project + hero preview
│       ├── openclaw-workspace-skills.webp    ← featured project, 5 skills
│       ├── snake-battle.webp
│       ├── critter-bonk.webp
│       ├── seismic-trace.svg                 ← the decorative wiggle line
│       └── og-image.png                      ← preview shown when the link is shared
├── PROJECT_BRIEF.md        ← audience, message, palette, typography decisions
├── REVIEW.md               ← the two stranger evaluations and what changed
└── README.md
```

## Preview locally

Easiest: double-click `index.html`.

Or run a tiny local server from this folder (closer to how Netlify serves it):

```bash
python -m http.server 8000
# then open http://localhost:8000
```

## Where to edit personal information

All content is in `index.html`, in clearly commented sections (`<!-- HERO -->`, `<!-- FEATURED PROJECT -->`, `<!-- CONTACT -->` and so on). Open it in any text editor and use Find:

| To change… | Search `index.html` for… |
|---|---|
| Headline and intro | `hero-title` |
| Email address | `samina379@gmail.com` (appears 3 times: contact button, contact text, footer) |
| Add a certificate | `CERTIFICATES:` (copy the commented block, one per certificate) |
| LinkedIn link | `linkedin.com` (appears 3 times: hero, contact, footer) |
| GitHub link | `github.com/Samina-Ashraf-88"` |
| Colours or fonts | the `:root` block at the top of `styles.css` |

> **Why no separate `profile.js` config file?** Filling the page from a JavaScript file would make it blank for search engines, link previews and visitors without JavaScript. Keeping the text in `index.html` is simpler and more robust, and the table above lists every spot you're likely to change.

## Replace images and certificates

- **Images:** put the new file in `assets/images/`, then update the matching `<img src="…">` in `index.html`. Also update its `alt` text (what the image shows) and its `width`/`height` (the image's real pixel size, which prevents layout jumps). WebP or JPEG at 800–1600px wide is plenty.
- **Certificates:** create `assets/certificate/`, add the PDF or image there, and use the `CERTIFICATES:` template in `index.html`. Only list a certificate you can show.
- **Add a photo:** you can replace the hero preview, or add an `<img>` above `hero-name`. Keep it under ~150 KB.

## Update project links

Each project card in `index.html` has its links in a `<p class="card-links">`. Change the `href` values there. The featured project's source link is the line containing `Read the Meeting Assistant source`.

## Deploy to Netlify

### Option 1: drag and drop (no account setup beyond sign-in)

1. Sign in at <https://app.netlify.com>.
2. Go to **Sites** (or **Projects**), then **Add new site → Deploy manually**.
3. Drag the whole `per-site` folder onto the drop zone. There's no build command and no publish directory to set.
4. Wait a few seconds for **Published**, then open the `https://<random-name>.netlify.app` link.
5. Optional: rename the site under **Site configuration → Change site name** (for example `samina-ashraf.netlify.app`).

**To update later:** open the site in Netlify, go to **Deploys**, and drag the folder onto the "drag and drop your site output folder here" box. The URL stays the same.

### Option 2: from a Git repository (auto-deploy on every push)

1. Put this folder in a GitHub repository (for example `Samina-Ashraf-88/personal-website`).
2. In Netlify: **Add new site → Import an existing project →** GitHub → pick the repository.
3. Leave **Build command** empty. Set **Publish directory** to `.` (or the folder name, if the site isn't at the repository root). `netlify.toml` already says this.
4. Click **Deploy**. Every `git push` now redeploys automatically.

### Option 3: command line

```bash
npx netlify-cli login
npx netlify-cli deploy --dir . --prod
```

### After the first deploy: fix the sharing preview

Link previews on LinkedIn, WhatsApp and similar apps need **full** URLs. In `index.html`, change:

```html
<meta property="og:image" content="assets/images/og-image.png">
<meta property="og:url" content="/">
```

to your real address, for example:

```html
<meta property="og:image" content="https://samina-ashraf.netlify.app/assets/images/og-image.png">
<meta property="og:url" content="https://samina-ashraf.netlify.app/">
```

Then redeploy, and check the preview at <https://www.linkedin.com/post-inspector/>.

## Troubleshooting

| Problem | Fix |
|---|---|
| Page shows with no styling | `styles.css` must sit next to `index.html`. Upload the whole folder, not just `index.html`. |
| An image is missing | File names are case-sensitive on Netlify (`Board.webp` ≠ `board.webp`). Check the `src` matches exactly. |
| "Page not found" on Netlify | `index.html` must be at the top level of what you uploaded, not inside a subfolder. |
| Old version still showing | Hard-refresh (Ctrl + F5), or check the **Deploys** tab to confirm the newest deploy is published. |
| Link preview has no image | Do the "fix the sharing preview" step above. LinkedIn caches previews, so re-inspect the URL in Post Inspector. |
| A "Powered by Netlify" badge appears | That's normal on the free tier. The page layout isn't affected. |

## What was tested

See `REVIEW.md` for the stranger evaluations. Technical checks (headless Chrome, at 320, 375, 768, 1024 and 1440px):

- no horizontal scrolling and no element past the viewport edge
- all images load and all have alt text
- every `#section` link has a target, and header links land on their sections
- no console errors, no failed requests, and zero requests to other sites
- the skip link appears on the first Tab press; focus rings are visible
- the page renders fully with JavaScript disabled; reduced-motion turns off smooth scrolling
- every external link returns HTTP 200 (LinkedIn blocks automated checks, so test that link by hand)
- text colour contrast meets WCAG AA throughout (most pairs meet AAA)
