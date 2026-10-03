# Brand assets

The logo, mark, banner and social card for launch-assist-sim. They are covered by the repository [LICENSE](../../LICENSE): all rights reserved. The files are public to view, but you have no permission to copy, modify or reuse them.

## The mark

The mark is a cross-section of the concept. A rocket rises out of an underground silo. The shaft walls carry linear-motor (maglev) coil sections, drawn in orange. They are brightest at the level the rocket has just left, like a travelling wave, and a short motion trail fades below the tail. Above the ground line is sky. A grey rim outlines the earth half, so the tile keeps its shape on dark pages, where the dark earth fill alone would melt into the background. It is drawn on a 64 × 64 grid and still reads at 32 px. `favicon.svg` is a simpler version for 16 px.

The wordmark `launch-assist-sim` is built from hand-drawn monoline strokes in the spirit of Barlow Condensed, so the logo needs no font. The two hyphens use the coil orange.

## Files

| File | Use |
|---|---|
| `logo.svg` | Horizontal lockup (mark and wordmark). The wordmark switches colour with `prefers-color-scheme`. Use it only on pages whose theme also follows `prefers-color-scheme`. |
| `logo-light.svg`, `logo.png` | Lockup for light backgrounds (ink wordmark). The PNG is 3×, with a transparent background. |
| `logo-dark.svg`, `logo-dark.png` | Lockup for dark backgrounds (light wordmark). The PNG is 3×, with a transparent background. |
| `logo-mark.svg`, `logo-mark.png` | Square mark. The PNG is 512 px, for avatars, slides and `apple-touch-icon`. |
| `favicon.svg` | Simplified mark for browser tabs. |
| `banner.svg`, `banner.png` | README banner, 1280 × 320, on a dark panel that reads on GitHub's light and dark themes. The PNG is 2×. |
| `banner-light.svg` | The same banner on a light panel, for a `<picture>` light source. |
| `banner-compact.svg` | A 640 × 380 banner for phone widths, on the dark panel: the caption and tagline are stacked and set larger, because the wide banner's would shrink to a few pixels. The landing page swaps it in below 600 px. |
| `social-preview.svg`, `social-preview.png` | Repository social preview, 1280 × 640. Upload the PNG under Settings → General → Social preview. |

Banner in a README, following the GitHub theme:

```html
<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/brand/banner-light.svg">
  <img alt="launch-assist-sim: how much rocket propellant can a ground-powered push replace?" src="assets/brand/banner.svg" width="100%">
</picture>
```

## Palette

The colours are the tokens of `src/launchsim/templates/replay.html`, with contrast fixes for small text. The site, the deck, the gallery and the banner captions use a darker light `--ink-3` and a lighter dark `--ink-3` than the replay template (`#7b858a` / `#78828a`), so small grey text reaches the WCAG AA 4.5:1; the site's frame applies the same values to the replay pages. The site also darkens the light `--caution` (`#845a00`, the template has `#9a6a00`) and sets small orange text in `--accent-ink`.

| Role | Light | Dark |
|---|---|---|
| Page `--bg` | `#f1f2ee` | `#111518` |
| Panel `--panel` | `#fbfbf8` | `#171c20` |
| Ink `--ink` / `--ink-2` / `--ink-3` | `#1c2226` / `#4c565c` / `#626c71` | `#e3e7e4` / `#aab3b3` / `#87919a` |
| Rules and grid | `#d6d9d1` / `#e3e5de` | `#2b3238` / `#222a2f` |
| Ground `--ground` | `#8a7a62` | `#b09a78` |
| Steel blue `--run-0` (sky, trajectory) | `#2d5f8f` | `#7fb0e0` |
| Coil orange `--run-1` (coils, hyphens, the silo path) | `#c2521a` | `#f08a4b` |
| Orange for small text `--accent-ink` (site only: kickers, labels) | `#a8440f` | `#f08a4b` |
| Caution `--caution` / `--caution-bg` (site only: caveat panels) | `#845a00` / `#f6ecd2` | `#e0b653` / `#2c2513` |

The mark uses fixed colours on both themes: sky `#2d5f8f`, earth `#1c2226`, shaft `#2b3238`, surface `#b09a78`, coils `#f08a4b`, rocket `#fbfbf8` with shading `#dfe4e1`, and a rim `#4c565c` around the earth half.

## Typography

- Headings: Barlow Condensed.
- Body: IBM Plex Sans.
- Numbers and code: IBM Plex Mono.

All three are loaded from Google Fonts on the site. Inside the SVGs, the tagline and captions fall back to Segoe UI, Helvetica Neue or Arial, and to Cascadia Mono, Consolas or Menlo.

## Regenerate

```text
python assets/brand/build_brand.py   # writes every SVG in this folder
python assets/brand/render_png.py    # writes the PNGs with headless Edge or Chrome (needs Pillow and numpy)
```
