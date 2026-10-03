"""Write the launch-assist-sim brand SVGs: logo lockups, square mark, favicon, banners, social card.

The wordmark is drawn from hand-built monoline glyphs (stroked centrelines in the spirit of
Barlow Condensed), so no SVG needs a font for it. Taglines and captions use a system font stack.
Colours are the :root tokens of src/launchsim/templates/replay.html (light and dark), except
ink3 (caption grey), which uses the site's contrast-checked values (site/assets/site.css):
#626c71 / #87919a reach 4.5:1 on every banner panel, where the template's #7b858a / #78828a
reach only 3.4:1 on the light banner and 4.4:1 on the dark banner panel.

Run from the repository root:  python assets/brand/build_brand.py
PNG renders:                   python assets/brand/render_png.py
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

OUT = Path(__file__).resolve().parent

# replay.html :root tokens (ink3: the site's AA values, see the module docstring)
LIGHT = {
    "bg": "#f1f2ee",
    "panel": "#fbfbf8",
    "ink": "#1c2226",
    "ink2": "#4c565c",
    "ink3": "#626c71",
    "rule": "#d6d9d1",
    "grid": "#e3e5de",
    "ground": "#8a7a62",
    "run0": "#2d5f8f",
    "run1": "#c2521a",
}
DARK = {
    "bg": "#111518",
    "panel": "#171c20",
    "ink": "#e3e7e4",
    "ink2": "#aab3b3",
    "ink3": "#87919a",
    "rule": "#2b3238",
    "grid": "#222a2f",
    "ground": "#b09a78",
    "run0": "#7fb0e0",
    "run1": "#f08a4b",
}

FONT_BODY = "'IBM Plex Sans','Segoe UI','Helvetica Neue',Arial,sans-serif"
FONT_MONO = "'IBM Plex Mono','Cascadia Mono',Consolas,'SFMono-Regular',Menlo,monospace"
TAGLINE = "How much rocket propellant can a ground-powered push replace?"
WORD = "launch-assist-sim"
REPO = "khoks/RocketLaunchOptimizationSimulator"

K = 0.62  # corner Bezier factor: 0.5523 draws a circle; larger gives squarer, DIN-like shoulders

Point = tuple[float, float]
UP: Point = (0, -1)
DN: Point = (0, 1)
LT: Point = (-1, 0)
RT: Point = (1, 0)


def num(v: float) -> str:
    """Format a coordinate with at most two decimals."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


class Pen:
    """Absolute M/L/C path builder."""

    def __init__(self) -> None:
        self.cmds: list[tuple[str, list[Point]]] = []
        self.cur: Point = (0.0, 0.0)

    def move(self, x: float, y: float) -> None:
        self.cmds.append(("M", [(x, y)]))
        self.cur = (x, y)

    def line(self, x: float, y: float) -> None:
        self.cmds.append(("L", [(x, y)]))
        self.cur = (x, y)

    def curve(self, p1: Point, p2: Point, p: Point) -> None:
        self.cmds.append(("C", [p1, p2, p]))
        self.cur = p

    def corner(self, x: float, y: float, d0: Point, d1: Point) -> None:
        """Quarter corner from the current point to (x, y); d0, d1 = start and end tangents."""
        x0, y0 = self.cur
        rx, ry = abs(x - x0), abs(y - y0)
        c1 = (x0 + K * rx * d0[0], y0 + K * ry * d0[1])
        c2 = (x - K * rx * d1[0], y - K * ry * d1[1])
        self.curve(c1, c2, (x, y))

    def mapped(self, tf: Callable[[float, float], Point]) -> Pen:
        out = Pen()
        out.cmds = [(c, [tf(x, y) for x, y in pts]) for c, pts in self.cmds]
        return out

    def d(self, dx: float = 0.0) -> str:
        return "".join(
            c + " ".join(f"{num(x + dx)} {num(y)}" for x, y in pts) for c, pts in self.cmds
        )


