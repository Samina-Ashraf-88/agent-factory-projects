/*
 * Critter Bonk — automated browser test suite (headless Chrome via puppeteer-core).
 *
 *   cd tests && npm install && npm test
 *
 * Set CHROME_PATH if Chrome/Edge is not in a default location.
 * Set GAME_URL to test a deployed copy instead of the local index.html.
 * Takes ~75 seconds (two full 30-second rounds run in parallel with the quick checks).
 */
const path = require('path');
const fs = require('fs');
const { pathToFileURL } = require('url');
const puppeteer = require('puppeteer-core');

// Test the local file by default, or a deployed copy: GAME_URL=https://your-site.netlify.app npm test
const URL = process.env.GAME_URL || pathToFileURL(path.resolve(__dirname, '..', 'index.html')).href;
const CHROME = process.env.CHROME_PATH || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
].find((p) => fs.existsSync(p));
const SHOTS = path.resolve(__dirname, 'screenshots');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const results = [];
const errors = [];
const check = (name, ok, info = '') => results.push({ name, ok: !!ok, info: String(info) });

async function newPage(b, vp = { width: 1280, height: 800 }) {
  const ctx = await b.createBrowserContext();          // isolated localStorage per game
  const p = await ctx.newPage();
  p.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warn') errors.push(m.text()); });
  p.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  await p.setViewport(vp);
  await p.goto(URL);
  return p;
}
const snap = (p) => p.evaluate(() => CritterBonk.snapshot());
const waitFor = (p, fn, timeout = 8000) => p.waitForFunction(fn, { timeout, polling: 20 });

// Bot: bonks every hittable critter after a human-like reaction delay and logs the progression.
const startBot = (p, reaction) => p.evaluate((reaction) => {
  window.__log = [];
  const seen = new Map();
  window.__decoySeenAt = [];
  window.__decoyHit = null;
  window.__bot = setInterval(() => {
    const s = CritterBonk.snapshot();
    if (s.phase !== 'playing') return;
    if (s.up.includes('decoy')) window.__decoySeenAt.push(s.score);
    // Deliberately bonk the first decoy once (twice in a row, to check it can't double-count).
    const d = s.up.indexOf('decoy');
    if (d >= 0 && !window.__decoyHit && s.streak >= 2) {
      const h = document.querySelectorAll('.hole')[d];
      const r = h.getBoundingClientRect();
      const o = { bubbles: true, cancelable: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 };
      h.dispatchEvent(new PointerEvent('pointerdown', o));
      h.dispatchEvent(new PointerEvent('pointerdown', o));
      const a = CritterBonk.snapshot();
      window.__decoyHit = { dScore: a.score - s.score, dWhiffs: a.whiffs - s.whiffs, streakBefore: s.streak, streakAfter: a.streak, decoysHit: a.decoysHit };
    }
    s.up.forEach((st, i) => {
      if (st !== 'up') { seen.delete(i); return; }
      const now = performance.now();
      if (!seen.has(i)) seen.set(i, now);
      if (now - seen.get(i) < reaction) return;
      const h = document.querySelectorAll('.hole')[i];
      const r = h.getBoundingClientRect();
      h.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2, pointerType: 'touch' }));
      seen.delete(i);
      const a = CritterBonk.snapshot();
      window.__log.push({ score: a.score, tier: a.tier, visible: Math.round(a.params.visible), maxActive: a.params.maxActive, t: Math.round(a.time) });
    });
  }, 30);
}, reaction);

