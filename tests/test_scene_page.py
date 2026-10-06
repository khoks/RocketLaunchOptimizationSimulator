"""The standalone scene page (SP2 step A3; design section 4.5): the template, the page
writer, the ``scene`` command and the page script's pure functions.

Fast tier. The data is one fixed-guidance flight pair of experiments/silo_screening_2d
.yaml (the pad and silo_failed, a 0.5 s sample step, rtol 1e-8, a 32-point max-Q scan; the
recipe of tests/test_scene.py with two flights), run once per module into a temporary
results root; results/ is never read.

Checked: the template ships as package data, is ASCII, holds the data token once and the
scene's own marker (never the replay page's); the rendered page is ASCII with strict JSON
in its data block and every '<' escaped; the seven helpers shared with replay.html are
byte-identical to its copies (D-SP2-21); no HTML sink takes anything but a literal; the
page makes no request (no URL, no network API, no link or src but data:, a meta
Content-Security-Policy whose script hash is the inline script's); the tab icon is the
brand favicon; the site's tokens are carried unchanged and every declared shape, outline
and text pair meets its contrast (3:1 shapes, 4.5:1 text) in both themes; node --check
of the script; ``parseHash`` on crafted input, the transform and camera functions
against display.screen_xy, running_extent_m and view_height_m, the carriage label's
placement and the caveat split, under node; the output rule of ``write_scene_page``
(default path, refusals) and the ``scene`` command.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from launchsim import cli, display, replay, run_data, scene, sim
from launchsim.config import resolve_experiment

REPO = Path(__file__).resolve().parents[1]
DISPLAY_DIR = REPO / "configs" / "display"
FAVICON = REPO / "assets" / "brand" / "favicon.svg"
SITE_CSS = REPO / "site" / "assets" / "site.css"
NODE = shutil.which("node")

FIXED_GAMMA_DEG = 20.0
FIXED_LTG = (0.756790, 2.19338e-3)
"""The pad's LTG pair at gamma* 20 deg (tests/test_planar_pipeline.py)."""
FIXTURE_SAMPLE_DT_S = 0.5
FIXTURE_RTOL = 1.0e-8
FIXTURE_DELTA_XTOL_RAD = 1.0e-8
FIXTURE_MAXQ_SCAN_POINTS = 32
"""The fixture's settings (tests/test_scene.py): these tests check the page, not the
integration or max-Q."""

PINNED_HELPERS = ("readPalette", "idxAt", "valAt", "phaseAt", "setupCanvas", "tick", "setPlaying")
"""The helpers the scene copies verbatim from replay.html (D-SP2-21; the scene has its own
currentRate)."""
REPLAY_MARKER = "Written by launchsim replay"
HTML_SINKS = (
    "innerHTML",
    "outerHTML",
    "insertAdjacentHTML",
    "document.write",
    # the newer HTML parsers
    "setHTMLUnsafe",
    "parseHTMLUnsafe",
    "createContextualFragment",
    "DOMParser",
    "srcdoc",
)
NETWORK_APIS = (
    "fetch(",
    "XMLHttpRequest",
    "WebSocket",
    "EventSource",
    "sendBeacon",
    "importScripts",
    "import(",
    "new Image",
    "window.open",
    # navigation (the meta CSP has no navigate-to) and element sources
    "location.assign",
    "location.replace",
    "location.href",
    "window.location =",
    "document.location",
    ".src =",
    ".href =",
    "Worker(",
    "RTCPeerConnection",
    'createElement("script',
    'createElement("img',
    'createElement("iframe',
    'createElement("link',
    "@import",
)
CSP_DIRECTIVES = {
    "default-src": ["'none'"],
    "style-src": ["'unsafe-inline'"],
    "img-src": ["data:"],
    "base-uri": ["'none'"],
    "form-action": ["'none'"],
}
"""Every directive of the page's meta CSP but script-src (a sha256 of the inline script)."""
BAD_YAML = "vehicle: [unclosed\n  a: : b\n"
"""A display file that is not YAML (yaml.safe_load raises a ParserError)."""