class Glyphs:
    """Monoline lowercase for the wordmark. Origin at the left ink edge, baseline y = 0, y down."""

    def __init__(self, x_height: float, ascender: float, stroke: float) -> None:
        self.X, self.A, self.S = x_height, ascender, stroke
        self.h = stroke / 2
        self.yT, self.yB = -x_height + stroke / 2, -stroke / 2  # centreline top and bottom
        self.k = x_height / 26.0  # widths below are tuned at x-height 26

    def _arch(self, p: Pen, xl: float, xr: float) -> None:
        r = (xr - xl) / 2
        p.move(xl, self.yT + r)
        p.corner(xl + r, self.yT, UP, RT)
        p.corner(xr, self.yT + r, RT, DN)
        p.line(xr, 0)

    def n(self, stem_top: float | None = None) -> tuple[list[Pen], float]:
        w, p = 19 * self.k, Pen()
        p.move(self.h, 0)
        p.line(self.h, -(stem_top or self.X))
        self._arch(p, self.h, w - self.h)
        return [p], w

    def h_(self) -> tuple[list[Pen], float]:
        return self.n(stem_top=self.A)

    def u(self) -> tuple[list[Pen], float]:
        (p,), w = self.n()
        x_height = self.X
        return [p.mapped(lambda x, y: (w - x, -x_height - y))], w  # n turned 180 degrees

    def m(self) -> tuple[list[Pen], float]:
        w, p, q = 30.4 * self.k, Pen(), Pen()
        p.move(self.h, 0)
        p.line(self.h, -self.X)
        self._arch(p, self.h, w / 2)
        self._arch(q, w / 2, w - self.h)
        return [p, q], w

    def a(self) -> tuple[list[Pen], float]:
        w, p, s = 18.4 * self.k, Pen(), Pen()
        xl, xr = self.h, w - self.h
        r = (xr - xl) / 2
        p.move(xr, self.yT + r)
        p.corner(xl + r, self.yT, UP, LT)
        p.corner(xl, self.yT + r, LT, DN)
        p.line(xl, self.yB - r)
        p.corner(xl + r, self.yB, DN, RT)
        p.corner(xr, self.yB - r, RT, UP)
        s.move(xr, -self.X)
        s.line(xr, 0)
        return [p, s], w

    def c(self) -> tuple[list[Pen], float]:
        w, p = 16.6 * self.k, Pen()
        xl, xr = self.h, w - self.h
        r = (xr - xl) / 2
        p.move(xr, self.yT + r)
        p.corner(xl + r, self.yT, UP, LT)
        p.corner(xl, self.yT + r, LT, DN)
        p.line(xl, self.yB - r)
        p.corner(xl + r, self.yB, DN, RT)
        p.corner(xr, self.yB - r, RT, UP)
        return [p], w

    def s(self) -> tuple[list[Pen], float]:
        w, p = 15.6 * self.k, Pen()
        xl, xr = self.h, w - self.h
        r = (xr - xl) / 2
        y1, y2 = self.yT + r, self.yB - r  # top-loop and bottom-loop equators
        c = 0.62 * (y2 - y1) / 2  # spine handle length
        trim = 0.6 * self.k  # terminals stop a little short of the equators
        p.move(xr, y1 - trim)
        p.corner(xl + r, self.yT, UP, LT)
        p.corner(xl, y1, LT, DN)
        p.curve((xl, y1 + c), (xr, y2 - c), (xr, y2))
        p.corner(xl + r, self.yB, DN, LT)
        p.corner(xl, y2 + trim, LT, UP)
        return [p], w

    def t(self) -> tuple[list[Pen], float]:
        k, p, bar = self.k, Pen(), Pen()
        xs, rh = 2.4 * k + self.h, 3.8 * k
        p.move(xs, -(self.A - 4.5 * k))
        p.line(xs, self.yB - rh)
        p.corner(xs + rh, self.yB, DN, RT)
        p.line(xs + rh + 2.4 * k, self.yB)
        bar.move(0, self.yT)
        bar.line(xs + self.h + 3.6 * k, self.yT)
        return [p, bar], max(xs + rh + 2.4 * k, xs + self.h + 3.6 * k)

    def stem(self, top: float) -> Pen:
        p = Pen()
        p.move(self.h, -top)
        p.line(self.h, 0)
        return p

    def ell(self) -> tuple[list[Pen], float]:
        return [self.stem(self.A)], self.S

    def i(self) -> tuple[list[Pen], float]:
        dot, gap = Pen(), 4.4 * self.k
        dot.move(self.h, -self.X - gap - self.S)
        dot.line(self.h, -self.X - gap)
        return [self.stem(self.X), dot], self.S

    def hyphen(self) -> tuple[list[Pen], float]:
        w, p = 10.6 * self.k, Pen()
        p.move(0, -self.X * 0.46)
        p.line(w, -self.X * 0.46)
        return [p], w


