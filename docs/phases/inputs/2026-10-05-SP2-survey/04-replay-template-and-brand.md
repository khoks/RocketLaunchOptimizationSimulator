Provenance: SP2 step A0 survey 04 of 9 (read-only agent report, 2026-10-05, line numbers checked at commit b69ff0c); below this header, a byte copy from the session scratchpad (a0/04-replay-template-and-brand.md); a record, not edited (README.md).

# Survey 04: the replay template, its payload, the brand and the site build

SP2 step A0, read-only survey at HEAD b69ff0c (clean tree), 2026-10-05.
Phase file sections read: 5.3, 5.4, 5.9, 5.10 (plus 5.2, 5.8, 6, 7, 8, 10 for cross-checks).

Method. Files were read in full: `src/launchsim/templates/replay.html` (588 lines, 32,008 bytes,
LF, ASCII, sha256 `1fa6eba6be18c5c2a8d10a3e42880ae556375dcf1508f6feb937aca641916990`),
`src/launchsim/replay.py` (1,244 lines), `tests/test_replay.py` (682 lines), `site/build.py`
(1,162 lines), `site/assets/site.css` (355 lines), `site/assets/site.js`,
`site/templates/replay-frame.html` (50 lines), `site/examples/index.html` (732 lines),
`assets/brand/README.md`, `favicon.svg`, `logo-mark.svg`, and the prototype
`docs/findings/probes/handoff-2026-09-30/template.html` (516 lines) and `prep_data.py` (98 lines).
Three scratch scripts (same folder as this report) measured what follows:
`s04_template.py` (tokens, contrast, function lines; output `s04_template_out.txt`),
`s04_payload.py` (`replay.replay_data` on real directories; output `s04_payload_out.txt`; it also
wrote the three rendered pages `s04_*_replay.html` here), `s04_pin.py` (the pin-test extractor
and a node probe of `idxAt`/`valAt`; output `s04_pin_out.txt`). Nothing was written in the
repository; pytest was not run. A plan-mode notice arrived mid-task and was lifted before this
file was written; nothing was written while it was active.

Line numbers below are for HEAD. `git diff --stat b3150c1 HEAD -- src tests configs experiments
pyproject.toml .gitignore site/build.py` lists four files: `site/build.py` (+142), `plots.py`,
`replay.py` (72 lines changed, net -2) and `tests/test_animate.py`. The template and
`tests/test_replay.py` did not change (the template's only commit is 2eebcae).

---

## 1. `templates/replay.html`

### 1.1 Page structure

| Lines | Element | Content |
|---|---|---|
| 1-2 | `<!doctype html>`, `<html lang="en">` | |
| 4-6 | `<meta charset="utf-8">`, viewport, `<title>Ascent Replay</title>` | the title is replaced at run time (line 564) |
| 7-9 | two `preconnect` links and one stylesheet link | Google Fonts (1.3) |
| 10-129 | one `<style>` | the comment at 11-13 holds the marker `Written by launchsim replay` (line 13) |
| 132-195 | `div.wrap` (max-width 1280 px, grid, gap 16 px) | everything visible |
| 133-137 | `header` | `h1` "Ascent Replay", `p.sub#subtitle`, `div.tags#tags` |
| 139-158 | `section.panel[aria-label=Playback]` | `.transport` (140-156): `button#play.btn`, `.clock` (`span#clock`, `small#clockSub`), `.timeline` (`canvas#ticks[aria-hidden]`, `input#scrub[type=range]` step 0.1), `label.rate` with `select#rate` (Auto, 1x, 5x, 20x, 60x); then `div.chips#chips[role=group]` (157) |
| 160-167 | `div.main` (2fr 1fr) | `section` Trajectory (`h2`, `canvas#traj.plot`, `p#trajNote.legend-note`); `section.panel.telemetry#telemetry` (filled by JS) |
| 169-181 | `div.plots2` (1fr 1fr) | `section` Launch close-up (`h2`, `canvas#closeup.plot`, `p#closeupNote`); `section.panel.strips` (`h2`, `canvas#s_v`, `#s_g`, `#s_q`) |
| 183-187 | `section.panel.results` | `h2` "What each run carries to orbit", `.tablewrap > table#results`, `p#resultsNote` |
| 189-192 | `section.caveats` | `h2` "Read before quoting these numbers", `ul#caveats` |
| 194 | `p.foot#foot` | provenance line |
| 197 | `<script type="application/json" id="replay-data">__REPLAY_DATA__</script>` | the only token |
| 198-586 | one `<script>`: a strict IIFE (199-585), canvas 2D, no library | |

Layout CSS: `.main` and `.plots2` fall to one column below 900 px (118-122); padding and the
telemetry grid tighten below 520 px (123-127). Canvas sizes come from CSS `aspect-ratio`
(`#traj` 16/8.2, `#closeup` 16/10, strips 16/4.2; `#ticks` is 22 px high). A telemetry card takes
its colour from an inline custom property: `style="--c: var(--run-N)"` (line 458, CSS line 93).

### 1.2 Custom properties: the full token table

`:root` (lines 14-36) defines 21 properties; the dark values are written twice with identical
values: inside `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {...} }`
(37-45) and in `:root[data-theme="dark"] {...}` (46-52). Both dark blocks also set
`color-scheme: dark`; the light block sets no `color-scheme`.

| Token | Template light | Template dark | site.css light | site.css dark |
|---|---|---|---|---|
| `--bg` | `#f1f2ee` | `#111518` | same | same |
| `--panel` | `#fbfbf8` | `#171c20` | same | same |
| `--ink` | `#1c2226` | `#e3e7e4` | same | same |
| `--ink-2` | `#4c565c` | `#aab3b3` | same | same |
| `--ink-3` | `#7b858a` | `#78828a` | **`#626c71`** | **`#87919a`** |
| `--rule` | `#d6d9d1` | `#2b3238` | same | same |
| `--grid` | `#e3e5de` | `#222a2f` | same | same |
| `--ground` | `#8a7a62` | `#b09a78` | same | same |
| `--shaft` | `#d9d2c4` | `#2c2a25` | same | same |
| `--run-0` | `#2d5f8f` | `#7fb0e0` | same | same |
| `--run-1` | `#c2521a` | `#f08a4b` | same | same |
| `--run-2` | `#177d6f` | `#4cc2ae` | same | same |
| `--run-3` | `#7a4c8e` | `#c39ad6` | same | same |
| `--good` | `#177d6f` | `#4cc2ae` | same | same |
| `--bad` | `#b3261e` | `#f2867c` | same | same |
| `--caution` | `#9a6a00` | `#e0b653` | **`#845a00`** | same |
| `--caution-bg` | `#f6ecd2` | `#2c2513` | same | same |
| `--focus` | `#2d5f8f` | `#7fb0e0` | same | same |
| `--link` | absent | absent | `#2d5f8f` | `#7fb0e0` |
| `--code-bg` | absent | absent | `#eceee8` | `#1d2328` |
| `--accent-ink` | absent | absent | `#a8440f` | `#f08a4b` |
| `--font-display` | `"Barlow Condensed", "Arial Narrow", "Roboto Condensed", sans-serif` | not redefined | same | |
| `--font-body` | `"IBM Plex Sans", "Segoe UI", system-ui, sans-serif` | not redefined | same | |
| `--font-data` | `"IBM Plex Mono", "Cascadia Mono", Consolas, monospace` | not redefined | same | |
| `color-scheme` | not set | `dark` | `light` | `dark` |

So the site differs from the template in exactly: `--ink-3` (both themes), the light `--caution`,
three added tokens (`--link`, `--code-bg`, `--accent-ink`) and `color-scheme: light` on `:root`.
`site/assets/site.css` 14-60 holds the site's set (24 light properties, 21 dark overrides, the
dark block again written twice). `site/examples/index.html` 16-62 and `site/deck/index.html`
carry their own inline copies of the same values.