(async () => {
  if (!CHROME) throw new Error('Chrome not found. Set CHROME_PATH.');
  fs.mkdirSync(SHOTS, { recursive: true });
  const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new' });

  /* ---------------- A: full bot game on Normal ---------------- */
  const gameA = (async () => {
    const p = await newPage(b);
    await p.click('#btn-start');
    const t0 = Date.now();
    await startBot(p, 250);
    const levels = [];
    const sampler = setInterval(async () => {
      try { levels.push(await p.evaluate(() => ({ r: CritterBonk.snapshot().remaining, l: document.querySelector('#progress').dataset.level, phase: CritterBonk.snapshot().phase }))); } catch (e) { /* page busy */ }
    }, 150);
    await waitFor(p, () => CritterBonk.snapshot().phase === 'results', 40000);
    clearInterval(sampler);
    const wall = Date.now() - t0;
    const s = await snap(p);
    const log = await p.evaluate(() => window.__log);

    const firstFast = log.find((e) => e.tier === 'fast');
    const firstFrenzy = log.find((e) => e.tier === 'frenzy');
    check('Difficulty: Easy→Fast exactly at score 8 (Normal)', firstFast && firstFast.score === 8 && log.filter((e) => e.score < 8).every((e) => e.tier === 'easy'), JSON.stringify(firstFast));
    check('Difficulty: Fast→Frenzy exactly at score 18 (Normal)', firstFrenzy && firstFrenzy.score === 18, JSON.stringify(firstFrenzy));
    const decoy = await p.evaluate(() => ({ seen: window.__decoySeenAt, hit: window.__decoyHit }));
    check('Decoys never appear in the Easy tier (score < 8)', decoy.seen.length > 0 && Math.min(...decoy.seen) >= 8, `first seen at score ${Math.min(...decoy.seen)}`);
    check('Bonking a decoy: no points, exactly one miss, streak reset, no double count', decoy.hit && decoy.hit.dScore === 0 && decoy.hit.dWhiffs === 1 && decoy.hit.streakAfter === 0 && decoy.hit.decoysHit === 1, JSON.stringify(decoy.hit));
    const vis = log.map((e) => e.visible);
    check('Difficulty: visibility never increases as score rises', vis.every((v, i) => i === 0 || v <= vis[i - 1]), `${vis[0]}ms → ${vis[vis.length - 1]}ms`);
    const actives = [...new Set(log.map((e) => e.maxActive))];
    check('Difficulty: simultaneous critters grow 1→2→3', JSON.stringify(actives) === '[1,2,3]', actives.join(','));
    check('Timer: round ends at ~30s wall clock (+1.05s results delay)', wall > 30500 && wall < 33500, wall + 'ms');
    const bad = levels.filter((x) => x.phase === 'playing' && !((x.r > 10000 && x.l === 'ok') || (x.r <= 10000 && x.r > 5000 && x.l === 'warn') || (x.r <= 5000 && x.l === 'danger')));
    check('Progress bar: green >10s, yellow 5–10s, red ≤5s', levels.length > 50 && bad.length <= 2, `${levels.length} samples, ${bad.length} mismatches`);
    check('Progress bar: all three colours observed', ['ok', 'warn', 'danger'].every((l) => levels.some((x) => x.l === l)));

    const dom = await p.evaluate(() => ({
      hits: document.querySelector('#st-hits').textContent, acc: document.querySelector('#st-acc').textContent,
      hpm: document.querySelector('#st-hpm').textContent, badge: !document.querySelector('#over-new').hidden, over: !document.querySelector('#screen-over').hidden,
    }));
    await sleep(1200);
    await p.screenshot({ path: path.join(SHOTS, 'results-desktop.png') });
    const finalShown = await p.evaluate(() => document.querySelector('#over-score').textContent);
    const expAcc = Math.round((s.hits / Math.max(1, s.hits + s.whiffs)) * 100) + '%';
    const expHpm = String(Math.round(s.hits / (Math.min(s.time, 30000) / 60000)));
    check('Results: shown, final score = hits', dom.over && finalShown === String(s.score) && dom.hits === String(s.hits) && s.hits === s.score, `score ${s.score}`);
    check('Results: accuracy and hits/min correct', dom.acc === expAcc && dom.hpm === expHpm, `${dom.acc} / ${dom.hpm} hpm`);
    check('Results: New High Score badge on first record', dom.badge && s.newBest && s.score > 0);
    check('Results: confetti renders behind the results panel', await p.evaluate(() => {
      const cv = document.querySelector('#confetti'), panel = document.querySelector('#screen-over .panel');
      return cv.parentElement.id === 'screen-over' && Number(getComputedStyle(panel).zIndex) > Number(getComputedStyle(cv).zIndex);
    }));
    check('Bot reaches Frenzy with a 250ms reaction time', s.score >= 25, 'score ' + s.score);
    const stored = await p.evaluate(() => JSON.parse(localStorage.getItem('critterBonk:v1')).best.normal);
    check('Best score saved to localStorage', stored === s.score, stored);
    await p.reload();
    await sleep(300);
    const shownBest = await p.evaluate(() => document.querySelector('#start-best').textContent);
    check('Best score persists after page reload', shownBest === String(s.score), shownBest);

    await p.click('#btn-start');                  // idle game: never beats the record
    await waitFor(p, () => CritterBonk.snapshot().phase === 'results', 40000);
    const s2 = await snap(p);
    const badge2 = await p.evaluate(() => !document.querySelector('#over-new').hidden);
    check('New High Score NOT shown when the record is not beaten', !badge2 && !s2.newBest && s2.best === s.score, `score ${s2.score}, best ${s2.best}`);
    check('Zero-hit game: accuracy 0%, hits/min 0 (no NaN)', await p.evaluate(() => document.querySelector('#st-acc').textContent === '0%' && document.querySelector('#st-hpm').textContent === '0'));
    check('Zero-hit game: escapes counted, tier stays Easy (score-driven, not time-driven)', s2.escaped > 5 && s2.tier === 'easy', `escaped ${s2.escaped}`);
    check('Effects cleaned up after game', (await snap(p)).fxNodes === 0);

    await p.click('#btn-again');
    const s3 = await snap(p);
    check('Play Again: fresh state, best kept, critter up', s3.phase === 'playing' && s3.score === 0 && s3.time < 100 && s3.best === s.score && s3.up.some(Boolean));
    await p.keyboard.press('Space');
    await sleep(100);
    await p.click('#btn-quit');
    await sleep(100);
    const menu = await p.evaluate(() => ({ s: CritterBonk.snapshot(), start: !document.querySelector('#screen-start').hidden }));
    check('Return to Menu: menu shown, loop stopped, board cleared', menu.s.phase === 'menu' && menu.start && !menu.s.loopRunning && !menu.s.up.some(Boolean));
    await p.close();
  })();

  /* ---------------- B: difficulty presets ---------------- */
  const gameB = (async () => {
    const p = await newPage(b);
    await p.click('input[value="easy"] + span');
    await p.click('#btn-start');
    const s = await snap(p);
    check('Easy: initial visibility = 2.5s', Math.abs(s.params.visible - 2500) < 1, s.params.visible);
    await p.keyboard.press('Space');
    await p.click('#btn-quit');
    await p.click('input[value="hard"] + span');
    await p.click('#btn-start');
    const h = await snap(p);
    check('Hard: starts faster than Easy', h.params.visible < 2000 && h.difficulty === 'hard', h.params.visible);
    await p.close();
  })();

  /* ---------------- C: audio gating + reduced motion ---------------- */
  const gameC = (async () => {
    const ctx = await b.createBrowserContext();
    const p = await ctx.newPage();
    p.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
    await p.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
    await p.evaluateOnNewDocument(() => {      // count AudioContext creations
      window.__acCount = 0;
      const AC = window.AudioContext;
      window.AudioContext = class extends AC { constructor(...a) { super(...a); window.__acCount++; } };
    });
    await p.setViewport({ width: 800, height: 800 });
    await p.goto(URL);
    await sleep(500);
    check('Audio: no AudioContext before the first user interaction', (await p.evaluate(() => window.__acCount)) === 0);
    await p.click('#btn-start');
    check('Audio: AudioContext created on Start (user gesture)', (await p.evaluate(() => window.__acCount)) === 1);
    await waitFor(p, () => CritterBonk.snapshot().up.includes('up'));
    const n = await p.evaluate(() => {
      const i = CritterBonk.snapshot().up.indexOf('up');
      const h = document.querySelectorAll('.hole')[i];
      const r = h.getBoundingClientRect();
      h.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 }));
      return { particles: document.querySelectorAll('#fx .particle').length, score: CritterBonk.snapshot().score };
    });
    check('Reduced motion: game plays with a lighter particle burst', n.score === 1 && n.particles > 0 && n.particles <= 6, JSON.stringify(n));
    await p.close();
  })();

  /* ---------------- Quick interactive checks ---------------- */
  const p = await newPage(b);
  const init = await p.evaluate(() => ({ start: !document.querySelector('#screen-start').hidden, holes: document.querySelectorAll('.hole').length, phase: CritterBonk.snapshot().phase }));
  check('Start screen loads with 9 holes', init.start && init.holes === 9 && init.phase === 'menu');
  await p.screenshot({ path: path.join(SHOTS, 'start-desktop.png') });

  const first = await p.evaluate(() => {
    document.querySelector('#btn-start').click();
    const s = CritterBonk.snapshot();
    const i = s.up.findIndex(Boolean);
    const h = document.querySelectorAll('.hole')[i];
    const r = h.getBoundingClientRect();
    h.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 }));
    return { count: s.up.filter(Boolean).length, time: s.time, score: CritterBonk.snapshot().score };
  });
  check('First critter appears synchronously in the Start click', first.count === 1 && first.time === 0, JSON.stringify(first));
  check('First critter is bonkable immediately', first.score === 1);

  await waitFor(p, () => CritterBonk.snapshot().up.includes('up'));
  const dbl = await p.evaluate(() => {
    const before = CritterBonk.snapshot();
    const i = before.up.indexOf('up');
    const h = document.querySelectorAll('.hole')[i];
    const r = h.getBoundingClientRect();
    const o = { bubbles: true, cancelable: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 };
    for (let k = 0; k < 6; k++) h.dispatchEvent(new PointerEvent('pointerdown', o));
    h.dispatchEvent(new MouseEvent('click', { ...o, detail: 1 }));
    h.click();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: String(i + 1), bubbles: true }));
    const after = CritterBonk.snapshot();
    return { d: after.score - before.score, w: after.whiffs - before.whiffs };
  });
  check('9 overlapping inputs on one critter score exactly +1, no misses', dbl.d === 1 && dbl.w === 0, JSON.stringify(dbl));
  const fxKinds = await p.evaluate(() => ['.particle', '.ring', '.mallet', '.pop'].map((s) => document.querySelectorAll('#fx ' + s).length));
  check('Hit spawns particles, shockwave ring, mallet swing and one "+1"', fxKinds[0] >= 6 && fxKinds[1] >= 1 && fxKinds[2] >= 1 && fxKinds[3] >= 1, fxKinds.join(','));

  await waitFor(p, () => CritterBonk.snapshot().up.includes('up'));
  {
    const s = await snap(p);
    const bb = await (await p.$$('.hole'))[s.up.indexOf('up')].boundingBox();
    await p.mouse.click(bb.x + bb.width / 2, bb.y + bb.height * 0.4);
    check('Real mouse click on a critter scores +1', (await snap(p)).score === s.score + 1);
  }
  await waitFor(p, () => CritterBonk.snapshot().up.includes('up'));
  await p.screenshot({ path: path.join(SHOTS, 'play-desktop.png') });

  const keyMap = [];
  for (let k = 1; k <= 9; k++) {
    await p.evaluate(() => document.querySelectorAll('.hole-glow').forEach((g) => g.classList.remove('flash', 'whiff')));
    const before = await snap(p);
    await p.keyboard.press(String(k));
    const lit = await p.evaluate(() => [...document.querySelectorAll('.hole-glow')].map((g, i) => (g.classList.contains('flash') || g.classList.contains('whiff') ? i : -1)).filter((i) => i >= 0));
    const after = await snap(p);
    keyMap.push(lit.length === 1 && lit[0] === k - 1 && after.score - before.score + (after.whiffs - before.whiffs) === 1);
  }
  check('Number keys 1–9 each target the matching hole', keyMap.every(Boolean), keyMap.map((x) => (x ? 'ok' : 'X')).join(' '));

  await waitFor(p, () => CritterBonk.snapshot().up.includes('up'));
  {
    const s = await snap(p);
    await p.keyboard.press(String(s.up.indexOf('up') + 1));
    check('Key press on an up critter scores +1', (await snap(p)).score === s.score + 1);
  }
  {
    const s = await snap(p);
    const key = String(s.up.indexOf(null) + 1);      // an empty hole, so the swing is a clean miss
    await p.keyboard.down(key); await p.keyboard.down(key); await p.keyboard.down(key); await p.keyboard.up(key);
    const a = await snap(p);
    check('Held key (auto-repeat) counts as one swing', a.score - s.score + (a.whiffs - s.whiffs) === 1);
  }

  await waitFor(p, () => CritterBonk.snapshot().up.includes('up'));
  await p.keyboard.press('Space');
  const pa = await p.evaluate(() => ({ s: CritterBonk.snapshot(), overlay: !document.querySelector('#screen-pause').hidden, tf: [...document.querySelectorAll('.critter')].map((c) => c.style.transform) }));
  await sleep(3000);
  const pb = await p.evaluate(() => ({ s: CritterBonk.snapshot(), tf: [...document.querySelectorAll('.critter')].map((c) => c.style.transform) }));
  check('Pause: overlay shown and loop stopped', pa.overlay && pa.s.phase === 'paused' && !pb.s.loopRunning);
  check('Pause: timer frozen for 3 seconds', pa.s.time === pb.s.time, `${pa.s.time.toFixed(0)} → ${pb.s.time.toFixed(0)}`);
  check('Pause: critters neither expire nor move', JSON.stringify(pa.s.up) === JSON.stringify(pb.s.up) && JSON.stringify(pa.tf) === JSON.stringify(pb.tf) && pa.s.escaped === pb.s.escaped);
  {
    const s = await snap(p);
    await p.keyboard.press('3');
    const a = await snap(p);
    check('Pause: number keys ignored while paused', a.score === s.score && a.whiffs === s.whiffs);
  }
  await p.keyboard.press('Space');
  await sleep(500);
  const pc = await snap(p);
  check('Resume: continues from the paused remaining time', pc.phase === 'playing' && pc.time - pb.s.time > 350 && pc.time - pb.s.time < 700, `${pb.s.time.toFixed(0)} → ${pc.time.toFixed(0)}`);

  await p.click('#btn-pause');
  check('HUD pause button pauses', (await snap(p)).phase === 'paused');
  await p.click('#btn-resume');
  check('Resume button resumes', (await snap(p)).phase === 'playing');
  await p.evaluate(() => window.dispatchEvent(new Event('blur')));
  check('Window blur auto-pauses', (await snap(p)).phase === 'paused');
  await p.keyboard.press('Enter');
  check('Enter resumes from pause', (await snap(p)).phase === 'playing');

  const sndBefore = (await snap(p)).sound;
  await p.click('#btn-sound-hud');
  const snd = await p.evaluate(() => ({ on: CritterBonk.snapshot().sound, stored: JSON.parse(localStorage.getItem('critterBonk:v1')).sound, aria: document.querySelector('#btn-sound-hud').getAttribute('aria-pressed') }));
  check('Sound toggle disables sound and persists the preference', sndBefore === true && !snd.on && snd.stored === false && snd.aria === 'false');
  await p.keyboard.press('m');
  check('M key re-enables sound', (await snap(p)).sound === true);

  for (let k = 0; k < 12; k++) { await p.keyboard.press('Space'); await p.click('#btn-restart'); }
  const f0 = await snap(p);
  await sleep(1000);
  const f1 = await snap(p);
  check('After 12 restarts: exactly one game loop (frame count ≈ display rate)', f1.frames - f0.frames > 20 && f1.frames - f0.frames < 75, `${f1.frames - f0.frames} frames/s`);
  check('After 12 restarts: game clock runs at real speed', f1.time - f0.time > 900 && f1.time - f0.time < 1100, `${(f1.time - f0.time).toFixed(0)}ms per 1000ms`);
  const nodes = await p.evaluate(() => document.getElementsByTagName('*').length);
  for (let k = 0; k < 10; k++) { await p.keyboard.press('Space'); await p.click('#btn-restart'); }
  await sleep(900);
  const nodes2 = await p.evaluate(() => document.getElementsByTagName('*').length);
  check('No DOM growth across repeated restarts', Math.abs(nodes2 - nodes) < 40, `${nodes} → ${nodes2} elements`);

  const layers = await p.evaluate(() => [...document.querySelector('.hole').children].map((c) => c.classList[0]));
  check('Hole layer order: shadow → rim → pit → critter → front lip → glow → hint', layers.join('|') === 'hole-shadow|hole-rim|hole-pit|critter-mask|hole-lip|hole-glow|key-hint');
  // Critter is clipped by the hole: when fully up, its bottom edge sits below the mask's bottom edge.
  await waitFor(p, () => CritterBonk.snapshot().up.includes('up'));
  await sleep(250);
  const clip = await p.evaluate(() => {
    const i = CritterBonk.snapshot().up.indexOf('up');
    const h = document.querySelectorAll('.hole')[i];
    const face = h.querySelector('.face').getBoundingClientRect(), mask = h.querySelector('.critter-mask').getBoundingClientRect(), hole = h.getBoundingClientRect();
    return { faceBottomBelowMask: face.bottom > mask.bottom, visibleFrac: (mask.bottom - face.top) / face.height, faceH: face.height / hole.height };
  });
  check('Critter face emerges from inside the hole (bottom clipped, most of face visible)', clip.faceBottomBelowMask && clip.visibleFrac > 0.8, JSON.stringify(clip));
  await p.close();

  /* ---------------- Mobile / tablet layouts ---------------- */
  for (const [w, h, label] of [[320, 568, 'small phone 320×568'], [375, 667, 'phone 375×667'], [412, 915, 'Android 412×915'], [667, 375, 'landscape 667×375'], [768, 1024, 'tablet 768×1024'], [1024, 768, 'tablet landscape 1024×768']]) {
    const m = await newPage(b, { width: w, height: h, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
    const fold = await m.evaluate(() => ['#btn-start', '#btn-sound-start'].every((s) => { const r = document.querySelector(s).getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }));
    check(`Layout ${label}: Start and sound buttons visible without scrolling`, fold);
    await m.tap('#btn-start');
    const L = await m.evaluate(() => {
      const r = (s) => document.querySelector(s).getBoundingClientRect();
      const hud = r('#hud'), board = r('#board-wrap');
      return {
        overlap: !(hud.bottom <= board.top + 0.5 || board.bottom <= hud.top + 0.5 || hud.right <= board.left + 0.5 || board.right <= hud.left + 0.5),
        inView: board.top >= -0.5 && board.left >= -0.5 && board.bottom <= innerHeight + 0.5 && board.right <= innerWidth + 0.5 && hud.top >= -0.5 && hud.bottom <= innerHeight + 0.5,
        hscroll: document.documentElement.scrollWidth > innerWidth, cell: Math.round(document.querySelector('.hole').getBoundingClientRect().width),
      };
    });
    await waitFor(m, () => CritterBonk.snapshot().up.includes('up'));
    const s = await snap(m);
    const bb = await (await m.$$('.hole'))[s.up.indexOf('up')].boundingBox();
    await m.touchscreen.tap(bb.x + bb.width / 2, bb.y + bb.height / 2);
    const a = await snap(m);
    check(`Layout ${label}: HUD/board don't overlap, fit on screen, no sideways scroll`, !L.overlap && L.inView && !L.hscroll, JSON.stringify(L));
    check(`Layout ${label}: touch target ≥ 44px and tap scores`, L.cell >= 44 && a.score === s.score + 1, `hole ${L.cell}px`);
    await sleep(60);
    await m.screenshot({ path: path.join(SHOTS, `play-${w}x${h}.png`) });
    await m.close();
  }

  await Promise.all([gameA, gameB, gameC]);
  await b.close();
  for (const r of results) console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.name}${r.info ? '  [' + r.info + ']' : ''}`);
  const pass = results.filter((r) => r.ok).length;
  console.log(`\n${pass}/${results.length} passed`);
  console.log('Console errors/warnings:', errors.length ? errors : 'none');
  process.exit(pass === results.length && !errors.length ? 0 : 1);
})().catch((e) => { console.error('HARNESS ERROR', e); process.exit(2); });