# Side shapes for spacing: S = straight stem, O = round, D = open or diagonal.
SIDES = {
    "l": "SS",
    "a": "OS",
    "u": "SS",
    "n": "SS",
    "c": "OD",
    "h": "SS",
    "-": "DD",
    "s": "DD",
    "i": "SS",
    "t": "DD",
    "m": "SS",
}
GAP = {"SS": 4.7, "SO": 3.9, "OS": 3.9, "OO": 3.4}
GAP_OPEN = 3.4


def wordmark(x_height: float, stroke: float, ascender: float) -> tuple[str, str, float]:
    """Return (ink path d, accent path d, width) of WORD; hyphens go to the accent path."""
    g = Glyphs(x_height, ascender, stroke)
    table = {
        "l": g.ell,
        "a": g.a,
        "u": g.u,
        "n": g.n,
        "c": g.c,
        "h": g.h_,
        "-": g.hyphen,
        "s": g.s,
        "i": g.i,
        "t": g.t,
        "m": g.m,
    }
    x, ink, acc = 0.0, [], []
    for idx, ch in enumerate(WORD):
        pens, w = table[ch]()
        (acc if ch == "-" else ink).extend(p.d(dx=x) for p in pens)
        x += w
        if idx + 1 < len(WORD):
            pair = SIDES[ch][1] + SIDES[WORD[idx + 1]][0]
            x += GAP.get(pair, GAP_OPEN) * g.k
    return "".join(ink), "".join(acc), x


def wordmark_group(
    x_height: float, ink: str, acc: str, tx: float, ty: float, css: bool = False
) -> tuple[str, float]:
    """SVG group with the wordmark at (tx, ty) = (left edge, baseline). css=True uses classes."""
    stroke, ascender = 0.215 * x_height, 1.423 * x_height
    ink_d, acc_d, w = wordmark(x_height, stroke, ascender)
    a_ink = 'class="wm-ink"' if css else f'stroke="{ink}"'
    a_acc = 'class="wm-acc"' if css else f'stroke="{acc}"'
    return (
        f'<g transform="translate({num(tx)} {num(ty)})" fill="none" '
        f'stroke-width="{num(stroke)}" stroke-linecap="butt">'
        f'<path {a_ink} d="{ink_d}"/><path {a_acc} d="{acc_d}"/></g>'
    ), w