Contrast (WCAG 2.x, computed by `s04_template.py`):

| Pair | Template light | Site light | Template dark | Site dark |
|---|---|---|---|---|
| `--ink-3` on `--bg` | 3.36 | 4.79 | 4.68 | 5.72 |
| `--ink-3` on `--panel` | 3.64 | 5.19 | 4.38 | 5.35 |
| `--ink-3` on `--caution-bg` | 3.21 | 4.57 | 3.88 | 4.74 |
| `--caution` on `--caution-bg` | 4.02 | 5.18 | 7.95 | 7.95 |
| `--ink-2` on `--panel` / `--bg` | 7.25 / 6.69 | same | 8.02 / 8.57 | same |
| `--ink` on `--panel` / `--bg` | 15.51 / 14.30 | same | 13.75 / 14.70 | same |
| `--run-1` on `--panel` / `--bg` | 4.49 / 4.14 | same | 6.90 / 7.38 | same |
| `--accent-ink` on `--panel` / `--bg` | - | 5.79 / 5.34 | - | 6.90 / 7.38 |
| `--run-0` on `--panel` / `--bg` | 6.44 / 5.94 | same | 7.51 / 8.03 | same |
| `--run-2` (= `--good`) on `--panel` / `--bg` | 4.82 / 4.45 | same | 7.88 / 8.42 | same |
| `--run-3` on `--panel` / `--bg` | 6.23 / 5.74 | same | 7.29 / 7.79 | same |
| `--bad` on `--panel` / `--bg` | 6.30 / 5.81 | same | 6.93 / 7.41 | same |
| `--ground` on `--panel` / `--bg` | 4.02 / 3.70 | same | 6.33 / 6.76 | same |
| `--ground` on `--shaft` | 2.77 | same | 5.28 | same |
| `--run-1` on `--shaft` | 3.09 | same | 5.76 | same |
| `--ink-2` on `--shaft` | 5.00 | same | 6.70 | same |
| `--shaft` against `--panel` / `--bg` (two fills) | 1.45 / 1.34 | same | 1.20 / 1.28 | same |

Readings for a scene: the template's `--ink-3` fails 4.5:1 in light mode everywhere and on the
panel and caution panel in dark mode; the canvas axis text uses it (`PAL.ink3`, lines 283, 435).
The light `--run-1` (4.14 on `--bg`) and `--run-2` (4.45 on `--bg`) are drawing colours, not
small-text colours. `--shaft` is nearly invisible against `--bg` or `--panel` without an outline,
and the light `--ground` line on the `--shaft` fill is 2.77:1, below the 3:1 usually asked of
graphics; the landing page's illustration outlines the shaft (`.ill .shaft { fill: var(--grid);
stroke: var(--ground) }`, site.css 188).

### 1.3 Fonts

Lines 7-9:

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">

Weights: Barlow Condensed 500/600/700 (h1, h2, buttons, card names), IBM Plex Sans 400/500/600
(body), IBM Plex Mono 400/500 (numbers, tags, clock, footer). The same three lines are in
`site/index.html` 16-18, `site/examples/index.html` 9-11 and `site/templates/manual.html`.
Canvas text reads the stacks at draw time (`css("--font-data")`, `css("--font-body")`: lines 282,
297, 362, 390, 431) and the page redraws once at `document.fonts.ready` (581). Removing the three
links leaves a working page on the fallback stacks; no other line depends on the web fonts.

### 1.4 Dark mode

CSS only: `prefers-color-scheme: dark` (37) unless `data-theme="light"` is set on `<html>`, and
`data-theme="dark"` (46) forces dark. There is **no toggle** in the page and no script that sets
`data-theme`. The script only listens: `matchMedia("(prefers-color-scheme: dark)")` change (577)
and a `MutationObserver` on the `data-theme` attribute of `<html>` (578), both calling `draw()`,
which re-reads the palette for the canvases (`readPalette()` at 496, every frame).
The site's own pages have a three-state toggle (auto, light, dark; `#theme-btn`,
`site/assets/site.js` 12-31) stored in `localStorage["las-theme"]`, applied by an inline head
script (`site/index.html` 20-27). The frame that `site/build.py` adds to a gallery replay page has
neither the head script nor the button, so a framed replay page follows the system theme only.

### 1.5 JavaScript: every function

Top-level state and constants: `DATA` (201), `META` (202), `PHASE_NAME` (203-207; nine phases:
HOLD, ASSIST, COAST_PRE_IGN, VERTICAL_RISE, KICK, GRAVITY_TURN, COAST_STAGING, LTG_BURN, COAST),
`EVENT_LABEL` (208-212; twelve names: push_start, release, ignition, kick_start, kick_end,
ramp_end, propellant "MECO", staging, fairing "Fairing off", cutoff "Orbit", apex, impact),
`MARK_EVENTS = ["propellant", "fairing", "cutoff", "impact"]` (213), `reduceMotion` (214),
`runs` (216, shallow copies of `DATA.runs`), `colorVar` (217), `visible` (219, every run on),
`T_MIN`, `T_MAX` (220-221, over all runs, visible or not), `let tNow = 0, playing = false,
lastFrame = null` (222), `PAL` (229), `fmt` (257), `orDash` (258), `qOr` (259), `shown` (339),
`r.alt_km` derived per run (343), `X_MAX`, `Y_MAX`, `Y_MIN` (344-346).

| Function | Lines | Purpose |
|---|---|---|
| `esc(s)` | 225-227 | HTML-escape `& < > " '` for strings put into `innerHTML` |
| `css(name)` | 228 | computed value of a custom property on `<html>`, trimmed |
| `readPalette()` | 230-234 | fill `PAL` with nine tokens (ink, ink2, ink3, rule, grid, ground, shaft, panel, caution) and one colour per run (`--run-<color>`) |
| `idxAt(t, arr)` | 235-241 | index of the last element <= t by bisection, clamped to the ends |
| `valAt(run, field, t)` | 242-249 | linear interpolation of `run[field]` at t; end values outside the span; null when either neighbour is null |
| `phaseAt(run, t)` | 250-255 | `pre_label` before the first sample, `end_label` from the last, else the phase of the sample at or before t, through `PHASE_NAME` |
| `clockText(t)` | 260 | "T+12.3 s" / "T-2.6 s" (U+2212 written as `−`) |
| `signedKg(v)` | 261 | "+1,499 kg" with a true minus sign |
| `setupCanvas(cv)` | 263-271 | size the backing store to CSS size x devicePixelRatio (only when it changed), set the transform, clear; returns `{ctx, w, h}` in CSS pixels |
| `niceStep(span, target)`, `niceMax(v)` | 272-275, 276 | 1-2-5 tick steps |
| `axes(ctx, box, xr, yr, xlabel, ylabel, opts)` | 277-302 | grid, tick labels, frame, axis titles; returns the scales `{sx, sy}` |
| `pathXY(ctx, run, fx, fy, sx, sy, tEnd)` | 303-316 | path of one field against another up to tEnd (interpolated end point) |
| `pathTime(ctx, run, fy, sx, sy, tA, tB)` | 317-330 | path of a field against time between tA and tB, broken at nulls |
| `stroke(ctx, run, width, alpha)` | 331-334 | stroke the current path in the run's colour, dashed for a yardstick run |
| `marker(ctx, x, y, key, r)` | 335-338 | filled dot with a panel-coloured ring |
| `swatch(r)` | 340 | the legend swatch `<span class="sw">` |
| `drawTraj()` | 348-368 | altitude (km) against downrange (km) on flat axes: faint full path, bold path to tNow, dots for `MARK_EVENTS` passed (labels for the first shown run only), the position marker (altitude clamped at 0) |
| `drawCloseup()` | 370-411 | altitude (m) against time from `min(-3, floor(T_MIN) - 0.5)` to 30 s: shaft band and floor lines from `META.floors`, ground line, paths, time cursor, markers |
| `drawStrip(id, field, label, yr0)` | 413-424 | one strip chart over `[T_MIN, T_MAX]` with a cursor |
| `drawTicks()` | 426-438 | event ticks and labels above the scrubber, from the first shown run |
| `telemetry()` | 440-465 | the telemetry update: rebuilds `#telemetry` as one card per shown run with eight cells (Altitude, Speed, Path angle, Mass, Felt g, q, Mach, Downrange); after a run's last sample felt g reads 0.00 for an inserted run and a dash otherwise; null q or Mach reads "no air" |
| `results()` | 467-493 | the results table, twelve columns (Run, Payload capacity, vs baseline, Ideal screening, Exit speed, Felt g on track, Peak felt g in flight, Max-Q, Gravity loss, Drag loss, Steering loss, Back-pressure loss); built once |
| `draw()` | 495-506 | `readPalette`, all six canvases, `telemetry`, clock text, "playing at Nx" or "paused", scrubber value |
| `currentRate()` | 509-515 | the rate select, or Auto: 1x below 12 s, 5x below 45 s, 30x after |
| `tick(ts)` | 516-525 | one animation frame: advance `tNow` by wall time x rate, stop at `T_MAX`, draw, request the next frame |
| `setPlaying(p)` | 526-533 | set the state and the button; restart from `T_MIN` when within 0.05 s of the end |
| `listItems(id, items)` | 536-538 | fill a `<ul>` with escaped items |
| `init()` | 539-583 | wiring, below |