SHAPE_CONTRAST = 3.0
TEXT_CONTRAST = 4.5
SHAPE_OUTLINES = {
    "--sc-earth": "--sc-ground",
    "--sc-shaft": "--sc-shaft-line",
    "--sc-ring": "--sc-ring-line",
    "--sc-body": "--sc-body-line",
    "--sc-tank-empty": "--sc-tank-line",
    "--sc-plume": "--sc-plume-line",
    "--sc-carriage": "--sc-carriage-line",
    "--sc-steel": "--sc-steel-line",
    "--sc-rail": "--sc-rail-line",
}
"""Every drawn fill token and its outline token (the earth's outline is the ground line)."""
SHAPE_PAIRS = (
    # (foreground, background): a shape's outline (or a fill that must read against another)
    ("--sc-ground", "--sc-sky"),  # ground line against the sky
    ("--sc-ground", "--sc-earth"),  # ... and the earth under it
    ("--sc-ground", "--panel"),
    ("--sc-shaft-line", "--sc-earth"),  # shaft walls in the earth
    ("--sc-shaft-line", "--sc-shaft"),  # ... and inside the shaft
    ("--sc-shaft-line", "--sc-sky"),
    ("--sc-shaft-line", "--panel"),
    ("--sc-ring-line", "--sc-earth"),  # drive rings in the wall
    ("--sc-ring-line", "--sc-shaft"),
    ("--sc-ring-line", "--panel"),
    ("--sc-body-line", "--sc-sky"),  # the rocket against the sky, shaft, earth and panel
    ("--sc-body-line", "--sc-shaft"),
    ("--sc-body-line", "--sc-earth"),
    ("--sc-body-line", "--panel"),
    ("--sc-tank-line", "--sc-body"),  # a tank inside the body
    ("--sc-prop", "--sc-tank-empty"),  # propellant against the empty tank
    ("--sc-hatch", "--sc-tank-empty"),  # the never-loaded band's hatch
    ("--sc-plume-line", "--sc-sky"),  # the plume against the sky, shaft, earth and panel
    ("--sc-plume-line", "--sc-shaft"),
    ("--sc-plume-line", "--sc-earth"),
    ("--sc-plume-line", "--panel"),
    ("--sc-plume-line", "--sc-carriage"),  # hot start: plume over the carriage (shaft, close-up)
    ("--sc-carriage-line", "--sc-shaft"),  # carriage in the shaft, above the mouth, close-up
    ("--sc-carriage-line", "--sc-sky"),
    ("--sc-carriage-line", "--panel"),
    ("--sc-steel-line", "--sc-sky"),  # mount, clamps, engine section, interstage
    ("--sc-steel-line", "--sc-earth"),
    ("--sc-steel-line", "--sc-shaft"),
    ("--sc-steel-line", "--panel"),
    ("--sc-rail-line", "--sc-sky"),  # brake rails above the mouth
    ("--sc-rail-line", "--sc-shaft"),
    ("--sc-rail-line", "--panel"),
    ("--ink-3", "--sc-sky"),  # the close-up's and every plate's border, the carriage's leader
    ("--ink-3", "--sc-earth"),  # the scale bar, gauge and marker plates over the earth; the leader
    ("--ink-3", "--sc-shaft"),  # ... and over the shaft
    ("--caution", "--sc-sky"),  # the impact caution plate's border over the sky
    ("--caution", "--panel"),  # ... in the band, and the exploratory strip's border
    ("--focus", "--panel"),  # the keyboard focus ring
    ("--focus", "--bg"),  # the keyboard focus ring
)
TEXT_PAIRS = (
    ("--ink", "--panel"),  # page text, canvas header, plates, the readout
    ("--ink-2", "--panel"),  # the header's second line, the note, legend and caveat bands
    ("--ink-3", "--panel"),
    ("--ink", "--bg"),
    ("--ink-2", "--bg"),  # the embed caveat strip (no background of its own)
    ("--ink-3", "--bg"),
    ("--caution", "--caution-bg"),  # the caveat heading
    ("--ink", "--caution-bg"),  # caveat text, the impact note, the exploratory banner and strip
    ("--ink-2", "--caution-bg"),  # the line over the recorded offload caveats
    ("--bad", "--panel"),  # a failed load-time check, the offload flags
)


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """silo_screening_2d with fixed guidance and two flights (pad, silo_failed) run once
    through sim.run_experiment into a temporary results root; the results directory."""
    exp = yaml.safe_load(
        (REPO / "experiments" / "silo_screening_2d.yaml").read_text(encoding="utf-8")
    )
    veh = yaml.safe_load(
        (REPO / "configs" / "vehicles" / "generic_f9_class_2d.yaml").read_text(encoding="utf-8")
    )
    exp["search"].update(
        {
            "figure_of_merit": "none",
            "fixed_gamma_star_deg": FIXED_GAMMA_DEG,
            "fixed_ltg_a": FIXED_LTG[0],
            "fixed_ltg_b_per_s": FIXED_LTG[1],
            "search_rtol": FIXTURE_RTOL,
            "final_rtol": FIXTURE_RTOL,
            "delta_xtol_rad": FIXTURE_DELTA_XTOL_RAD,
        }
    )
    exp["baseline"]["integrator"]["sample_dt_s"] = FIXTURE_SAMPLE_DT_S
    exp["baseline"]["integrator"]["rtol"] = FIXTURE_RTOL
    exp["checks"]["maxq_scan_points"] = FIXTURE_MAXQ_SCAN_POINTS
    exp["variants"] = {k: v for k, v in exp["variants"].items() if k == "silo_failed"}
    for key in ("sweeps", "sensitivity", "bounds", "cases"):
        exp.pop(key, None)
    resolved = resolve_experiment(exp, veh)
    root = tmp_path_factory.mktemp("scene_page")
    _, out = sim.run_experiment(resolved, root, plots=False, repo_root=REPO)
    return out


@pytest.fixture(scope="module")
def payload(run_dir: Path) -> dict[str, Any]:
    return scene.scene_payload(run_dir, ["pad", "silo_failed"], display_dir=DISPLAY_DIR)


@pytest.fixture(scope="module")
def template() -> str:
    return scene.load_template()


def _script(page: str) -> str:
    """The one inline (executable) script of a page."""
    scripts = re.findall(r"<script>(.*?)</script>", page, re.S)
    assert len(scripts) == 1
    return scripts[0]


def _data_block(page: str, block_id: str) -> str:
    found = re.findall(
        rf'<script type="application/json" id="{block_id}">(.*?)</script>', page, re.S
    )
    assert len(found) == 1
    return found[0]


def _strict_json(text: str) -> Any:
    def refuse(name: str) -> Any:
        raise ValueError(f"non-strict JSON constant {name}")

    return json.loads(text, parse_constant=refuse)


# ------------------------------------------------------------------ the template


def test_template_ships_as_package_data_with_one_token_and_its_own_marker(template: str) -> None:
    """Read through importlib.resources (scene.load_template); ASCII with LF line ends;
    the data token exactly once; the scene's marker in its style comment and never the
    replay page's (site/build.py frames pages by that marker); charset, lang and the two
    data blocks present."""
    assert template.isascii() and "\r" not in template
    assert template.startswith('<!doctype html>\n<html lang="en">')
    assert '<meta charset="utf-8">' in template
    assert template.count(scene.SCENE_DATA_TOKEN) == 1
    assert scene.SCENE_MARKER in template and REPLAY_MARKER not in template
    assert scene.SCENE_MARKER == "Written by launchsim scene"
    assert _data_block(template, "scene-data") == scene.SCENE_DATA_TOKEN
    assert _data_block(template, "qa-state") == ""
    assert 'JSON.parse(document.getElementById("scene-data").textContent)' in template
    for canvas in re.findall(r"<canvas\b[^>]*>(.*?)</canvas>", template, re.S):
        assert canvas.strip(), "every canvas carries fallback text"
    scene_canvas = re.search(r"<canvas id=\"scene\"[^>]*>", template)
    assert scene_canvas and 'role="img"' in scene_canvas.group(0)
    assert "aria-label=" in scene_canvas.group(0)


def test_rendered_page_is_ascii_with_strict_json_and_lt_escaped(
    payload: dict[str, Any], template: str
) -> None:
    """render_page replaces the one token with scene_json and changes nothing else; the
    page is ASCII; its data block is strict JSON equal to the payload; a string with
    '</script>' or '<!--' cannot close the block; NaN is refused."""
    hostile = dict(payload)
    hostile["caveats"] = [*payload["caveats"], "</script><img src=x onerror=1>", "<!--<script>"]
    page = scene.render_page(hostile)
    assert page.isascii()
    block = _data_block(page, "scene-data")
    assert "<" not in block
    assert _strict_json(block) == json.loads(json.dumps(hostile))
    assert page == template.replace(scene.SCENE_DATA_TOKEN, scene.scene_json(hostile))
    with pytest.raises(ValueError):
        scene.render_page({**payload, "bad": math.nan})