def mark_body(uid: str, simple: bool = False) -> str:
    """Inner SVG of the square mark on a 64 x 64 grid.

    An elevation section: the rocket rises out of a vertical shaft whose walls carry linear-motor
    coil sections (orange), brightest at the level the rocket has just left (a travelling wave),
    with a short motion trail below the tail. simple=True drops the fine detail (favicon).
    A grey rim outlines the earth half, so the tile keeps its silhouette on dark pages
    (the earth fill alone is about 1.1:1 against GitHub's and the site's dark panels).
    """
    sky, earth, surface, shaft = "#2d5f8f", "#1c2226", "#b09a78", "#2b3238"
    coil, rocket, shade, band = "#f08a4b", "#fbfbf8", "#dfe4e1", "#1c2226"
    rim = "#4c565c"  # ink-2 (light); half of the stroke falls inside the clipped tile
    gy, sx0, sx1 = 41.0, 25.0, 39.0  # ground surface, shaft walls
    tail = 47.0 if simple else 46.0
    body = f"M28 18.5C28 12 30.6 7.4 32 5.5C33.4 7.4 36 12 36 18.5V{num(tail)}H28Z"
    parts = [
        f'<clipPath id="{uid}c"><rect width="64" height="64" rx="12"/></clipPath>',
        f'<clipPath id="{uid}r"><path d="{body}"/></clipPath>',
    ]
    if not simple:
        parts.append(
            f'<linearGradient id="{uid}t" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{rocket}" stop-opacity=".5"/>'
            f'<stop offset="1" stop-color="{rocket}" stop-opacity="0"/></linearGradient>'
        )
    parts += [
        f'<g clip-path="url(#{uid}c)">',
        f'<rect width="64" height="{num(gy)}" fill="{sky}"/>',
        f'<rect y="{num(gy)}" width="64" height="{num(64 - gy)}" fill="{earth}"/>',
        f'<rect x="{num(sx0)}" y="{num(gy)}" width="{num(sx1 - sx0)}" '
        f'height="{num(64 - gy)}" fill="{shaft}"/>',
        f'<path d="M0 {num(gy + 1.25)}H{num(sx0)}M{num(sx1)} {num(gy + 1.25)}H64" '
        f'stroke="{surface}" stroke-width="2.5"/>',
    ]
    if not simple:
        parts.append(
            f'<path d="M{num(sx0 + 0.6)} {num(gy)}V64M{num(sx1 - 0.6)} {num(gy)}V64" '
            f'stroke="{surface}" stroke-opacity=".55" stroke-width="1.2"/>'
        )
    levels = [(48.5, 1.0), (56.5, 0.5)] if simple else [(47.5, 1.0), (53.5, 0.62), (59.5, 0.32)]
    coil_h = 3.6 if simple else 2.8
    for y, op in levels:
        parts.append(
            f'<path d="M{num(sx0 - 5.5)} {num(y)}h5.5M{num(sx1)} {num(y)}h5.5" stroke="{coil}" '
            f'stroke-opacity="{op}" stroke-width="{coil_h}"/>'
        )
    if not simple:
        parts.append(f'<rect x="28" y="{num(tail)}" width="8" height="15" fill="url(#{uid}t)"/>')
    parts += [
        f'<path d="{body}" fill="{rocket}"/>',
        f'<rect x="33.6" y="4" width="3" height="{num(tail - 3)}" fill="{shade}" '
        f'clip-path="url(#{uid}r)"/>',
        f'<rect x="28" y="27" width="8" height="2.2" fill="{band}"/>',
        f'<path d="M0 {num(gy)}V52A12 12 0 0 0 12 64H52A12 12 0 0 0 64 52V{num(gy)}" '
        f'fill="none" stroke="{rim}" stroke-width="{5 if simple else 3}"/>',
        "</g>",
    ]
    return "".join(parts)


def svg(w: float, h: float, body: str, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(w)}" height="{num(h)}" '
        f'viewBox="0 0 {num(w)} {num(h)}" role="img" aria-label="{title}">'
        f"<title>{title}</title>{body}</svg>\n"
    )


def logo(variant: str) -> str:
    """Horizontal lockup. variant: 'auto' (follows prefers-color-scheme), 'light' or 'dark'."""
    pal = DARK if variant == "dark" else LIGHT
    css = variant == "auto"
    wm, w = wordmark_group(26.0, pal["ink"], pal["run1"], 82.0, 47.0, css=css)
    style = ""
    if css:
        style = (
            f"<style>.wm-ink{{stroke:{LIGHT['ink']}}}.wm-acc{{stroke:{LIGHT['run1']}}}"
            f"@media (prefers-color-scheme:dark){{.wm-ink{{stroke:{DARK['ink']}}}"
            f".wm-acc{{stroke:{DARK['run1']}}}}}</style>"
        )
    return svg(82.0 + w + 2, 64, style + mark_body("m") + wm, WORD)