`init()` in order: scrubber bounds rounded outward to 0.1 s (543) and its `input` handler, which
clamps to `[T_MIN, T_MAX]` (544); Play click (545); rate `change` redraws (546); keyboard (547-550);
one chip button per run with `aria-pressed` and `title = detail` (551-563); `document.title =
"Ascent Replay: " + META.experiment` (564); subtitle, tags, notes, caveats, footer (565-573);
`results()` (574); resize and theme observers (575-578); first paint at `tNow = clamp(0)` (579-580);
redraw when fonts are ready (581); auto-play from `T_MIN` after 900 ms unless reduced motion (582).

- **Scrubber and rate select:** native `<input type=range>` (145) and `<select>` (148-154).
  `draw()` writes `scrub.value = tNow.toFixed(1)` every frame (505).
- **Keyboard (547-550):** Space anywhere toggles play, except when the focus is on an INPUT,
  SELECT or BUTTON (the native behaviour then applies: Space on the Play button clicks it).
  Nothing else is handled by the page; arrows, Home and End work on the focused range input
  natively (0.1 s per arrow). No frame-step or rate keys.
- **Reduced motion:** CSS line 128 (`* { scroll-behavior: auto; }`, which changes nothing here)
  and the one-time read at 214 that suppresses the auto-start (582). Play on demand still animates.
- **Resize:** a `ResizeObserver` on `.wrap` (576) redraws; `setupCanvas` re-measures the canvas
  and `devicePixelRatio` on every draw.
- **Clock under Auto** for the reference page (T from -2.607 to 538.801 s): 14.6 s at 1x, 6.6 s
  at 5x, 16.5 s at 30x, about 38 s in all. The select offers 1x, 5x, 20x, 60x; 30x exists only
  inside Auto.
- `tick` does not cap the frame interval: after a hidden tab (no animation frames) the next frame
  advances `tNow` by the whole absence times the current rate. Harmless here because every frame
  is drawn from `tNow` alone.

### 1.6 The helpers a scene page would copy verbatim

All eight are complete multi-line functions at two-space indent, 60 lines and 2,344 characters in
all. They close over these names, which a copy must keep: `runs`, `colorVar`, `css`, `PAL`,
`PHASE_NAME`, `tNow`, `playing`, `lastFrame`, `T_MIN`, `T_MAX`, `draw`, and the element ids
`play` and `rate`; a run must carry `t`, `phase`, `pre_label`, `end_label`, `key`, `color`.

`readPalette` (230-234):

      function readPalette() {
        PAL = { ink: css("--ink"), ink2: css("--ink-2"), ink3: css("--ink-3"), rule: css("--rule"), grid: css("--grid"),
          ground: css("--ground"), shaft: css("--shaft"), panel: css("--panel"), caution: css("--caution") };
        runs.forEach(r => { PAL[r.key] = css(colorVar(r)); });
      }

`idxAt` (235-241):

      function idxAt(t, arr) {
        if (t <= arr[0]) return 0;
        if (t >= arr[arr.length - 1]) return arr.length - 1;
        let lo = 0, hi = arr.length - 1;
        while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (arr[mid] <= t) lo = mid; else hi = mid; }
        return lo;
      }

`valAt` (242-249):

      function valAt(run, field, t) {
        const T = run.t, Y = run[field];
        if (t <= T[0]) return Y[0];
        if (t >= T[T.length - 1]) return Y[Y.length - 1];
        const i = idxAt(t, T), f = (t - T[i]) / (T[i + 1] - T[i]);
        if (Y[i] === null || Y[i + 1] === null) return null;
        return Y[i] + f * (Y[i + 1] - Y[i]);
      }

`phaseAt` (250-255):

      function phaseAt(run, t) {
        if (t < run.t[0]) return run.pre_label;
        if (t >= run.t[run.t.length - 1]) return run.end_label;
        const p = run.phase[idxAt(t, run.t)];
        return PHASE_NAME[p] || p;
      }

`setupCanvas` (263-271):

      function setupCanvas(cv) {
        const dpr = window.devicePixelRatio || 1;
        const w = cv.clientWidth, h = cv.clientHeight;
        if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
        const ctx = cv.getContext("2d");
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, w, h);
        return { ctx, w, h };
      }

`currentRate`, `tick`, `setPlaying` (509-533, contiguous):

      function currentRate() {
        const sel = document.getElementById("rate").value;
        if (sel !== "auto") return Number(sel);
        if (tNow < 12) return 1;
        if (tNow < 45) return 5;
        return 30;
      }
      function tick(ts) {
        if (!playing) { lastFrame = null; return; }
        if (lastFrame !== null) {
          tNow = Math.min(T_MAX, tNow + (ts - lastFrame) / 1000 * currentRate());
          if (tNow >= T_MAX) setPlaying(false);
        }
        lastFrame = ts;
        draw();
        if (playing) requestAnimationFrame(tick);
      }
      function setPlaying(p) {
        playing = p;
        const b = document.getElementById("play");
        b.textContent = p ? "Pause" : "Play";
        b.setAttribute("aria-label", p ? "Pause" : "Play");
        if (p) { if (tNow >= T_MAX - 0.05) tNow = T_MIN; lastFrame = null; requestAnimationFrame(tick); }
        draw();
      }

Measured behaviour that matters for the scene's grid (node, `s04_pin_out.txt`). `idxAt` and
`valAt` accept a grid with **repeated times**. With `t = [0, 5, 10, 10, 11, 20]` and
`m = [100, 90, 80, 50, 49, 40]`: `valAt` gives 80.002 at 9.999, 50 at exactly 10, 49.999 at
10.001; `idxAt(10)` is 3 (the last of the equal times). Three equal times, and a repeat at the
first or last sample, also work; no division by zero occurs because `idxAt` never returns the
first of two equal times. So a step (the mass drop at staging, thrust off at MECO) can be carried
as two samples at the event time, before and after, and the unchanged helpers show it without
smearing. One quirk: `valAt` returns null whenever the sample after the bracketing one is null,
even at f = 0 (q at exactly 10 in the probe, with `q = [null, 1, 2, 2, null, 4]`, is null).