def _function_source(src: str, name: str) -> list[str]:
    """Every definition of ``name`` at two-space indent: the one-line form first, else
    the text up to the first line that is exactly two spaces and '}' (survey 04 section
    7.2; the multi-line pattern tried first runs on into the next function)."""
    one_line = re.findall(rf"^  function {name}\(.*\}}$", src, re.M)
    if one_line:
        return one_line
    return re.findall(rf"^  function {name}\(.*?^  \}}$", src, re.M | re.S)


def test_seven_helpers_are_byte_identical_to_replay(template: str) -> None:
    """readPalette, idxAt, valAt, phaseAt, setupCanvas, tick and setPlaying are copied
    verbatim from replay.html (D-SP2-21); the closure names they use are defined; the
    scene's currentRate is its own."""
    replay_src = replay.load_template()
    for name in PINNED_HELPERS:
        ours, theirs = _function_source(template, name), _function_source(replay_src, name)
        assert len(ours) == 1 and len(theirs) == 1, name
        assert ours[0] == theirs[0], f"{name} differs from replay.html's"
    for closure in (
        "const runs = ",
        "const colorVar = ",
        "function css(",
        "let PAL = {}",
        "const PHASE_NAME = ",
        "let T_MIN = ",
        "let tNow = 0, playing = false, lastFrame = null;",
        "function draw()",
        "function currentRate()",
        'id="play"',
        'id="rate"',
    ):
        assert closure in template, closure
    assert _function_source(template, "currentRate") != _function_source(replay_src, "currentRate")


def test_no_html_sink_takes_anything_but_a_literal(template: str) -> None:
    """innerHTML, outerHTML, insertAdjacentHTML, document.write and the newer HTML parsers
    (setHTMLUnsafe, parseHTMLUnsafe, createContextualFragment, DOMParser, srcdoc) appear
    only with a string literal (today: not at all); values reach the DOM by textContent."""
    script = _script(template)
    for sink in HTML_SINKS:
        for match in re.finditer(re.escape(sink), script):
            statement = script[match.start() : script.index(";", match.start())]
            assert re.fullmatch(
                rf"{re.escape(sink)}\s*(=\s*|\(\s*)(\"[^\"\\]*\"|'[^'\\]*')\s*\)?", statement
            ), f"{sink} with non-literal content: {statement}"
    assert "textContent" in script


def test_the_page_makes_no_request(template: str) -> None:
    """No http(s) URL anywhere in the template; no network API in the script; every link
    and src is a data: URI (the tab icon only); no CSS url() but data:."""
    assert not re.search(r"https?://", template, re.I)
    script = _script(template)
    for api in NETWORK_APIS:
        assert api not in script, api
    assert "@import" not in template
    links = re.findall(r"<link\b[^>]*>", template)
    assert len(links) == 1 and 'rel="icon"' in links[0]
    for href in re.findall(r"\bhref=\"([^\"]*)\"", template):
        assert href.startswith("data:"), href
    for src in re.findall(r"\bsrc=\"([^\"]*)\"", template):
        assert src.startswith("data:"), src
    for url in re.findall(r"url\(([^)]*)\)", template):
        assert url.strip("'\" ").startswith("data:"), url


def test_meta_csp_allows_only_the_inline_script_styles_and_data_images(template: str) -> None:
    """A meta Content-Security-Policy before any script: default-src 'none'; the one
    inline script by its sha256 (which must match the script: the message gives the new
    value); inline styles; data: images; no connect-src, so no request."""
    metas = re.findall(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)">', template)
    assert len(metas) == 1
    assert template.index("Content-Security-Policy") < template.index("<script")
    directives = {
        part.split()[0]: part.split()[1:]
        for part in (p.strip() for p in metas[0].split(";"))
        if part
    }
    script_src = directives.pop("script-src")
    assert directives == CSP_DIRECTIVES
    digest = base64.b64encode(hashlib.sha256(_script(template).encode("utf-8")).digest()).decode()
    assert script_src == [f"'sha256-{digest}'"], (
        f"the inline script changed: set script-src to 'sha256-{digest}' in the template"
    )


def test_tab_icon_is_the_brand_favicon(template: str) -> None:
    """The scene page carries the tab icon only (D-SP2-33): assets/brand/favicon.svg as a
    base64 data URI, byte for byte."""
    (href,) = re.findall(r'<link rel="icon" type="image/svg\+xml" href="([^"]*)">', template)
    prefix = "data:image/svg+xml;base64,"
    assert href.startswith(prefix)
    assert base64.b64decode(href[len(prefix) :]) == FAVICON.read_bytes()


# ------------------------------------------------------------------ tokens and contrast