def scene(
    cx: float,
    gy: float,
    s: float,
    pal: dict[str, str],
    x_left: float,
    x_right: float,
    rise: float,
    end: Point,
    bottom: float,
    uid: str,
) -> str:
    """Line art: ground line, silo section with coils, dashed ascent bending downrange (right)."""
    w = 26 * s
    sx, g = cx - w / 2, pal["ground"]
    fade = f"{uid}w"  # the shaft walls fade out towards `bottom`
    parts = [
        f'<linearGradient id="{fade}" gradientUnits="userSpaceOnUse" x1="0" y1="{num(gy)}" '
        f'x2="0" y2="{num(bottom)}"><stop offset="0" stop-color="{g}" stop-opacity=".5"/>'
        f'<stop offset="1" stop-color="{g}" stop-opacity="0"/></linearGradient>',
        f'<path d="M{num(x_left)} {num(gy)}H{num(sx)}M{num(sx + w)} {num(gy)}H{num(x_right)}" '
        f'stroke="{g}" stroke-opacity=".7" stroke-width="{num(2 * s)}"/>',
        f'<path d="M{num(sx)} {num(gy)}V{num(bottom)}M{num(sx + w)} {num(gy)}V{num(bottom)}" '
        f'stroke="url(#{fade})" stroke-width="{num(2 * s)}"/>',
    ]
    for i, op in enumerate((0.95, 0.6, 0.32)):
        y = gy + (14 + 16 * i) * s
        if y > bottom - 4:
            break
        parts.append(
            f'<path d="M{num(sx - 12 * s)} {num(y)}h{num(11 * s)}'
            f'M{num(sx + w + s)} {num(y)}h{num(11 * s)}" stroke="{pal["run1"]}" '
            f'stroke-opacity="{op}" stroke-width="{num(5 * s)}"/>'
        )
    ex, ey = end
    y1 = gy - rise
    c1 = (cx, y1 - 0.45 * (y1 - ey))
    c2 = (cx + 0.25 * (ex - cx), ey + 0.12 * (y1 - ey))
    path = (
        f"M{num(cx)} {num(gy - 8 * s)}V{num(y1)}"
        f"C{num(c1[0])} {num(c1[1])} {num(c2[0])} {num(c2[1])} {num(ex)} {num(ey)}"
    )
    parts.append(
        f'<path d="{path}" fill="none" stroke="{pal["run0"]}" stroke-opacity=".9" '
        f'stroke-width="{num(2.4 * s)}" stroke-dasharray="{num(9 * s)} {num(7 * s)}"/>'
    )
    return "".join(parts)


def grid_path(w: int, h: int, step: int = 80) -> str:
    xs = [f"M{x} 0V{h}" for x in range(step, w, step)]
    ys = [f"M0 {y}H{w}" for y in range(step, h, step)]
    return "".join(xs + ys)


def text(
    x: float, y: float, fill: str, family: str, size: float, body: str, extra: str = ""
) -> str:
    return (
        f'<text x="{num(x)}" y="{num(y)}" fill="{fill}" font-family="{family}" '
        f'font-size="{num(size)}"{extra}>{body}</text>'
    )


def banner(variant: str) -> str:
    """README banner, 1280 x 320, on an explicit panel so it reads on light and dark pages."""
    w, h = 1280, 320
    pal = DARK if variant == "dark" else LIGHT
    msize, mx = 152, 64
    my = (h - msize) / 2
    tx, base = mx + msize + 40, 184.0
    ground = my + 41 * msize / 64  # the scene's ground line continues the mark's horizon
    wm, _ = wordmark_group(52.0, pal["ink"], pal["run1"], tx, base)
    # dark: the raised panel tone stands off GitHub's dark page; light: the vellum page tone
    panel = pal["panel"] if variant == "dark" else pal["bg"]
    body = (
        f'<defs><clipPath id="bc"><rect width="{w}" height="{h}" rx="18"/></clipPath></defs>'
        f'<g clip-path="url(#bc)"><rect width="{w}" height="{h}" fill="{panel}"/>'
        f'<path d="{grid_path(w, h)}" stroke="{pal["grid"]}" stroke-width="1"/>'
        + scene(1188, ground, 0.85, pal, 1072, w, 52, (w + 12, 18), h + 40, "b")
        + f'</g><rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="17.5" fill="none" '
        f'stroke="{pal["rule"]}"/>'
        f'<g transform="translate({mx} {num(my)}) scale({num(msize / 64)})">'
        f"{mark_body('bm')}</g>"
        + wm
        + text(tx + 2, base + 52, pal["ink2"], FONT_BODY, 26, TAGLINE, ' font-weight="500"')
        + text(
            tx + 2,
            base - 96,
            pal["ink3"],
            FONT_MONO,
            17,
            "RESEARCH SIMULATOR · GROUND-POWERED LAUNCH ASSIST",
            ' letter-spacing="2.2"',
        )
    )
    return svg(w, h, body, WORD)