---

## 2. The payload the template consumes

### 2.1 Builder and embedding

- `replay.replay_data(run_dir: Path, runs: Sequence[str] | None) -> dict[str, Any]` (replay.py
  1105-1160) returns `{"meta": {...}, "runs": [...]}`.
- `replay.run_record(run_dir, name, source, baseline_name, base_cfg, vehicle, index) -> dict`
  (980-1060) builds one run; `run_series(frame)` (430-442) the series; `run_events(path,
  offset_s)` (445-464) the events.
- `replay.embed_json(data: dict[str, Any]) -> str` (1166-1171):
  `json.dumps(data, separators=(",", ":"), allow_nan=False, ensure_ascii=True)` then
  `.replace("<", "\\u003c")`. NaN or Infinity raises `ValueError`; the text is pure ASCII and is
  itself valid JSON (`json.loads(text) == data`, test line 363), so the same string can be an
  HTTP response body.
- `replay.load_template() -> str` (1174-1177): `resources.files("launchsim").joinpath(*REPLAY_TEMPLATE).read_text(encoding="utf-8")`
  with `REPLAY_TEMPLATE = ("templates", "replay.html")` (62).
- `replay.render_page(data) -> str` (1180-1185): the token `REPLAY_DATA_TOKEN = "__REPLAY_DATA__"`
  (64) must occur exactly once (`RuntimeError` otherwise); one `str.replace`.
- `replay.write_replay_page(run_dir, runs, out_path) -> Path` (1237-1244): data, then
  `check_replay_out`, then render, then `out_path.write_text(page, encoding="utf-8", newline="\n")`.
- The page reads it with `JSON.parse(document.getElementById("replay-data").textContent)` (201).
- A page is exactly the template with the token replaced: page bytes = JSON bytes + 31,993
  (32,008 - 15), on all three measured pages.

### 2.2 `meta` (17 keys)

| Key | Type | Example (reference page) | Read by the page |
|---|---|---|---|
| `experiment` | str | `silo_screening_2d` | title (564) |
| `timestamp` | str | `20260930T175743Z` | no |
| `source` | str | `results/silo_screening_2d/20260930T175743Z` | footer (572) |
| `git` | str | `7ad381f227a9` | footer |
| `dirty` | bool | false | footer |
| `version` | str | `0.1.0` | footer |
| `vehicle` | str | `generic_f9_class_2d` | no |
| `baseline` | str | `pad` | results table (476) |
| `orbit` | str | `200 km circular orbit` | no |
| `subtitle` | str | "Experiment silo_screening_2d: the generic_f9_class_2d vehicle flown to a 200 km circular orbit in 4 runs; ..." | 565 |
| `tags` | list of 7 str | planar 2-D; rotating Earth; drag and back-pressure; sweep-optimized guidance; unthrottled; 200 km circular; latitude 28.5 deg, azimuth 90 deg | 566 |
| `closeup_notes` | list of str (3) | | 567 |
| `results_notes` | list of str (2 or 3) | | 570 |
| `caveats` | list of str (6; 120 to 381 characters each) | model, calibration, structure, drive, upper bound, did-not-reach-orbit | 571 |
| `floors` | list of `{depth_m, label, vertical}` | `[{"depth_m": 100.0, "label": "silo floor, 100 m down", "vertical": true}]` | 377-398 |
| `downrange_note` | str | "Downrange is the ground arc from the launch site over the rotating Earth." | 569 |
| `yardstick_shown_kg` | float | 0.5 | 481 |

### 2.3 One run record (38 keys, in this order)

`key`, `label`, `detail`, `role`, `compared_to`, `color`, `dashed`, `baseline`, `assisted`,
`vertical`, `status`, `inserted`, `t`, `alt_m`, `x_km`, `v`, `gamma_deg`, `m_t`, `g_ax`, `q_kpa`,
`mach`, `phase`, `events`, `payload_kg`, `payload_delta_kg`, `ideal_screening_kg`,
`screening_yardstick_kg`, `upper_bound`, `upper_bound_reasons`, `max_q_kpa`, `peak_g_flight`,
`losses_mps`, `exit_speed_mps`, `felt_g_track`, `push_s`, `start_alt_m`, `pre_label`, `end_label`.