def _blocks(css_text: str) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """(light, dark under prefers-color-scheme, dark under data-theme) token dicts of a
    stylesheet written in the site's three-block pattern."""

    def tokens(body: str) -> dict[str, str]:
        return {k: v.strip() for k, v in re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", body)}

    light = re.search(r"^:root \{(.*?)^\}", css_text, re.M | re.S)
    dark_media = re.search(
        r'@media \(prefers-color-scheme: dark\) \{\s*:root:not\(\[data-theme="light"\]\) \{(.*?)\}',
        css_text,
        re.S,
    )
    dark_attr = re.search(r':root\[data-theme="dark"\] \{(.*?)\}', css_text, re.S)
    assert light and dark_media and dark_attr
    return tokens(light.group(1)), tokens(dark_media.group(1)), tokens(dark_attr.group(1))


def _luminance(hex_colour: str) -> float:
    assert re.fullmatch(r"#[0-9a-f]{6}", hex_colour), hex_colour
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def test_site_tokens_are_carried_unchanged(template: str) -> None:
    """Every token of site/assets/site.css's three blocks (lines 14-60) is in the scene's
    blocks with the same value; both dark blocks are identical; color-scheme is set in
    both themes."""
    site_text = SITE_CSS.read_text(encoding="utf-8")
    ours, theirs = _blocks(template), _blocks(site_text)
    for mine, site in zip(ours, theirs, strict=True):
        for key, value in site.items():
            assert mine.get(key) == value, key
    assert ours[1] == ours[2]
    assert "color-scheme: light;" in template and template.count("color-scheme: dark;") == 2


def test_every_shape_has_an_outline_and_every_pair_meets_its_contrast(template: str) -> None:
    """Each drawn fill token has an outline token; in both themes every shape pair of
    SHAPE_PAIRS reaches 3:1 and every text pair of TEXT_PAIRS 4.5:1 (WCAG 2.x)."""
    light, dark, _ = _blocks(template)
    themes = {"light": light, "dark": {**light, **dark}}
    for fill, outline in SHAPE_OUTLINES.items():
        assert fill in light and outline in light and fill in dark and outline in dark
    low = []
    for theme, tokens in themes.items():
        for pairs, need in ((SHAPE_PAIRS, SHAPE_CONTRAST), (TEXT_PAIRS, TEXT_CONTRAST)):
            for fg, bg in pairs:
                ratio = _contrast(tokens[fg], tokens[bg])
                if ratio < need:
                    low.append(f"{theme}: {fg} on {bg} is {ratio:.2f}, needs {need}")
    assert not low, low


# ------------------------------------------------------------------ the script under node


@pytest.mark.skipif(NODE is None, reason="node not installed: inline script syntax not checked")
def test_inline_script_is_valid_javascript(payload: dict[str, Any], tmp_path: Path) -> None:
    js = tmp_path / "inline.js"
    js.write_text(_script(scene.render_page(payload)), encoding="utf-8")
    assert NODE is not None
    proc = subprocess.run(
        [NODE, "--check", str(js)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


PURE_BEGIN = (
    "// ------------------------------------------------------------------ pure functions: begin"
)
PURE_END = (
    "// ------------------------------------------------------------------ pure functions: end"
)
HARNESS = """
const fs = require("fs");
const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = {};
out.hash = input.hashes.map(h => parseHash(h[0], input.limits));
out.no_limits = [parseHash("#t=5"), parseHash("#t=5", null), parseHash("#t=5&runs=pad", 7),
  parseHash("#t=5", { tMin: "a", tMax: 9 })];
out.big_qa = parseHash("#qa=" + new Array(1000000).fill("1.5").join(","), input.limits).qa.length;
out.big_runs = parseHash("#runs=" + new Array(100000).fill("pad").join(","), input.limits).runs;
out.screen = input.points.map(p => screenXY(p[0], p[1], input.rE));
out.extent = runningExtent(input.alt, input.dr, input.floor, input.L, input.aspect);
out.height = out.extent.map(e => viewHeight(e, input.hMin, input.margin));
out.camera = cameraView(out.extent[3], { min_view_height_m: input.hMin, margin: input.margin },
  { x: 0, y: 0, w: 800, h: 400 }, { xMin: -10, xMax: 30, yMin: -100, yMax: 370 });
out.rate = input.rateTimes.map(rateLaw);
out.nice = input.niceIn.map(niceLength);
out.wrap = input.wrapIn.map(wrapDeg);
out.qa_no_limits = [parseHash("#qa=1,2").qa, parseHash("#qa=1,2", { tMin: -1 }).qa];
out.snap_big = [1e308, -1e308, 1e300, 2.5000004].map(t => snapTime(t, 6));
out.side = input.side.map(c =>
  sideLabel(s => c.charPx * s.length, c.text, c.walls, c.span, c.gap, c.pad));
out.split = splitCaveats(input.caveats, input.recorded);
process.stdout.write(JSON.stringify(out));
"""
LABEL_TEXT = "carriage after release: drawn, not computed"
"""The carriage label (the template's CARRIAGE_LABEL)."""
SIDE_LABEL_CASES = {
    # name: (walls [left, right] x, span [left, right] x) [px], the shaft centred in the view as
    # the camera frames it after release (rails 3.5 m out at 1.6 to 2.65 px per m)
    "1280 px page": ([604.0, 617.0], [10.0, 1212.0]),
    "375 px page": ([156.0, 169.0], [10.0, 315.0]),
    "walls near the right edge": ([1180.0, 1195.0], [10.0, 1212.0]),
    "narrow page, walls at the right": ([250.0, 263.0], [10.0, 300.0]),
    "no room either side": ([30.0, 40.0], [10.0, 60.0]),
}
LABEL_CHAR_PX = 5.6
"""Width per character [px] that stands in for the 11 px font's measureText under node."""
LABEL_GAP_PX = 12.0
LABEL_PAD_PX = 6.0
"""The template's LABEL_GAP_PX and PLATE_PAD_PX."""
CRAFTED_HASHES = (
    ("#t=<img src=x onerror=1>", {"t": None}),
    ("#t=%3Cimg%20src%3Dx%20onerror%3D1%3E", {"t": None}),
    ('#theme="><script>', {"theme": None}),
    ("#theme=%22%3E%3Cscript%3E", {"theme": None}),
    ("#t=1e999", {"t": None}),
    ("#t=-1e999", {"t": None}),
    ("#t=NaN", {"t": None}),
    ("#t=Infinity", {"t": None}),
    ("#t=0x10", {"t": None}),
    ("#t=%E0%A4%A", {"t": None}),
    ("#t=-50", {"t": -2.5}),
    ("#t=1e6", {"t": 600.0}),
    ("#t=12.5&t=40", {"t": 12.5}),
    (
        "#t=12.5&theme=dark&runs=silo_failed,pad,unknown,pad&embed=1&autoplay=1"
        "&qa=1,2,<svg onload=1>,1e999,NaN,-3",
        {
            "t": 12.5,
            "theme": "dark",
            "runs": ["silo_failed", "pad"],
            "embed": True,
            "autoplay": True,
            "qa": [1, 2, -2.5],  # -3 clamped to the data, as t is
        },
    ),
    ("#qa=1e308,-1e308,5", {"qa": [600.0, -2.5, 5]}),  # clamped: snapTime never sees 1e308
    ("#theme=light&embed=true&autoplay=yes", {"theme": "light", "embed": False, "autoplay": False}),
    ("#runs=a%2Bb,a+b,a%20b", {"runs": ["a+b"]}),
    ("#__proto__=1&constructor=2&toString=3&hasOwnProperty=4", {}),
    ("#qa=", {"qa": []}),
    ("", {}),
    ("#", {}),
)
HASH_DEFAULTS = {
    "t": None,
    "theme": None,
    "runs": [],
    "embed": False,
    "autoplay": False,
    "qa": None,
}


def _pure_block(template: str) -> str:
    start, end = template.index(PURE_BEGIN), template.index(PURE_END)
    return template[start:end]


@pytest.mark.skipif(NODE is None, reason="node not installed: page functions not run")
def test_parse_hash_transform_and_camera_under_node(
    template: str, payload: dict[str, Any], tmp_path: Path
) -> None:
    """The page's pure block run under node: parseHash ignores what is not exactly its
    contract (crafted t, theme and qa values, 1e6 qa entries, 1e999, NaN, unknown keys,
    malformed escapes) and clamps t and every qa time to the data (none kept without
    finite limits); snapTime leaves a time too large to scale as it is; screenXY,
    runningExtent and viewHeight equal display.screen_xy, running_extent_m and
    view_height_m; cameraView frames the content in the middle of the view; the A3 rate
    law and the helpers; sideLabel puts the carriage label inside the view and outside
    the rails (at the 1280 px and 375 px pages' geometry, near an edge) or nowhere, never
    cut; splitCaveats keeps every payload caveat in exactly one of its two lists."""
    scene_cfg = scene.load_scene_config(DISPLAY_DIR)
    h_min = scene_cfg.camera.min_view_height_m.value
    margin = scene_cfg.camera.margin.value
    alt = [-100.0, -50.0, 0.0, 300.65, 120.0, 0.0, 5.0e4, 2.0e5]
    dr = [0.0, 0.0, 0.0, -0.2, -0.3, -0.4, 3.0e4, 2.0e6]
    points = [
        (0.0, 0.0),
        (100.0, 0.0),
        (300.0, -0.4),
        (5.0e5, 1.0e5),
        (2.0e5, 2.0e6),
        (-100.0, 50.0),
    ]
    case = {
        "hashes": [[text] for text, _ in CRAFTED_HASHES] + [[None]],
        "limits": {"tMin": -2.5, "tMax": 600.0, "names": ["pad", "silo_failed", "a+b"]},
        "points": points,
        "rE": display.R_EARTH_M,
        "alt": alt,
        "dr": dr,
        "floor": -100.0,
        "L": 70.0,
        "aspect": 2.3,
        "hMin": h_min,
        "margin": margin,
        "rateTimes": [-3.0, 11.99, 12.0, 44.9, 45.0, 500.0],
        "niceIn": [0.0, 0.7, 1.0, 1.9, 2.0, 4.99, 5.0, 99.0, 180.0, 12345.0],
        "wrapIn": [0.0, 90.0, 180.0, 190.0, -190.0, 450.0, 269.9],
        "side": [
            {
                "text": LABEL_TEXT,
                "walls": walls,
                "span": span,
                "gap": LABEL_GAP_PX,
                "pad": LABEL_PAD_PX,
                "charPx": LABEL_CHAR_PX,
            }
            for walls, span in SIDE_LABEL_CASES.values()
        ],
        # as scene_payload builds it: the run caveats, then the recorded offload caveats (one
        # of them also a run caveat, word for word)
        "caveats": [*payload["caveats"], "recorded offload caveat", payload["caveats"][0]],
        "recorded": ["recorded offload caveat", payload["caveats"][0]],
    }
    data_file = tmp_path / "case.json"
    data_file.write_text(json.dumps(case), encoding="utf-8")
    js = tmp_path / "pure.js"
    js.write_text(_pure_block(template) + HARNESS, encoding="utf-8")
    assert NODE is not None
    proc = subprocess.run(
        [NODE, str(js), str(data_file)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)

    for (text, want), got in zip(CRAFTED_HASHES, out["hash"], strict=False):
        assert got == {**HASH_DEFAULTS, **want}, text
    assert out["hash"][-1] == HASH_DEFAULTS  # not a string
    # total: no limits, null or non-object limits, non-numeric bounds: t ignored, nothing thrown
    assert out["no_limits"] == [HASH_DEFAULTS] * 4
    assert out["big_qa"] == 200
    assert out["big_runs"] == ["pad"]

    for (a, d), got in zip(points, out["screen"], strict=True):
        x, y = display.screen_xy(a, d)
        assert got[0] == pytest.approx(float(x), rel=1e-12, abs=1e-6)
        assert got[1] == pytest.approx(float(y), rel=1e-12, abs=1e-6)
    extent = display.running_extent_m(
        np.array(alt), np.array(dr), floor_m=-100.0, body_length_m=70.0, aspect=2.3
    )
    np.testing.assert_allclose(out["extent"], extent, rtol=1e-12)
    np.testing.assert_allclose(
        out["height"], display.view_height_m(extent, h_min, margin), rtol=1e-12
    )
    assert out["extent"][0] == pytest.approx(170.0)  # by hand: max(-100, 0) + 100 + 70
    cam = out["camera"]
    height = float(display.view_height_m(extent[3], h_min, margin))
    assert cam["H"] == pytest.approx(height, rel=1e-12)
    assert cam["ppm"] == pytest.approx(400.0 / height, rel=1e-12)
    assert cam["W"] == pytest.approx(800.0 / cam["ppm"], rel=1e-12)
    assert cam["x0"] + cam["W"] / 2 == pytest.approx(10.0)
    assert cam["y0"] + cam["H"] / 2 == pytest.approx(135.0)
    assert out["rate"] == [1, 1, 5, 5, 30, 30]
    assert out["nice"] == pytest.approx([0, 0.5, 1, 1, 2, 2, 5, 50, 100, 10000])
    assert out["wrap"] == pytest.approx([0.0, 90.0, -180.0, -170.0, 170.0, 90.0, -90.1])
    assert out["qa_no_limits"] == [[], []]
    assert out["snap_big"] == [1e308, -1e308, 1e300, 2.5]

    for (name, (walls, span)), got in zip(SIDE_LABEL_CASES.items(), out["side"], strict=True):
        if name == "no room either side":
            assert got is None, name
            continue
        assert got is not None, name
        assert " ".join(got["lines"]) == LABEL_TEXT, name  # every word kept
        widest = max(LABEL_CHAR_PX * len(s) for s in got["lines"]) + 2 * LABEL_PAD_PX
        assert got["w"] == pytest.approx(widest), name
        if got["side"] == "right":
            x0, x1 = got["x"], got["x"] + got["w"]
            assert x0 >= walls[1] + LABEL_GAP_PX - 1e-9, name  # right of the right rail
        else:
            x0, x1 = got["x"] - got["w"], got["x"]
            assert x1 <= walls[0] - LABEL_GAP_PX + 1e-9, name  # left of the left rail
        assert span[0] - 1e-9 <= x0 and x1 <= span[1] + 1e-9, name  # inside the view, never cut
    sides = {n: g and g["side"] for n, g in zip(SIDE_LABEL_CASES, out["side"], strict=True)}
    assert sides["1280 px page"] == "right" and sides["walls near the right edge"] == "left"
    # the right side first, wrapped, so the plate does not hop sides as the rails move a pixel
    assert sides["375 px page"] == "right" and sides["narrow page, walls at the right"] == "left"
    lines = {n: g and len(g["lines"]) for n, g in zip(SIDE_LABEL_CASES, out["side"], strict=True)}
    assert lines["1280 px page"] == 1 and lines["walls near the right edge"] == 1
    assert lines["375 px page"] > 1 and lines["narrow page, walls at the right"] > 1

    recorded = case["recorded"]
    assert out["split"]["recorded"] == recorded
    assert out["split"]["own"] == [c for c in payload["caveats"] if c not in recorded]
    assert set(out["split"]["own"]) | set(recorded) == set(case["caveats"])
    assert not set(out["split"]["own"]) & set(recorded)


SNAP_HARNESS = """
const run = { t: [0.5, 1.000001, 1.000001, 1.5], y: [0, 10, 20, 30], s: [0, 0, 1, 1] };
const stepAt = (r, f, t) => r[f][idxAt(t, r.t)];
const out = {};
// a query at the CSV's own event time (more decimals than the payload's clock), raw and snapped
out.raw = [valAt(run, "y", 1.0000005), stepAt(run, "s", 1.0000005)];
const tt = snapTime(1.0000005, 6);
out.snapped = [tt, valAt(run, "y", tt), stepAt(run, "s", tt)];
// rounded down (1.0000014 -> 1.000001) it lands on the later row too; a snap moves t <= 0.5e-6 s
const td = snapTime(1.0000014, 6);
out.down = [td, valAt(run, "y", td), stepAt(run, "s", td)];
out.neg = snapTime(-2.6073181790, 6);
out.grid = [snapTime(12.4937285829, 6), snapTime(151.328437545, 6), snapTime(0, 6)];
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(NODE is None, reason="node not installed: page functions not run")
def test_snap_time_puts_an_event_time_on_the_later_row(template: str, tmp_path: Path) -> None:
    """Exit criterion 5 at an event time: a time taken from events.csv or timeseries.csv
    (10 decimals) falls just before the payload's duplicate pair when rounding to
    scene.TIME_DECIMALS goes up, and valAt (pinned, replay.html's) then interpolates toward
    the row before the pair. snapTime puts the query on the payload's clock first, so the
    pinned idxAt picks the later row of the pair for interpolated and step series alike;
    stateAt, captureFrame, #t and #qa all snap (checked in the script)."""
    helpers = "\n".join(_function_source(template, name)[0] for name in ("idxAt", "valAt"))
    js = tmp_path / "snap.js"
    js.write_text(_pure_block(template) + helpers + SNAP_HARNESS, encoding="utf-8")
    assert NODE is not None
    proc = subprocess.run(
        [NODE, str(js)], capture_output=True, text=True, encoding="utf-8", timeout=60, check=False
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["raw"][0] == pytest.approx(10.0, abs=1e-3) and out["raw"][1] == 0  # the earlier row
    assert out["snapped"] == [1.000001, 20, 1]  # the later row
    assert out["down"] == [1.000001, 20, 1]
    assert out["neg"] == -2.607318
    assert out["grid"] == [12.493729, 151.328438, 0]
    script = _script(template)
    for use in (
        "panelState(panelRun, snapTime(tt, TIME_DECIMALS), sceneBox())",  # stateAt (and #qa)
        "drawPanel(ctx, box, snapTime(tt, TIME_DECIMALS), pal, panelRun)",  # captureFrame
        "snapTime(hash.t, TIME_DECIMALS)",  # #t
    ):
        assert use in script, use
    assert "const TIME_DECIMALS = DATA.tolerances.time_decimals;" in script


# ------------------------------------------------------------------ writing the page


def test_write_scene_page_default_path_and_refusals(run_dir: Path, tmp_path: Path) -> None:
    """The default file is <cwd>/<experiment>_<timestamp>_scene.html (next to the
    outermost results tree when cwd is inside one); refused, with nothing written: an
    output inside the run's tree or any folder named results in any letter case, a
    missing folder, a suffix other than .html or .htm (any case)."""
    experiment, timestamp = run_data.run_identity(run_dir)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    written = scene.write_scene_page(run_dir, None, None, cwd=cwd, display_dir=DISPLAY_DIR)
    assert written == cwd / f"{experiment}_{timestamp}_scene.html"
    page = written.read_text(encoding="utf-8")
    assert page.isascii() and "\r" not in page and scene.SCENE_MARKER in page
    shown = [r["key"] for r in _strict_json(_data_block(page, "scene-data"))["runs"]]
    assert shown == ["pad", "silo_failed"]  # D-SP2-28: the baseline and the assisted variant
    inside = scene.default_scene_path(run_dir, run_dir)
    assert inside == run_data.results_tree(run_dir).parent / written.name

    upper = tmp_path / "ReSuLtS"
    upper.mkdir()
    refusals = {
        run_dir / "page.html": "inside the results tree",
        upper / "page.html": "inside the results tree",
        tmp_path / "missing" / "page.html": "output folder does not exist",
        tmp_path / "page.txt": "must end in .html",
    }
    for out, message in refusals.items():
        with pytest.raises(scene.SceneError, match=message):
            scene.write_scene_page(run_dir, ["pad"], out, cwd=cwd, display_dir=DISPLAY_DIR)
        assert not out.exists()
    for name in ("page.HTM", "page.Html"):
        assert scene.write_scene_page(
            run_dir, ["silo_failed"], tmp_path / name, cwd=cwd, display_dir=DISPLAY_DIR
        ).is_file()


def test_cli_scene_writes_a_page_and_refuses_a_1d_directory(
    run_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``launchsim scene`` writes the page (one ASCII line with the path), finds the
    display files above the installed package when cwd has none, and refuses a 1-D
    directory, a missing display folder, a display file that is not YAML and an output
    inside the results tree with exit code 1, one error line, no traceback and nothing
    written."""
    experiment, timestamp = run_data.run_identity(run_dir)
    out = tmp_path / "page.html"
    code = cli.main(["scene", str(run_dir), "--runs", "silo_failed", "--out", str(out)])
    printed = capsys.readouterr().out
    assert code == 0 and out.is_file() and printed.isascii()
    assert printed.startswith("scene: ") and str(out) in printed
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    assert cli.main(["scene", str(run_dir)]) == 0
    assert (cwd / f"{experiment}_{timestamp}_scene.html").is_file()
    capsys.readouterr()

    one_d = tmp_path / "results" / "silo_screening_1d" / "20260101T000000Z"
    one_d.mkdir(parents=True)
    (one_d / run_data.METRICS_FILE).write_text(
        json.dumps({"experiment": "x", "baseline": "pad", "runs": {"pad": {}}}), encoding="utf-8"
    )
    (one_d / scene.SUMMARY_FILE).write_text("# s\n", encoding="utf-8")
    bad_display = tmp_path / "bad_display"
    shutil.copytree(DISPLAY_DIR, bad_display)
    (bad_display / "f9_class.yaml").write_text(BAD_YAML, encoding="utf-8")
    refused = {
        ("scene", str(one_d), "--display", str(DISPLAY_DIR)): "vertical_1d run",
        ("scene", str(run_dir), "--display", str(tmp_path / "no_display")): "no scene.yaml",
        # a vehicle display file that is not YAML: one line, not a yaml.YAMLError traceback
        ("scene", str(run_dir), "--display", str(bad_display)): "cannot read",
        ("scene", str(run_dir), "--out", str(run_dir / "x.html")): "inside the results tree",
        # the directory is checked before the display files are looked for
        ("scene", str(tmp_path / "no_such_run")): "run directory not found",
        ("scene", str(tmp_path / "no_such_run"), "--display", str(tmp_path / "x")): (
            "run directory not found"
        ),
    }
    before = sorted(p.name for p in cwd.iterdir())
    for argv, message in refused.items():
        assert cli.main(list(argv)) == 1
        printed = capsys.readouterr().out
        assert printed.startswith("error: ") and message in printed and "Traceback" not in printed
    assert not (run_dir / "x.html").exists()
    assert sorted(p.name for p in cwd.iterdir()) == before


# ------------------------------------------------------------------ what the page shows


def test_payload_carries_felt_g_yardstick_flags_and_the_drawing_constant(
    payload: dict[str, Any],
) -> None:
    """Each run carries the recorded felt axial g on its time grid (the hold reads g_eff,
    just under 1 g; the push reads more than 1 g), whether it is a yardstick (drawn
    dashed) and its offload flags (none here); the payload carries the plume's drawing
    constant that the display-only text quotes, and no exploratory mark for a recorded
    directory."""
    for run in payload["runs"]:
        felt = run["felt_g"]
        assert len(felt) == len(run["t"]) and all(isinstance(g, float) for g in felt)
        assert run["yardstick"] is False and run["flags"] == []
    pad = next(r for r in payload["runs"] if r["key"] == "pad")
    assert pad["phase"][0] == "HOLD" and 0.99 < pad["felt_g"][0] < 1.0
    failed = next(r for r in payload["runs"] if r["key"] == "silo_failed")
    push = [g for g, p in zip(failed["felt_g"], failed["phase"], strict=True) if p == "ASSIST"]
    assert push and min(push) > 1.0
    assert payload["drawing"] == {"plume_of_stack": scene.PLUME_OF_STACK}
    assert f"{scene.PLUME_OF_STACK:.0%} of the drawn stack" in scene.DISPLAY_ONLY[0]
    assert payload["exploratory_caveat"] is None


def test_exploratory_mark_is_the_one_string(run_dir: Path, tmp_path: Path) -> None:
    """An exploratory directory's payload carries replay.EXPLORATORY_CAVEAT as
    ``exploratory_caveat`` (None otherwise); the page takes the banner, the embed strip,
    the footer and the in-canvas strip from that one field, never by position in the
    caveat list and with no second wording of the mark; the strip is drawn only when the
    field is set."""
    copy = tmp_path / run_dir.parent.name / run_dir.name
    shutil.copytree(run_dir, copy)
    metrics_path = copy / run_data.METRICS_FILE
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["label"] = replay.EXPLORATORY_LABEL
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8", newline="\n")
    marked = scene.scene_payload(copy, ["pad"], display_dir=DISPLAY_DIR)
    assert marked["exploratory"] and marked["exploratory_caveat"] == replay.EXPLORATORY_CAVEAT
    script = _script(scene.load_template())
    assert "caveats[0]" not in script and "Exploratory run" not in script
    assert "EXPLORATORY" not in script  # the mark's text comes from the payload only
    for use in (
        "b.textContent = DATA.exploratory_caveat;",  # the banner
        'textContent = (DATA.exploratory_caveat ? DATA.exploratory_caveat + " " : "")',  # strip
        "if (DATA.exploratory_caveat) lines.push(DATA.exploratory_caveat);",  # footers
        "const mark = DATA.exploratory_caveat ? {",  # the in-canvas strip, only when set
        "if (lay.mark) drawMark(ctx, lay.mark, pal);",
    ):
        assert use in script, use


def test_the_drawing_reports_what_it_painted(template: str) -> None:
    """The vehicle is painted through ctx.transform with the direction the hook reports,
    and the base and nose the hook returns are read back through that transform; the hook
    draws the panel to get them (the close-up's nose too) and returns the readout's lines
    and the carriage label's plate (placed by sideLabel inside the view's margins); the
    readout (the engines' share of full vacuum thrust, named so, altitude or depth from
    alt_m, speed, felt g, drive force) is drawn in every layout, beside the gauges in the
    band only when its widest line fits; a yardstick's outlines are dashed; the run's note
    and its offload flags reach the page by textContent, the note drawn in the canvas
    band and kept in the page for assistive technology only."""
    script = _script(template)
    vehicle = _function_source(template, "drawVehicle")[0]
    assert "ctx.rotate(" not in vehicle
    assert "ctx.transform(s.dir[0], s.dir[1], -s.dir[1], s.dir[0], 0, 0);" in vehicle
    assert "getTransform()" in vehicle and "transformPoint(" in vehicle
    assert "if (s.dashed) ctx.setLineDash(DASH_OUTLINE);" in vehicle
    assert "dashed: run.yardstick === true" in script
    state = _function_source(template, "panelState")[0]
    assert "drawPanel(" in state and "closeup_nose_px: pm.closeup.nose" in state
    assert "base_px: pm.main.base, nose_px: pm.main.nose" in state and "hud: P.hud" in state
    hud = _function_source(template, "hudLines")[0]
    for text in ("enginesText(st.plume)", '"Engines off"', '"Depth "', '"Altitude "', '"Speed "'):
        assert text in hud, text
    assert '"Felt "' in hud and '"Drive "' in hud and '"Thrust ' not in hud
    engines = _function_source(template, "enginesText")[0]
    assert '"Engines "' in engines and '" of full vacuum thrust"' in engines
    assert '["thrust", "Engines (vacuum thrust)"]' in script
    assert "p_amb A_e" in template  # the telemetry note says what the engines figure is not
    assert "hudWidth(ctx, pal, run)" in _function_source(template, "panelLayout")[0]
    assert "drawHud(ctx, pal, hud," in _function_source(template, "drawView")[0]
    assert "drawHud(ctx, pal, view.hud, p.hud);" in _function_source(template, "drawPanel")[0]
    label = _function_source(template, "drawCarriageLabel")[0]
    assert (
        "sideLabel(" in label
        and "view.x + VIEW_MARGIN_PX, view.x + view.w - VIEW_MARGIN_PX" in label
    )
    assert "carriage_label: pm.carriageLabel" in state
    assert re.search(r'<p class="vh" id="runNote" hidden>', template)
    assert "note.textContent = panelRun.note" in script
    assert "drawTextBand(ctx, lay.noteBox, pal, lay.note, false);" in script
    assert '"Flagged: " + flagged.join("; ")' in script


def test_capture_frame_defaults_and_one_band_threshold(template: str) -> None:
    """captureFrame(t), the contract's one-argument call (design 4.5, D-SP2-30), is a
    1280 x 720 frame (a width and a height may still be given); the canvas is tall exactly
    when the script draws the band layout: one threshold, NARROW_VIEW_PX, read by a
    container query on the canvas's own width (a media query would also count the page's
    padding and any classic scrollbar)."""
    script = _script(template)
    capture = _function_source(template, "captureFrame")[0]
    assert capture.startswith("  function captureFrame(t, width, height) {")
    assert "const CAPTURE_DEFAULT_W_PX = 1280, CAPTURE_DEFAULT_H_PX = 720;" in script
    assert "width === undefined ? CAPTURE_DEFAULT_W_PX : width" in capture
    assert "height === undefined ? CAPTURE_DEFAULT_H_PX : height" in capture
    (narrow,) = re.findall(r"const NARROW_VIEW_PX = (\d+);", script)
    assert "body.w >= NARROW_VIEW_PX" in _function_source(template, "panelLayout")[0]
    style = template[: template.index("</style>")]
    assert re.search(
        r"\.scenepanel \{[^}]*container-type: inline-size; container-name: scenepanel;", style
    )
    tall = re.findall(r"@container scenepanel \(width < (\d+)px\) \{\s*#scene \{ height:", style)
    assert tall == [narrow]
    # no viewport rule makes the canvas tall
    for media in re.findall(r"@media[^{]*\{(.*?)\n\}", style, re.S):
        assert "clamp(900px" not in media
    assert style.index("@container scenepanel") > style.index("@media (max-width: 900px)")


def test_what_the_page_says_matches_what_it_draws(template: str) -> None:
    """A3 review round 3: the close-up's carriage label is drawn only whole (never cut by
    the drawing's edge over the readout) and reported by the hook; its title says it is
    rescaled whenever the stack shown is shorter than the whole stack (staging, the fairing
    drop); the pad's clamps open at liftoff; the hold is named without claiming a ramp; an
    impact run's ticker says the model has no contact; the run selector marks yardsticks;
    the page claims no spent-stage or fairing path (A3 draws none) and no impact 'at the
    mouth level' (the model's ground is altitude 0)."""
    script = _script(template)
    closeup = _function_source(template, "drawCloseup")[0]
    assert "ly - half >= draw.y && ly + half <= draw.y + draw.h" in closeup
    assert "lx + lw + CLOSEUP_LABEL_CLEAR_PX <= draw.x + draw.w" in closeup
    assert "closeup_carriage_label: pm.closeup.carriageLabel" in script
    assert '(L.parts.L < L.g.stack_length_m ? "rescaled with the stack: " : "own scale: ")' in (
        closeup
    )
    assert "scale changes at staging and at the fairing drop" in template
    clamps = _function_source(template, "drawClamps")[0]
    assert 'firstEventT(run, "liftoff")' in clamps and "open = t >= 0" not in clamps
    assert "drawClamps(ctx, t, pal, L, run);" in script
    assert 'HOLD: "Held down", ' in script and "engines ramping" not in script
    ticker = _function_source(template, "buildTicker")[0]
    assert "impactNote(panelRun)" in ticker and "IMPACT_TICKER_NOTE" in ticker
    assert "no contact with the carriage, the mouth or the shaft" in script
    assert '(r.yardstick === true ? YARDSTICK_MARK : "")' in _function_source(template, "init")[0]
    assert "fairing paths" not in template and "drag-free" not in template
    assert "mouth level" not in template
    assert "returns to altitude 0, the model's ground" in script


def test_recorded_offload_caveats_are_listed_apart_and_named(template: str) -> None:
    """The caveats built for the runs shown and the display-only items go in one list; the
    directory's recorded offload caveats (word for word) in a second list under a line that
    names their source; splitCaveats (tested under node) puts every payload caveat in one
    of the two."""
    script = _script(template)
    for use in (
        "const split = splitCaveats(DATA.caveats, DATA.offload_caveats);",
        'listItems("caveats", split.own.concat(DATA.display_only));',
        'listItems("offloadCaveats", split.recorded);',
    ):
        assert use in script, use
    head = re.search(r'<p class="note" id="offloadHead" hidden>([^<]*)</p>', template)
    assert head and "metrics.json offload.caveats" in head.group(1)
    assert "word for word" in head.group(1)
    assert '<ul id="offloadCaveats" hidden></ul>' in template