def banner_compact() -> str:
    """Phone-width banner, 640 x 380, dark panel: the wide banner's caption and tagline would
    shrink to 4-6 px at 360 px wide, so here they are stacked and set larger."""
    w, h = 640, 380
    pal = DARK
    msize, mx, my = 112, 40, 40
    tx, base = 40, 252.0
    wm, _ = wordmark_group(46.0, pal["ink"], pal["run1"], tx, base)
    cap, med = ' letter-spacing="2.2"', ' font-weight="500"'
    kx = mx + msize + 26
    line1, line2 = "How much rocket propellant can a", "ground-powered push replace?"
    body = (
        f'<defs><clipPath id="cc"><rect width="{w}" height="{h}" rx="18"/></clipPath></defs>'
        f'<g clip-path="url(#cc)"><rect width="{w}" height="{h}" fill="{pal["panel"]}"/>'
        f'<path d="{grid_path(w, h)}" stroke="{pal["grid"]}" stroke-width="1"/></g>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="17.5" fill="none" '
        f'stroke="{pal["rule"]}"/>'
        f'<g transform="translate({mx} {my}) scale({num(msize / 64)})">{mark_body("cm")}</g>'
        + text(kx, my + 46, pal["ink3"], FONT_MONO, 21, "RESEARCH SIMULATOR", cap)
        + text(kx, my + 78, pal["ink3"], FONT_MONO, 21, "GROUND-POWERED LAUNCH ASSIST", cap)
        + wm
        + text(tx + 2, base + 52, pal["ink2"], FONT_BODY, 30, line1, med)
        + text(tx + 2, base + 92, pal["ink2"], FONT_BODY, 30, line2, med)
    )
    return svg(w, h, body, WORD)


def social() -> str:
    """Repository social preview, 1280 x 640 (GitHub keeps a 40 px safe border)."""
    w, h = 1280, 640
    pal = DARK
    msize, mx, my = 152, 88, 88
    tx, base = 88, 392.0
    ground = my + 41 * msize / 64
    wm, _ = wordmark_group(62.0, pal["ink"], pal["run1"], tx, base)
    cap = ' letter-spacing="2.6"'
    body = (
        f'<rect width="{w}" height="{h}" fill="{pal["bg"]}"/>'
        f'<path d="{grid_path(w, h)}" stroke="{pal["grid"]}" stroke-width="1"/>'
        + scene(1080, ground, 1.3, pal, 880, w, 70, (w + 16, 24), ground + 170, "s")
        + f'<g transform="translate({mx} {my}) scale({num(msize / 64)})">{mark_body("sm")}</g>'
        + text(mx + msize + 36, my + 68, pal["ink3"], FONT_MONO, 20, "RESEARCH SIMULATOR", cap)
        + text(
            mx + msize + 36,
            my + 100,
            pal["ink3"],
            FONT_MONO,
            20,
            "GROUND-POWERED LAUNCH ASSIST",
            cap,
        )
        + wm
        + text(tx + 2, base + 70, pal["ink2"], FONT_BODY, 35, TAGLINE, ' font-weight="500"')
        + text(tx + 2, h - 72, pal["run0"], FONT_MONO, 28, REPO)
        + text(
            w - 88,
            h - 72,
            pal["ink3"],
            FONT_MONO,
            18,
            "public to read · all rights reserved",
            ' text-anchor="end"',
        )
    )
    return svg(w, h, body, f"{WORD}: RocketLaunchOptimizationSimulator")


def main(out: Path = OUT) -> None:
    files = {
        "logo-mark.svg": svg(64, 64, mark_body("m"), WORD),
        "favicon.svg": svg(64, 64, mark_body("f", simple=True), WORD),
        "logo.svg": logo("auto"),
        "logo-light.svg": logo("light"),
        "logo-dark.svg": logo("dark"),
        "banner.svg": banner("dark"),
        "banner-light.svg": banner("light"),
        "banner-compact.svg": banner_compact(),
        "social-preview.svg": social(),
    }
    out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8", newline="\n")
        print(f"wrote {out / name} ({len(content.encode())} bytes)")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