- Text and flags: `key` (run name), `label` ("pad (baseline)"), `detail` ("vertical silo 100 m
  deep, 3 g net push, exit 76.7 m/s; cold start: stage 1 lit T+0.5 s after release (2 s ramp)"),
  `role` (run, bound, paired_baseline, case, offload), `compared_to` (name or null), `color`
  (index 0-3), `dashed` (step startup), `baseline`, `assisted`, `vertical`, `status`, `inserted`.
- Series, all the same length: `t` [s after release, 3 decimals] and the eight `SERIES_FIELDS`
  (replay.py 119-128): `alt_m` (1 decimal), `x_km` (3), `v` (Earth-relative, 2), `gamma_deg`
  (wrapped to [-180, 180], 2), `m_t` (3), `g_ax` (3), `q_kpa` (3, null in a vented shaft),
  `mach` (3, null likewise); plus `phase` (one phase name per sample, the last row at or before
  it).
- Grid (`replay_grid`, 394-402): the first time, every 0.1 s up to 40 s after release, every 1 s
  after, the last time; unique; event times are not added. `read_series` (365-377) keeps the last
  of two rows with the same time, so a step is spread over one grid step (up to 1 s late in the
  flight).
- `events`: every row of events.csv as `{t, name, stage, alt_m, x_km, v}`; no mass, no phase.
- Metrics: `payload_kg`; `payload_delta_kg`, `ideal_screening_kg`, `screening_yardstick_kg` (null
  unless compared and inserted); `upper_bound`, `upper_bound_reasons`; `max_q_kpa`;
  `peak_g_flight`; `losses_mps` (four keys, null unless inserted); `exit_speed_mps`,
  `felt_g_track`, `push_s`, `start_alt_m` (null for a pad start); `pre_label`, `end_label`.
- Not read by the page's script: `role`, `assisted`, `vertical`, `upper_bound`,
  `upper_bound_reasons`, `push_s`, `start_alt_m`, and an event's `stage` and `v`. They feed the
  Python-side text (caveats, notes, floors).

### 2.4 Sizes of real examples

Reference page: `results/silo_screening_2d/20260930T175743Z`, runs pad, silo_cold,
silo_hot_ramp_on_track, silo_failed, at HEAD.

| Item | Value |
|---|---|
| Page | 247,949 bytes, ASCII, sha256 `3ca23dc5ce6532e6b9e3fd4656ab4846bcb4cdddfced7a077ce05c9411fd1eab` (the value the phase file gives for b3150c1: SP1 step 10a did not change the page) |
| JSON | 215,956 bytes; `meta` 3,208 |
| pad | 66,027 bytes; 918 samples (-2.0 to 536.301 s; 420 below 40 s, 498 after); 10 events, 870 bytes |
| silo_cold | 67,362 bytes; 927 samples (-2.607 to 538.801 s); 12 events, 1,034 bytes; 27 nulls each in `q_kpa` and `mach` |
| silo_hot_ramp_on_track | 67,362 bytes; 925 samples; 12 events |
| silo_failed | 11,975 bytes; 185 samples (-2.607 to 15.689 s); 6 events (push_start, release, ignition_failed, apex, impact, end) |
| One series of pad | `t` 4,931 bytes; the eight numeric fields 4,895 to 6,994 bytes each; `phase` 11,823 bytes (18% of the record) |

Other pages: pad with silo_cold_s1 of `silo_offload_2d/20261003T112934Z` gives 167,055 bytes
(JSON 135,062), the size of the committed `site/examples/pad-vs-silo-offload.html`; pad,
silo_cold_s1, silo_cold_s1__pad and pad__offload_stage1 give 298,591 bytes (JSON 266,598), the
figure in phase section 5.3.

Estimate for the scene (not measured): nine more numeric series at about 6 kB each put a run near
120 kB and four runs near 0.5 MB, inside the phase file's 1 MB.

Event facts the scene has to handle, from the same output:
- `ignition` occurs twice per orbital run (stage1 and stage2), `propellant` can occur for stage 2:
  pad__offload_stage1 ends with `("propellant", "stage2", 536.301)` and has no `cutoff`. The
  template labels by name alone (`EVENT_LABEL.propellant = "MECO"`), so that page marks a stage-2
  depletion "MECO". A scene must label by name and stage.
- Several events share one time: silo_hot_ramp_on_track has `ramp_end`, `release` and
  `kick_start` at 0.0; `propellant` and `staging` always coincide; `cutoff` and `end` coincide.
- `EVENT_LABEL` has no entry for `liftoff`, `ignition_failed`, `ignition_height` or `end`; the
  page falls back to the raw name, and only `MARK_EVENTS` are drawn.

---

## 3. Brand

### 3.1 `assets/brand/README.md` (65 lines)

- All rights reserved; the files are public to view only.
- The mark: a cross-section, rocket rising out of an underground silo, linear-motor coil sections
  in orange on the shaft walls, brightest at the level the rocket has just left, a short motion
  trail below the tail, sky above the ground line, a grey rim around the earth half. Drawn on a
  64 x 64 grid; reads at 32 px; `favicon.svg` is "a simpler version for 16 px".
- The wordmark `launch-assist-sim` is hand-drawn strokes (no font); the two hyphens are orange.
- Usage rule: `logo.svg` switches its wordmark colour with `prefers-color-scheme`, so use it only
  on pages whose theme also follows `prefers-color-scheme`; otherwise `logo-light.svg` or
  `logo-dark.svg`.
- Palette table (README 38-48): the site's values, `--ink-3` `#626c71` / `#87919a`,
  `--caution` `#845a00` / `#e0b653`, `--accent-ink` `#a8440f` / `#f08a4b` ("site only: kickers,
  labels"); `--run-0` is "steel blue (sky, trajectory)", `--run-1` "coil orange (coils, hyphens,
  the silo path)".
- The mark's fixed colours on both themes: sky `#2d5f8f`, earth `#1c2226`, shaft `#2b3238`,
  surface `#b09a78`, coils `#f08a4b`, rocket `#fbfbf8` with shading `#dfe4e1`, rim `#4c565c`.
- Typography: headings Barlow Condensed, body IBM Plex Sans, numbers and code IBM Plex Mono, all
  loaded from Google Fonts on the site.
- Regenerate: `python assets/brand/build_brand.py` (SVGs), `python assets/brand/render_png.py`
  (PNGs; needs Pillow and numpy).

### 3.2 Files

| File | Bytes | Note |
|---|---|---|
| `favicon.svg` | 1,111 | one line plus a newline, ASCII, sha256 `2dda5459...02bc6d`; ids `fc`, `fr`; 12 `#` and 106 `"` characters |
| `logo-mark.svg` | 1,540 | one line, ASCII; ids `mc`, `mr`, `mt`; three coil rows and a trail gradient |
| `logo.svg` | 4,009 | lockup; inline `<style>` with a `prefers-color-scheme` rule |
| `logo-light.svg`, `logo-dark.svg` | 3,870 each | fixed-colour lockups |
| `banner.svg`, `banner-light.svg` | 5,849 each | 1280 x 320 |
| `banner-compact.svg` | 5,196 | 640 x 380 |
| `social-preview.svg` | 6,350 | 1280 x 640 |
| PNGs | | `logo.png`, `logo-dark.png`, `logo-mark.png` (512 px), `banner.png`, `social-preview.png` |

`favicon.svg` in full:

    <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" role="img" aria-label="launch-assist-sim"><title>launch-assist-sim</title><clipPath id="fc"><rect width="64" height="64" rx="12"/></clipPath><clipPath id="fr"><path d="M28 18.5C28 12 30.6 7.4 32 5.5C33.4 7.4 36 12 36 18.5V47H28Z"/></clipPath><g clip-path="url(#fc)"><rect width="64" height="41" fill="#2d5f8f"/><rect y="41" width="64" height="23" fill="#1c2226"/><rect x="25" y="41" width="14" height="23" fill="#2b3238"/><path d="M0 42.25H25M39 42.25H64" stroke="#b09a78" stroke-width="2.5"/><path d="M19.5 48.5h5.5M39 48.5h5.5" stroke="#f08a4b" stroke-opacity="1.0" stroke-width="3.6"/><path d="M19.5 56.5h5.5M39 56.5h5.5" stroke="#f08a4b" stroke-opacity="0.5" stroke-width="3.6"/><path d="M28 18.5C28 12 30.6 7.4 32 5.5C33.4 7.4 36 12 36 18.5V47H28Z" fill="#fbfbf8"/><rect x="33.6" y="4" width="3" height="44" fill="#dfe4e1" clip-path="url(#fr)"/><rect x="28" y="27" width="8" height="2.2" fill="#1c2226"/><path d="M0 41V52A12 12 0 0 0 12 64H52A12 12 0 0 0 64 52V41" fill="none" stroke="#4c565c" stroke-width="5"/></g></svg>

How the site uses them: every page links `favicon.svg` as the tab icon
(`<link rel="icon" href=".../assets/brand/favicon.svg" type="image/svg+xml">`), and shows
**`logo-mark.svg`** (not the favicon) at 28 px in the header (24 px in the replay frame), followed
by the name as text in Barlow Condensed 700 with the hyphens in `--run-1`
(`<span class="wm">launch<span class="hy">-</span>assist<span class="hy">-</span>sim</span>`,
`site/examples/index.html` 215; `.brand` rules in site.css 83-85). No page uses the SVG wordmark
in its header.

The landing page's illustration classes are a ready vocabulary for a schematic silo
(site.css 182-200): `.sky` fill `--bg`; `.earth` fill `--shaft`; `.ground-line` stroke `--ground`
2.5 px; `.shaft` fill `--grid`, stroke `--ground` 1.2 px; `.coil` stroke `--run-1` 4 px;
`.rocket` fill `--panel`, stroke `--ink` 1.4 px; `.band` fill `--ink`; `.orbit` dashed `--ink-3`;
`.path-pad` `--run-0`; `.path-silo` `--run-1`.

### 3.3 The token set the app and the scene should use

The site's values (site.css 14-60), light then dark:

    --bg #f1f2ee / #111518        --panel #fbfbf8 / #171c20
    --ink #1c2226 / #e3e7e4       --ink-2 #4c565c / #aab3b3      --ink-3 #626c71 / #87919a
    --rule #d6d9d1 / #2b3238      --grid #e3e5de / #222a2f
    --ground #8a7a62 / #b09a78    --shaft #d9d2c4 / #2c2a25
    --run-0 #2d5f8f / #7fb0e0     --run-1 #c2521a / #f08a4b
    --run-2 #177d6f / #4cc2ae     --run-3 #7a4c8e / #c39ad6
    --good #177d6f / #4cc2ae      --bad #b3261e / #f2867c
    --caution #845a00 / #e0b653   --caution-bg #f6ecd2 / #2c2513
    --focus #2d5f8f / #7fb0e0     --link #2d5f8f / #7fb0e0
    --code-bg #eceee8 / #1d2328   --accent-ink #a8440f / #f08a4b
    --font-display "Barlow Condensed", "Arial Narrow", "Roboto Condensed", sans-serif
    --font-body "IBM Plex Sans", "Segoe UI", system-ui, sans-serif
    --font-data "IBM Plex Mono", "Cascadia Mono", Consolas, monospace
    color-scheme: light / dark

with the same three-block pattern (`:root`; the media query on `:root:not([data-theme="light"])`;
`:root[data-theme="dark"]`). No token exists for a plume, a propellant fill, a carriage or steel;
a scene that needs them adds tokens of its own in both themes and its `readPalette` equivalent.

---

## 4. `site/build.py`: framing, the gallery, the link check

### 4.1 How a replay page is framed

- Constants: `REPLAY_FRAME = SITE_SRC / "templates" / "replay-frame.html"` (70), `REPLAY_DIR =
  "examples"` (87), `REPLAY_MARKER = "Written by launchsim replay"` (88), `FRAME_PART_RE` (89),
  `BODY_OPEN_RE` (90).
- `frame_replays(out, log)` (941-957) visits `sorted((out / "examples").glob("*.html"))` (not
  recursive), skips any page without the marker (948-949), frames it and applies the text fixes,
  and counts it. A page with the marker but without head and body is an error (953).
- `frame_replay(text, parts, root)` (899-915) inserts the frame's `head` part just before
  `</head>` (after the page's own `<style>`, so its rules win), `top` just after `<body ...>`,
  `bottom` just before the last `</body>`; `{{root}}` becomes `../`.
- The frame (`site/templates/replay-frame.html`): `head` = a favicon link and a `<style>` that
  overrides exactly two tokens, `--ink-3` (`#626c71` / `#87919a`) and `--caution` (`#845a00` /
  `#e0b653`), plus the `las-` bar and footer rules; `top` = a bar with the mark, the name, and
  links "Animation examples" (`index.html`), Home, Manual; `bottom` = the all-rights-reserved
  notice with a LICENSE link. The frame file says to remove the two overrides "once
  src/launchsim/templates/replay.html has these values". It holds one non-ASCII character (the
  copyright sign), so a framed page is UTF-8, not ASCII.
- `fix_replay_text(text, label, log)` (918-938) then applies:
  - `REPLAY_TEXT_FIXES` (123-166), five plain `str.replace` pairs applied to **every** replay
    page, with no warning when one does not match: (1) the drive caveat's closing sentence
    (`REPLAY_STALE_TEXT = "Each of these favours the assisted runs."`, 122), matched only in the
    exact 3 g wording; (2) the grammar "starts 100 m below ground and leave the silo mouth";
    (3)-(5) three **JavaScript** patches matched against template source lines: line 379
    (`const yr = [deepest > 0 ? -1.6 * deepest : ...`, the floor label overprinting the time
    axis), line 289 (`ctx.fillText(fmt(x, xs < 1 ? 1 : 0), px, box.y + box.h + 4);`, the last
    x tick label cut at the canvas edge) and line 436 (`if (x - lastX > 60) { ctx.fillText(...`,
    the last timeline label cut). Each of the three old strings occurs exactly once in the
    template at HEAD.
  - `REPLAY_PAGE_FIXES` (200-260), per file name: four pairs for `pad-vs-silo-offload.html`, seven
    for `offload-vs-paired-pad.html` (the drive sentence for offloads, 41.3 t to 41.26 t rounding,
    "the fully fuelled stack" for an offloaded run, the paired pad's label "(offload)" and its
    caveat and subtitle). A pair that matches neither its old nor its new text is a warning (927).
  - A page still holding `REPLAY_STALE_TEXT` afterwards is a build **error** (932-937).
- The five gallery replay pages (`failed-ignition`, `ignition-timing`, `offload-vs-paired-pad`,
  `pad-vs-silo-cold`, `pad-vs-silo-offload`; 114,305 to 304,598 bytes) are committed as
  `launchsim replay` wrote them: each equals the template at HEAD on lines 1-196 and 198-588.

### 4.2 The gallery index

`site/examples/index.html` (732 lines, 66,439 bytes, UTF-8 with 50 non-ASCII characters) is
written by hand. `build.py` copies it, checks its links and nothing else (it has no stamp
markers). It carries its own inline `<style>` (12-202, the site's tokens again) and scripts
(203-210 theme from storage; 646-730 theme button, code wrapping, copy buttons).

Adding an entry means editing, by hand:

1. the page itself, written with `--out site/examples/<name>.html` (a name ending `_replay.html`
   would be git-ignored, `.gitignore` 19), and any media under `site/examples/media/`;
2. a line in the table of contents `ul.toc` (261-272): `<li><a href="#<id>">...</a></li>`;
3. optionally a group heading `section.group` (275-286; 425 on) with kicker, `h2`, provenance
   tags and an intro;
4. the card: `<article class="example" id="<id>" aria-labelledby="...">` (303-370 is the fullest
   one) holding `header` (`p.kicker`, `h2`, `p.summary`); optionally `figure` (`video.media` with
   a poster and an MP4 source, a GIF fallback link, `figcaption`); `div.actions`
   (`<a class="btn" href="<name>.html">Open the interactive replay</a>`, ghost buttons for MP4 and
   GIF with sizes); `div.col` "What it shows"; `div.tablewrap > table.nums`; `p.src`;
   `div.cols` with two `div.col` lists (`ul.for`, `ul.against`); `details.cmd` with the commands
   in `div.codeblock > pre > code`;
5. the footer's "Data:" paragraph (641) and the meta description (7).

### 4.3 The link check

`LinkChecker.run` (1020-1034) parses every `*.html` under the output folder with `PageScan`
(978-996), which records `id` (and `<a name>`) and every `href`, `src`, `poster`, `xlink:href`
and `srcset` URL. `check` (1040-1066): an http(s) URL is skipped unless it is a
`github.com/khoks/RocketLaunchOptimizationSimulator/(blob|tree)/main/...` link, which
`check_repo_refs` (1068-1084) tests against the checkout (the path must exist, must not be
git-ignored, and a `#fragment` on a `.md` file must be one of its heading anchors); other schemes
are skipped; `#id` must exist on the page; a relative path must exist inside the output folder
(a folder means its `index.html`) and its fragment must be an id of that page. Any failure makes
the build exit 1 unless `--allow-broken-links`. Script contents are not parsed. A self-contained
scene page has nothing to fail except in-page `href="#..."` references (for instance SVG `<use>`).

---

## 5. The 2026-09-30 prototype

`docs/findings/probes/handoff-2026-09-30/template.html` (516 lines, a fragment: no doctype, html,
head, charset or viewport; raw non-ASCII characters; token `__DATA__`) and `prep_data.py`
(98 lines; hard-coded repository path, directory and four runs).

- **Pitch.** `prep_data.py` line 78 emits `"pitch_deg": col("pitch_rad", 180.0 / np.pi, 2)`.
  The prototype's template never reads it: "pitch" appears there only in the words "Pitch kick"
  (lines 174, 192, 196). So the prototype drew nothing that the shipped page lacks; it only
  carried one unused series. The shipped builder dropped it and `tests/test_replay.py` 311 asserts
  `"pitch_deg" not in silo`.
- The shipped page draws strictly more: generated subtitle, notes and caveats; `META.floors` in
  place of a hard-coded 100 m shaft; axis ranges from the data (the prototype fixes 1,800 km by
  220 km); the `impact` event; `esc`; yardstick lines; the 12-column table (the prototype has 8).
- Helper drift since the prototype: `idxAt`, `valAt`, `setupCanvas`, `currentRate`, `tick`,
  `setPlaying`, `niceStep`, `pathXY`, `pathTime`, `marker` and `draw` are byte-identical in both;
  `readPalette` differs in one line (`COLOR_VAR[r.key]` became `colorVar(r)`); `phaseAt` differs
  (hard-coded labels became `pre_label` and `end_label`).
- Reusable for a scene: nothing beyond what the shipped template has. One point on angles:
  `prep_data.py` resampled `pitch_rad` and `gamma_rel_rad` linearly with no wrapping, which is
  continuous because both columns are unwrapped per run. The shipped builder wraps
  `gamma_rel_rad` to [-180, 180] deg **before** resampling (`SERIES_FIELDS`, replay.py 123, the
  converter `wrapped_deg`), so on a fall-back run (silo_failed: 1.590 rad rising to 4.673 rad
  falling, test line 500) two neighbouring samples can sit either side of +/-180 deg and `valAt`
  interpolates through 0 deg between them. For the readout that is one wrong value in a 0.1 s
  window; for a drawn rocket it would be a flip. The scene should carry the attitude unwrapped,
  rotate by the interpolated value directly, and wrap only the number shown in the HUD.

---

## 6. Accessibility and robustness to keep, and the tests that pin the template

### 6.1 In the page today

| Property | Where | Note |
|---|---|---|
| ASCII-only source | whole file (0 non-ASCII bytes) | non-ASCII output comes from JavaScript escapes (`—`, `−`, `°`) and from the JSON's `\uXXXX` escapes (`ensure_ascii=True`). The only HTML entities are the five inside `esc` (226). |
| `<meta charset="utf-8">` | 4 | asserted by the test at 285 |
| `lang="en"`, viewport | 2, 5 | |
| Strict JSON | `embed_json` | no NaN or Infinity, `<` escaped |
| Canvas alternatives | 163, 172, 177-179 | `role="img"` with an `aria-label` on five canvases; `#ticks` is `aria-hidden` (144). **No canvas has fallback text inside the element.** The numbers are also in the DOM: telemetry cards, results table. |
| Labelled regions and controls | 139-189 | every `section` has an `aria-label`; the scrubber has one (145); the rate select has a `<label for>` (147); Play's `aria-label` follows its state (530); chips are `button`s with `aria-pressed` in a `role="group"` (157, 555-559) |
| Clock | 142 | `aria-live="off"`, so a screen reader is not flooded |
| Focus ring | 69 | 2 px `--focus` outline on button, select, input, chip |
| Keyboard | 547-550 | Space toggles play; native controls otherwise |
| Reduced motion | 128, 214, 582 | no auto-start |
| Escaping | 225-227 | every data string put in `innerHTML` goes through `esc`; other text through `textContent` |
| Not by colour alone | 82, 333 | a yardstick run is dashed as well as coloured |
| Small screens | 109, 118-127 | the table scrolls sideways; one column below 900 px |
| Contrast | 1.2 above | the template's `--ink-3` and light `--caution` fail 4.5:1; the site's values pass |

### 6.2 Tests in `tests/test_replay.py` that pin the template and the page

- `test_page_embeds_every_run_and_event_as_strict_json` (278-316): the page is written to
  `tmp_path` and the results tree is unchanged (read-only, 280-282);
  `page.startswith("<!doctype html>")` (284); `'<meta charset="utf-8">' in page` (285);
  `page.isascii()` (286); the data block is found by the regex
  `<script type="application/json" id="replay-data">(.*?)</script>` and parsed with
  `parse_constant` raising on NaN (269-275); every run and event present; series lengths equal
  (294); NaN and Infinity metrics become null (296-297); shaft q is null (299-300);
  `"pitch_deg" not in silo` (311).
- `test_embedded_json_cannot_close_its_script_and_rejects_nan` (360-365): for `"</script><b>"`
  and `"<!--<script>"`, `"<" not in text and json.loads(text) == {"s": value}`;
  `embed_json({"x": math.nan})` raises `ValueError`.
- `test_template_ships_as_package_data` (368-371):

      template = replay.load_template()
      assert template.count(replay.REPLAY_DATA_TOKEN) == 1
      assert template.isascii()

  It reads through `importlib.resources`, so it covers the editable install only (phase 5.8
  item 4).
- `test_template_shows_every_run_and_the_flight_peak_g` (628-633):

      template = replay.load_template()
      assert "const visible = new Set(runs.map(r => r.key));" in template
      assert "r.peak_g_flight" in template and "META.downrange_note" in template
      assert "Speed and path angle are relative to the Earth" in template
      assert "rotating Earth" not in template  # generated from the run data

- `test_inline_script_is_valid_javascript` (665-682), skipped when `shutil.which("node")` is
  None: renders a page from the synthetic directory, takes `re.findall(r"<script>(.*?)</script>",
  page, re.S)`, asserts exactly one, writes it to `tmp_path / "inline.js"` and runs
  `[NODE, "--check", str(js)]` with `timeout=60`, asserting return code 0. Node is installed here
  (`/c/nvm4w/nodejs/node`, v24.11.1). It checks syntax only; no test runs the page's code.
- Output-path tests: 374-390, 393-399, 612-625. CLI refusals: 402-423, 636-662.
- The fixture is synthetic (`_make_run_dir`, 183-258; rows every 0.5 s from -2 s to 60 s; columns
  `[*replay.REPLAY_COLUMNS, "stage"]`, line 40), so no test needs a simulation or the CSVs.

The scene template's tests can follow the same five patterns (doctype, charset, ASCII; strict JSON
through its own data-block id; token count and ASCII of the template; a few pinned strings;
`node --check` on the rendered page), plus the helper pin of section 7.

---

## 7. Recommendation: a deliberate copy guarded by a pin test

### 7.1 What a shared fragment would take

The eight helpers are not one block. They sit in three places inside one closure:
230-255 (`readPalette`, `idxAt`, `valAt`, `phaseAt`), 263-271 (`setupCanvas`) and 509-533
(`currentRate`, `tick`, `setPlaying`), with page-specific code between and around them. They are
not modules: they read and write the closure's variables (`tNow`, `playing`, `lastFrame`, `PAL`,
`runs`, `T_MIN`, `T_MAX`, `draw`), so a fragment file cannot be parsed or tested on its own.
The template's own section comments do bound two contiguous regions, "helpers" (224-340) and
"playback" (508-533), but the first also holds `axes` (with the clipped tick label that
`site/build.py` patches), `qOr` ("no air", where the scene wants a dash) and the palette key list.

A fragment injected at render time would mean: new files under `templates/` (shipped by
`uv_build` with the rest of `src/launchsim`); two or three new tokens in `replay.html`; the
fragments substituted before the data token, never after it (data inserted first could contain a
fragment token); and `replay.load_template()` returning the composed text, because the tests at
368-371 and 628-633 assert on its return value and `render_page` counts the data token in it.
To keep the reference page byte-identical the composition must reproduce today's 32,008 template
bytes exactly (sha256 `1fa6eba6...6990`), including indentation and the absence of any marker
comment. That is possible but it edits `replay.html` and `replay.py`'s render path during the
phase whose first gate is that this page does not change, and exit criterion 10 allows only two
named replay changes after A1 (the drive-caveat sentence and the contrast tokens). It buys the
removal of 60 duplicated lines.

### 7.2 Recommended: copy, and pin

- `templates/scene.html` copies the eight functions verbatim and keeps the closure names and the
  ids `play` and `rate` (section 1.6). `replay.html` and `replay.py`'s rendering are not touched
  by the scene work at any step, so the byte-identical gate cannot be affected by it.
- A fast test in `tests/test_scene.py` pins them:

      PINNED_HELPERS = ("readPalette", "idxAt", "valAt", "phaseAt", "setupCanvas",
                        "currentRate", "tick", "setPlaying")

  For each name, extract the function's source from `replay.load_template()` and from the scene's
  template, assert exactly one match in each and that the two texts are equal. Extraction rule
  proved on `replay.html` (`s04_pin_out.txt`): a one-line function is the single line
  `^  function <name>\(.*\}$`; otherwise the text from `^  function <name>\(` to the first line
  that is exactly two spaces and `}`. Try the one-line form first: a multi-line pattern tried
  first on a one-line function (`css`, `clockText`, `signedKg`, `niceMax`, `swatch`) runs on into
  the next function (it returned 7, 12, 11, 27 and 29 lines for those five). The eight pinned
  functions are all multi-line and each extracts to its own lines (5, 7, 8, 6, 9, 7, 10, 8).
- A helper the scene needs different (extra palette keys, a dash for "no air", the label clamps)
  is a new function beside the pinned ones (`readScenePalette`, `stepAt`), or is left off the
  list with a comment saying why. The pinned list is the stated contract between the two pages.
- A fix to a pinned helper is then made in both templates in one change; for the replay page that
  is a byte change and is logged as one of the deliberate changes after A1's gate.
- Optional tripwire: a test that the template file's sha256 is the recorded one makes every edit
  of `replay.html` in SP2 a visible, deliberate act without needing the results CSVs. The
  reference page is the template plus the JSON, so the two together cover the gate.
- The scene's `<style>` comment must carry its own marker (for example "Written by launchsim
  scene") and must not contain "Written by launchsim replay", or `site/build.py` would frame a
  gallery copy as a replay page and run the JavaScript text patches over it.
- Keep the app page from becoming a third copy: serve the rendered scene page from the app and
  show it in an `<iframe>` (same origin on 127.0.0.1). The `data-theme` observer the copy
  inherits (line 578) lets the app page pass its theme to the frame by setting the attribute on
  the frame's `<html>`.

---

## 8. Statements of the phase file that HEAD contradicts, and gaps

1. **`replay.py` line numbers.** Section 6 heads the table "replay.py (1,246 lines)" and sections
   5.2, 5.3 and 5.8 cite its lines. At HEAD the file has 1,244 lines and every definition after
   `offload_note` (322) sits two lines higher: `read_series` 365 (phase: 367), `_finite` 383
   (385), `replay_grid` 394 (396), `defined_mask` 405 (407), `series_values` 415 (417),
   `run_series` 430 (432), `run_events` 445 (447), `push_accel_g` 519 (521), `assist_text` 529
   (531), `calibration_caveat` 662 (664), `drive_caveat` 734 with the stale sentence at 761 (736,
   763), `caveats` 843 (845), `run_record` 980-1060 (982-1062), `source_text` 1063 (1065),
   `replay_data` 1105 (1107), `embed_json` 1166 (1168), `load_template` 1174 (1176),
   `render_page` 1180 (1182), `results_ancestors` 1188 (1190), `protected_tree` 1197 (1199),
   `default_replay_path` 1209 (1211), `check_replay_out` 1222 (1224), `write_replay_page` 1237
   (1239); the private calls are `plots._results_tree` at 1067 and 1203 and `plots._is_inside` at
   1204 (phase: 1069, 1205, 1206). The header of the phase file expects this re-check.
   `plots.py` moved too (`ANIMATION_MAX_RUNS` 324, `RESULTS_TREE_NAME` 347, `CALIBRATION_RECORDS`
   507, `CALIBRATION_BAND` 521, `ANIMATION_COLUMNS` 613, `animation_run_names` 645).
2. **Which brand file the header mark is (5.10, R18).** The phase file proposes inlining "the
   mark" with a test that it matches `assets/brand/favicon.svg`. The site's header mark is
   `logo-mark.svg` (`site/examples/index.html` 215, `replay-frame.html`), and `favicon.svg` is
   the simplified tab icon (brand README line 7). They are different drawings (1,540 and 1,111
   bytes; three coil rows and a trail against two rows).
3. **Token differences (5.10).** The phase file lists `--ink-3`, the light `--caution` and
   `--accent-ink`. The site's set also adds `--link` and `--code-bg` and sets `color-scheme:
   light` on `:root` (site.css 33-34, 39).
4. **Site fixes of replay output (5.8 item 5, R17).** The phase file names only the drive-caveat
   sentence. `site/build.py` at HEAD holds five `REPLAY_TEXT_FIXES` (one of them a grammar fix
   for `closeup_notes`, replay.py 900; three of them JavaScript patches of template lines
   289, 379 and 436) and eleven `REPLAY_PAGE_FIXES` entries for the two offload pages, which record
   further wording faults of `replay.py` for offload runs (`ROLE_LABELS` 964-968 labels a paired
   pad "(offload)"; `comparison_caveats` 831-839 says a paired pad measures propellant saved;
   `structure_caveat` 698-700 calls an offloaded stack "fully fuelled"; `offload_note` 348-353
   rounds to 41.3 t and 10.0%; the subtitle 1099-1102 names a baseline the page may not show).
   TODO.md tracks only the caveat sentence (KI-029). A scene that reuses these Python text
   helpers inherits each fault.
5. **Reference page (section 7).** Consistent, not a contradiction: at HEAD the reference page is
   247,949 bytes with the sha256 the phase file records for b3150c1, so SP1's last change to
   `replay.py` left it unchanged.
6. **The task text for this survey** lists "canvas fallback text" among what the replay page
   already has. It has none (section 6.1).
7. **.gitignore.** No `!docs/demos/**` line was added at SP1's close (22 lines at HEAD);
   `docs/demos/SP1/pad_vs_offloaded_silo.html` avoids the ignored suffix by its name. The pattern
   check of 5.8 item 4 still applies to a `*_scene.html` default.

---

## 9. Consequences for the SP2 design

1. Use the site's token values in `scene.html` and `app.html`, in the three-block pattern, and add
   `color-scheme: light` to `:root`. Canvas text in `--ink-3` then passes 4.5:1 in both themes.
2. Copy the eight helpers verbatim and pin them with the test of 7.2; do not touch `replay.html`
   for the scene.
3. Carry steps as two samples at the event time. `idxAt` and `valAt` handle repeated times as
   measured, so the event-aligned grid of 5.3 needs no new interpolation code on the page; the
   loader must then keep both rows of a phase boundary (replay's `read_series` keeps the last
   only) and must not pass the grid through `np.unique`. Use the index of `idxAt` directly for
   step fields (`phase`, `stage`, thrust on), as `phaseAt` does.
4. Draw every frame from `tNow` alone (no state carried between frames), as the replay does;
   then scrubbing, the uncapped frame interval of `tick`, and separation animations all stay
   consistent.
5. Label events by name and stage; map all sixteen names of 5.4. Carry the attitude unwrapped
   and wrap only the displayed number (section 5).
6. Encode `phase` (and `stage`) compactly if size matters: `phase` is 18% of a run record as one
   string per sample. If `phaseAt` is to stay pinned, the per-sample array stays.
7. Give the scene template its own marker and give `site/build.py` a frame rule for it (5.9); the
   existing frame's token override becomes unnecessary for a page that already has the site's
   values.
8. Keep the page ASCII with JavaScript escapes, `<meta charset>`, strict JSON through
   `embed_json` (reuse the function; it is already valid as an HTTP JSON body), `role="img"` and
   `aria-label` on canvases, and add fallback text inside each canvas, which the replay lacks.
9. The clipped-label and floor-label fixes that `site/build.py` patches into replay pages belong
   in the scene's own drawing code from the start (`axes`, the timeline labels).
10. For the offline answer to Q2, omit the three font links; the stacks and the
    `document.fonts.ready` redraw already cope.
11. Brand in the package: the tab icon from `favicon.svg` and the header mark from
    `logo-mark.svg`, each as package data or an inline copy with an equality test against
    `assets/brand/`; in a data URI the 12 `#` characters must be written `%23`; two inline copies
    of one SVG in a page would repeat its ids (`fc`, `fr`; `mc`, `mr`, `mt`). The name beside the
    mark is plain text with `--run-1` hyphens, as on the site.
12. Do not reuse replay's text helpers for offload runs without fixing the faults listed in 8.4,
    and never emit `REPLAY_STALE_TEXT`: a framed gallery page that still holds it fails the site
    build.
