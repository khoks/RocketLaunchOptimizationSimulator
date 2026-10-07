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

Step A3b (two panels, the flight after the kick, the rate law): the Auto rate under node on
the events of a pad and a cold silo start shaped as the recorded runs (each regime, no step
above 1% between samples 0.01 s apart but the named one, the 3x holds, criterion 16's
windows) and on a failed ignition; the payload's default pair, the page's choice of panels
and the one-run layout, the panel boxes against the CSS's container rules, and the camera
the panels share (one run gives A3's camera); the drawn separations, the label placement
and the event steps; the controls, captureFrame's composite and the hook's per-panel
states; the new shape and line pairs in the contrast table. Review round 3: the camera
frames the part of the view right of the close-up's column (the site and the vehicle
inside that frame), the marker regime's switch, the fairing halves inside the close-up's
drawing and clear of its caption, the shorter 1x span after a kick, the fairing cap, the
plain event names, the honest labels (drag-free, waiting, ended, the values shown) and a
captured frame's caveat footer. Fix round 4: the fairing seen from its drop until clear of
the vehicle (the close-up's halves drawn until they have wholly left it; in the view a
separated body on its vehicle drawn over it with a label on a leader), the
recorded max-Q, the short labels' 'display only', the telemetry's held and frozen states.
"""

from __future__ import annotations

import base64
import hashlib
import itertools
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
    # step A3b
    ("--run-0", "--sc-halo"),  # the flown path, over its halo (its outline) ...
    ("--run-1", "--sc-halo"),  # ... in each run colour; also the other panel's hollow ring
    ("--run-2", "--sc-halo"),
    ("--run-3", "--sc-halo"),
    ("--sc-sep", "--sc-halo"),  # a separated body's hollow marker and dashed path, over its halo
    # an event marker on the flown path is a diamond in the run colour outlined in --sc-body-line,
    # as the position marker is: the outline is checked against the halo of the flown path it
    # sits on, as well as against the sky and the earth above
    ("--sc-body-line", "--sc-halo"),  # an event diamond and the position marker over the halo
    ("--run-0", "--panel"),  # the slider's event marks per panel, and the column swatches
    ("--run-1", "--panel"),
    ("--run-2", "--panel"),
    ("--run-3", "--panel"),
    ("--ink", "--panel"),  # the swatches' outline
    ("--ink-3", "--panel"),  # an event mark not yet passed
    ("--ink-3", "--sc-halo"),  # a label plate's border where it crosses a halo
    ("--caution", "--sc-earth"),  # a frozen panel's banner over the earth
    ("--caution", "--sc-shaft"),
)
LINE_HALOS = {
    "--run-0": "--sc-halo",
    "--run-1": "--sc-halo",
    "--run-2": "--sc-halo",
    "--run-3": "--sc-halo",
    "--sc-sep": "--sc-halo",
}
"""Step A3b: every drawn line or hollow marker (the flown path, the other panel's ring, a
separated body's marker and path) and the halo drawn under it as its outline."""
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
    # step A3b's text is on these same pairs: label plates on the view, the banner of a run in
    # orbit and the column heads are --ink on --panel; the banner of a run that did not reach
    # orbit --ink on --caution-bg; event names over the slider and the close-up's captions
    # --ink-2 and --ink on --panel
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
    for fill, outline in {**SHAPE_OUTLINES, **LINE_HALOS}.items():
        assert fill in light and outline in light and fill in dark and outline in dark
    for line, halo in LINE_HALOS.items():
        assert (line, halo) in SHAPE_PAIRS, line
    script = _script(template)
    assert 'halo: "--sc-halo", sep: "--sc-sep",' in script
    assert script.count("haloStroke(ctx, pal, ") >= 4  # path, body path, body marker, other ring
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
    view_height_m; cameraView frames the content in the middle of the view; the helpers
    (step A3b's rate law has a test of its own); sideLabel puts the carriage label inside
    the view and outside
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
        "panelStates(snapTime(tt, TIME_DECIMALS), sceneBox())",  # stateAt (and #qa)
        "const ts = snapTime(tt, TIME_DECIMALS);",  # captureFrame ...
        "drawScene(ctx, box, ts, pal, panelRuns);",  # ... draws at the snapped time
        "snapTime(hash.t, TIME_DECIMALS)",  # #t
        "tNow = Math.min(T_MAX, Math.max(T_MIN, snapTime(t, TIME_DECIMALS)));",  # keys, ticker
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
    states = _function_source(template, "panelStates")[0]
    assert "drawScene(" in states and "closeup_nose_px: pm.closeup.nose" in state
    assert "base_px: pm.main.base, nose_px: pm.main.nose" in state and "hud: P.hud" in state
    hud = _function_source(template, "hudLines")[0]
    for text in ("enginesText(st.plume)", '"Engines off"', '"Depth "', '"Altitude "', '"Speed "'):
        assert text in hud, text
    assert '"Felt "' in hud and '"Drive "' in hud and '"Thrust ' not in hud
    engines = _function_source(template, "enginesText")[0]
    assert '"Engines "' in engines and '" of full vacuum thrust"' in engines
    assert '["thrust", "Engines (vacuum thrust)"]' in script
    assert "p_amb A_e" in template  # the telemetry note says what the engines figure is not
    assert "hudWidth(ctx, pal, run)" in _function_source(template, "plateRow")[0]
    assert "plateRow(ctx, pal, run, body)" in _function_source(template, "panelLayout")[0]
    assert "drawReadout(ctx, pal, run, L, box, hud," in _function_source(template, "drawView")[0]
    assert "drawHud(ctx, pal, hud," in _function_source(template, "drawReadout")[0]
    assert "drawHud(ctx, pal, view.hud, p.hud)" in _function_source(template, "drawPanel")[0]
    label = _function_source(template, "drawCarriageLabel")[0]
    assert (
        "sideLabel(" in label
        and "view.x + VIEW_MARGIN_PX, view.x + view.w - VIEW_MARGIN_PX" in label
    )
    assert "carriage_label: pm.carriageLabel" in state
    assert re.search(r'<p class="vh" id="runNote" hidden>', template)
    assert 'note.textContent = notes.join(" ");' in script  # every shown run's note
    assert 'const notes = panelRuns.filter(r => r.note).map(r => r.name + ": " + r.note);' in script
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
    # the fourth argument (step A6v) is the footer lines; absent, the frame is A3b's
    assert capture.startswith("  function captureFrame(t, width, height, footerLines) {")
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
    the separated bodies' labels say their coasts are drawn (step A3b draws them); no impact
    'at the mouth level' (the model's ground is altitude 0)."""
    script = _script(template)
    closeup = _function_source(template, "drawCloseup")[0]
    assert "ly - half >= draw.y && ly + half <= draw.y + draw.h" in closeup
    assert "lx + lw + CLOSEUP_LABEL_CLEAR_PX <= draw.x + draw.w" in closeup
    assert "closeup_carriage_label: pm.closeup.carriageLabel" in script
    # step A3b: the title's second line says which change made the stack shorter
    assert "closeupScaleText(L)" in closeup
    scale = _function_source(template, "closeupScaleText")[0]
    assert "L.cf.why" in scale and "CAM.closeup_stack_px / L.kc" in scale
    frame = _function_source(template, "closeupFrame")[0]
    for why in (
        '"after the fairing drop"',
        '"after staging"',
        '"own scale"',
        '"zooming in for staging"',
        '"zooming in for the fairing"',
        '"fairing halves opening"',
        '"fairing halves leaving"',
    ):
        assert why in frame, why
    assert "scale changes at staging and at the fairing drop" in template
    # A3b review round 3: the title is drawn as fitted (cut to the box, ending in ...) and the
    # hook reports what is drawn; no reason is long enough to cut the scale it states (the QA
    # record's dense #qa states count none ending in ...)
    assert (
        "closeupScaleText(L)].map(s => fitText(ctx, s, box.w - 2 * CLOSEUP_TEXT_INSET_PX));"
        in closeup
    )
    assert "ctx.fillText(s, box.x + CLOSEUP_TEXT_INSET_PX" in closeup
    assert "painted.title = title;" in closeup
    assert "zooming in for the fairing drop" not in script
    clamps = _function_source(template, "drawClamps")[0]
    assert 'firstEventT(run, "liftoff")' in clamps and "open = t >= 0" not in clamps
    assert "drawClamps(ctx, t, pal, L, run);" in script
    assert 'HOLD: "Held down", ' in script and "engines ramping" not in script
    ticker = _function_source(template, "buildTicker")[0]
    assert "impactNote(run)" in ticker and "IMPACT_TICKER_NOTE" in ticker
    assert "no contact with the carriage, the mouth or the shaft" in script
    assert (
        '(r.yardstick === true ? YARDSTICK_MARK : "")' in _function_source(template, "runOption")[0]
    )
    # step A3b draws the separated bodies: every label says the coast is drag-free and display-only
    body = _function_source(template, "drawBodyMarker")[0]
    assert '": drag-free coast (display only)"' in body
    # the short label too: it keeps "display only" (A3b fix round 4), and "drag-free" wherever it
    # states an impact time or a stop (A3b review round 3)
    (short,) = re.findall(r"const short = (.*);", body)
    pieces = re.findall(r'"([^"]*)"', short)
    assert short.startswith('tag + " (display only)" + '), short
    stated = [piece for piece in pieces if "impact" in piece or "stopped" in piece]
    assert len(stated) == 2 and all("drag-free" in piece for piece in stated), pieces
    assert "drawn coast" not in script
    assert '"Close-up: shapes drawn, not computed"' in script
    assert "Not model output: separated bodies' dashed drag-free coasts." in script
    assert "spent stage 1" in script and "fairing halves" in script
    assert "fairing paths" not in template
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


# ------------------------------------------------------------------ step A3b: two panels, the rate


def _run_pure(template: str, harness: str, case: dict[str, Any], tmp_path: Path) -> Any:
    """The page's pure block plus a harness, run under node on ``case`` (JSON); its output."""
    data_file = tmp_path / "case.json"
    data_file.write_text(json.dumps(case), encoding="utf-8")
    js = tmp_path / "a3b.js"
    js.write_text(_pure_block(template) + harness, encoding="utf-8")
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
    return json.loads(proc.stdout)


def _event(name: str, stage: str, t: float) -> dict[str, Any]:
    return {"name": name, "stage": stage, "t": t}


PAD_LIKE = {
    # a pad as the recorded pad of results/silo_screening_2d logs it (times after release)
    "start": -2.0,
    "stages": ["stage1", "stage2"],
    "events": [
        _event("ignition", "stage1", -2.0),
        _event("release", "stage1", 0.0),
        _event("liftoff", "stage1", 0.0),
        _event("ramp_end", "stage1", 0.0),
        _event("kick_start", "stage1", 12.493729),
        _event("kick_end", "stage1", 17.774014),
        _event("propellant", "stage1", 151.328438),
        _event("staging", "stage2", 151.328438),
        _event("ignition", "stage2", 162.328438),
        _event("fairing", "stage2", 196.807531),
        _event("cutoff", "stage2", 536.300685),
        _event("end", "stage2", 536.300685),
    ],
}
SILO_LIKE = {
    # a cold silo start as silo_cold_s1 of results/silo_offload_2d logs it
    "start": -2.607318,
    "stages": ["stage1", "stage2"],
    "events": [
        _event("push_start", "stage1", -2.607318),
        _event("release", "stage1", 0.0),
        _event("ignition", "stage1", 0.5),
        _event("kick_start", "stage1", 0.5),
        _event("ramp_end", "stage1", 2.5),
        _event("kick_end", "stage1", 7.948339),
        _event("propellant", "stage1", 138.531493),
        _event("staging", "stage2", 138.531493),
        _event("ignition", "stage2", 149.531493),
        _event("fairing", "stage2", 184.250483),
        _event("cutoff", "stage2", 523.503743),
        _event("end", "stage2", 523.503743),
    ],
}
PAD_CONTROL_LIKE = {
    # a pad control that ends by stage-2 depletion short of orbit (pad__offload_stage1 of
    # results/silo_offload_2d): propellant and end on stage 2, no cutoff
    "start": -2.0,
    "stages": ["stage1", "stage2"],
    "events": [
        *PAD_LIKE["events"][:9],
        _event("fairing", "stage2", 196.807531),
        _event("propellant", "stage2", 536.300687),
        _event("end", "stage2", 536.300687),
    ],
}
FAILED_LIKE = {
    # a failed ignition that falls back (silo_failed)
    "start": -2.607318,
    "stages": ["stage1", "stage2"],
    "events": [
        _event("push_start", "stage1", -2.607318),
        _event("release", "stage1", 0.0),
        _event("ignition_failed", "stage1", 0.0),
        _event("apex", "stage1", 7.842648),
        _event("impact", "stage1", 15.689059),
        _event("end", "stage1", 15.689059),
        {"name": "unknown_time", "stage": "stage1", "t": None},
    ],
}
RATE_HARNESS = """
const fs = require("fs");
const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = {};
const dt = 0.01;
input.cases.forEach(c => {
  const sched = rateSchedule(c.runs, c.zoom || null);
  const t1 = Math.max(...c.ends);
  const samples = [];
  for (let k = 0; ; k++) {
    const t = c.start + k * dt;
    if (t > t1) break;
    samples.push([t, rateLaw(t, sched)]);
  }
  const wall = (a, b) => {
    let w = 0;
    const n = Math.ceil((b - a) / 0.001), h = (b - a) / n;
    for (let i = 0; i < n; i++) w += h / rateLaw(a + (i + 0.5) * h, sched);
    return w;
  };
  out[c.name] = {
    sched: sched, samples: samples, at: c.at.map(t => rateLaw(t, sched)),
    windows: c.windows.map(e => wall(e - 2, e + 3)), total: wall(c.start, t1)
  };
});
out.empty = rateSchedule([]);
process.stdout.write(JSON.stringify(out));
"""
ZOOM_GROWTH_PER_S = 0.05
"""The synthetic zoom case: ln H grows this much per scene second from 20 s to 120 s."""
ZOOM_SAMPLES = [
    [
        float(t),
        1000.0
        * math.exp(ZOOM_GROWTH_PER_S * min(max(t - 20, 0), 100))
        * 2.0 ** min(max(t - 300, 0), 5),
    ]
    for t in range(-2, 537)
]
RATE_STEP_TOL = 0.01
"""The largest relative change of the Auto rate between samples 0.01 s apart outside the
named step at the last stage-1 ramp end (0.5x to 1x): the rate rises and eases with no step."""
WATCH_WALL_S = 1.5
"""Exit criterion 16: staging, stage-2 ignition and the fairing drop each stay on screen at
least this many wall seconds under the default rate ([event - 2 s, event + 3 s])."""


@pytest.mark.skipif(NODE is None, reason="node not installed: page functions not run")
def test_rate_law_under_node(template: str, tmp_path: Path) -> None:
    """The Auto rate (D-SP2-21 as amended; design review 06 finding 2) on the events of a
    pad and a cold silo start shaped as the recorded runs: 0.5x from the first row to the
    last stage-1 ramp end, 1x through each run's kick (to its kick end, or 2 s after its
    kick start when that comes first: review round 3), a geometric rise (ln rate linear in
    scene time) to 30x, held at 3x from 2 s before the first MECO to 3 s after the last
    stage-2 ignition and within 3 s of each fairing drop and cutoff, and at 2x within 3 s
    of each fairing drop; never a step above 1% between samples 0.01 s apart except the
    named one at the ramp end; staging and stage-2 ignition play [e - 2 s, e + 3 s] in
    5/3 wall seconds and each fairing drop in 2.5 (criterion 16: at least 1.5). A failed
    ignition alone has no ramp or kick end (the release stands for
    both) and is held near its impact; an event with no time is ignored. The page uses the
    law for Auto only, from the shown runs, and the hook reports it."""
    ends_pair = [536.300685, 523.503743]
    case = {
        "cases": [
            {
                "name": "pair",
                "runs": [PAD_LIKE, SILO_LIKE],
                "start": -2.607318,
                "ends": ends_pair,
                "at": [
                    -2.6,
                    0.0,
                    2.499,
                    2.5,
                    10.0,
                    14.4937,
                    14.493729,
                    17.774,
                    25.0,
                    44.493729,
                    60.0,
                    100.0,
                    136.531493,
                    150.0,
                    165.328438,
                    181.250483,
                    184.25,
                    187.250483,
                    196.807531,
                    300.0,
                    520.503743,
                    523.503743,
                    536.300685,
                ],
                "windows": [151.328438, 162.328438, 196.807531, 138.531493, 149.531493, 184.250483],
            },
            {
                # a run that ends by depletion is held at its end (no cutoff, no impact)
                "name": "depletion",
                "runs": [SILO_LIKE, PAD_CONTROL_LIKE],
                "start": -2.607318,
                "ends": [523.503743, 536.300687],
                "at": [536.300687 - 3, 536.300687],
                "windows": [],
            },
            {
                # the softer cap at each run's max-Q
                "name": "maxq",
                "runs": [{**PAD_LIKE, "maxq": 65.75}, {**SILO_LIKE, "maxq": 52.992682}],
                "start": -2.607318,
                "ends": ends_pair,
                "at": [65.75, 52.992682, 55.0, 75.0, 100.0],
                "windows": [],
            },
            {
                # the zoom cap: the view height grows 5% per scene second from 20 s to 120 s, and
                # doubles every second from 300 s to 305 s (the cap is floored at 1x)
                "name": "zoom",
                "runs": [PAD_LIKE],
                "start": -2.0,
                "ends": [536.300685],
                "zoom": ZOOM_SAMPLES,
                "at": [70.0, 302.5, 17.774014, 400.0],
                "windows": [],
            },
            {
                "name": "failed",
                "runs": [FAILED_LIKE],
                "start": -2.607318,
                "ends": [15.689059],
                "at": [-1.0, 0.0, 5.0, 12.689059, 15.689059],
                "windows": [],
            },
        ]
    }
    out = _run_pure(template, RATE_HARNESS, case, tmp_path)
    pair = out["pair"]
    sched = pair["sched"]
    # the pad's kick is a step at its start (12.493729 s): 1x until 2 s after it, not to its
    # kick end (17.774014 s); the silo's kick ends (7.95 s) after its start + 2 s (2.5 s)
    assert sched["rampEnd"] == pytest.approx(2.5) and sched["kickEnd"] == pytest.approx(14.493729)
    holds = sorted(tuple(h) for h in sched["holds"])
    assert holds == pytest.approx(
        sorted(
            [
                (138.531493 - 2, 162.328438 + 3),  # first MECO - 2 to last stage-2 ignition + 3
                (184.250483 - 3, 184.250483 + 3),
                (196.807531 - 3, 196.807531 + 3),
                (523.503743 - 3, 523.503743 + 3),
                (536.300685 - 3, 536.300685 + 3),
            ]
        )
    )
    at = dict(zip(case["cases"][0]["at"], pair["at"], strict=True))
    assert at[-2.6] == 0.5 and at[0.0] == 0.5 and at[2.499] == 0.5  # the push and the ramp
    assert at[2.5] == 1 and at[10.0] == 1 and at[14.4937] == 1  # through the kicks
    assert at[14.493729] == pytest.approx(1.0)  # the rise starts at 1x: no step
    assert 1 < at[17.774] < 2  # the pad's held tilt after its kick step plays a little faster
    assert 1 < at[25.0] < 30 and at[44.493729] == pytest.approx(30.0)  # 30 s rise, geometric
    assert at[60.0] == pytest.approx(30.0) and at[100.0] == pytest.approx(30.0)
    for t in (136.531493, 150.0, 165.328438, 520.503743, 523.503743, 536.300685):
        assert at[t] == pytest.approx(3.0), t  # held at 3x
    for t in (181.250483, 184.25, 187.250483, 196.807531):
        assert at[t] == pytest.approx(2.0), t  # the fairing drops at 2x
    assert 3 < at[300.0] <= 30
    # geometric: ln rate is linear in time on the rise (equal ratios over equal steps)
    rise = [r for t, r in pair["samples"] if 15.0 <= t <= 40.0]
    ratios = [b / a for a, b in itertools.pairwise(rise)]
    assert max(ratios) == pytest.approx(min(ratios), rel=1e-9)
    # no step but the named one, anywhere
    steps = [
        (t0, abs(r1 / r0 - 1))
        for (t0, r0), (_, r1) in itertools.pairwise(pair["samples"])
        if not (t0 < sched["rampEnd"] <= t0 + 0.0101)
    ]
    worst = max(steps, key=lambda s: s[1])
    assert worst[1] < RATE_STEP_TOL, worst
    assert all(0.5 <= r <= 30.0 + 1e-9 for _, r in pair["samples"])
    fairings = (196.807531, 184.250483)
    for e, wall_s in zip(case["cases"][0]["windows"], pair["windows"], strict=True):
        assert wall_s >= WATCH_WALL_S, (e, wall_s)
        assert wall_s == pytest.approx(5.0 / (2.0 if e in fairings else 3.0), rel=1e-3), e
    fairing_caps = sorted(c for c in sched["caps"] if c[2] == 2)
    assert [x for c in fairing_caps for x in c] == pytest.approx(
        [181.250483, 187.250483, 2, 193.807531, 199.807531, 2]
    )
    failed = out["failed"]
    assert failed["sched"]["rampEnd"] == 0.0 and failed["sched"]["kickEnd"] == 0.0
    assert failed["sched"]["holds"] == [pytest.approx([12.689059, 18.689059])]
    # no kick: the rise starts at the release
    assert failed["at"][0] == 0.5 and failed["at"][1] == pytest.approx(1.0)
    assert 1 < failed["at"][2] < 3 and failed["at"][3] == pytest.approx(3.0)
    assert failed["at"][4] == pytest.approx(3.0)
    assert out["empty"] == {"start": 0, "rampEnd": 0, "kickEnd": 0, "holds": [], "caps": []}
    # a run that ends by depletion short of orbit is held at its end like a cutoff (review 06
    # finding 2: the run's end), and an end at a cutoff or impact adds no second hold
    depletion = out["depletion"]
    assert depletion["at"] == pytest.approx([3.0, 3.0])
    assert sorted(tuple(h) for h in depletion["sched"]["holds"])[-1] == pytest.approx(
        (536.300687 - 3, 536.300687 + 3)
    )
    assert len(pair["sched"]["holds"]) == 5 and len(failed["sched"]["holds"]) == 1
    # max-Q: at most RATE_MAXQ within 5 s of each, easing back with no step
    maxq = out["maxq"]
    assert maxq["at"][0] == pytest.approx(5.0) and maxq["at"][1] == pytest.approx(5.0)
    assert maxq["at"][2] <= 5.0 + 1e-9 and 5.0 < maxq["at"][3] < 30.0
    assert maxq["at"][4] == pytest.approx(30.0)
    caps = sorted(c[:2] for c in maxq["sched"]["caps"] if c[2] == 5)
    assert [x for c in caps for x in c] == pytest.approx(
        [52.992682 - 5, 52.992682 + 5, 65.75 - 5, 65.75 + 5]
    )
    # the zoom cap: the view height grows at most 1.3-fold per wall second where it binds, and
    # never slows the playback under 1x
    zoom = out["zoom"]
    assert zoom["at"][0] == pytest.approx(math.log(1.3) / ZOOM_GROWTH_PER_S, rel=1e-9)
    assert zoom["at"][1] == pytest.approx(1.0) and zoom["at"][2] <= 1.5
    assert zoom["at"][3] == pytest.approx(30.0)
    for t, r in zoom["samples"]:
        if 20.0 < t < 120.0:
            assert r * ZOOM_GROWTH_PER_S <= math.log(1.3) + 1e-9, t
    for name in ("depletion", "maxq", "zoom"):
        sched_n = out[name]["sched"]
        worst_n = max(
            abs(r1 / r0 - 1)
            for (t0, r0), (_, r1) in itertools.pairwise(out[name]["samples"])
            if not (t0 < sched_n["rampEnd"] <= t0 + 0.0101)
        )
        assert worst_n < RATE_STEP_TOL, name

    script = _script(template)
    rate_at = _function_source(template, "rateAt")[0]
    assert "return rateLaw(t, SCHED);" in rate_at and 'if (sel !== "auto")' in rate_at
    assert (
        "SCHED = rateSchedule(panelRuns.map(r => "
        "({ start: r.t[0], stages: r.tanks.stage_names, events: r.events, "
        "maxq: r.maxq ? r.maxq.t : null })), zoomSamples(panelRuns));"
    ) in script
    assert "rate: rateAt(sceneT), rate_auto: rateLaw(sceneT, SCHED)" in script
    options = re.findall(r'<option value="([^"]+)"', template)
    (choices,) = re.findall(r"const RATE_CHOICES = \[([^\]]*)\];", script)
    assert options == ["auto", *(c.strip() for c in choices.split(","))]
    assert options == ["auto", "0.25", "0.5", "1", "5", "20", "60"]


@pytest.mark.skipif(NODE is None, reason="node not installed: page functions not run")
def test_default_pair_one_run_layout_and_shared_camera_under_node(
    template: str, run_dir: Path, payload: dict[str, Any], tmp_path: Path
) -> None:
    """Two panels on one clock and one camera (design 4.5; review 06 findings 4 and 12).
    The payload carries D-SP2-28's pair for the runs it holds (scene.default_pair: the
    baseline left, the assisted variant right, whatever the selection's order; one run when
    it holds one), and the page opens on it unless #runs names runs; a one-run payload (or
    pair) gives one full-width panel. Two panels sit side by side from 900 px of canvas
    width, else one above the other, in boxes of one size, matching the CSS's container
    rules. The camera is shared: its view height is the camera law's at the larger extent
    (display.view_height_m), centred on the union of what each run's own camera frames, so
    one run gives A3's camera unchanged; a panel whose run has ended is drawn at its last
    row with the shared camera of that time. Review round 3: the camera frames the part of
    the view right of the close-up's column (the content box centred there, the law's view
    height over the frame's height, so the launch site and the vehicle lie in the frame and
    never under the close-up); the rocket is drawn to scale while its body is at least the
    configured 3 px wide (vehicleMode), which the camera crosses where the law's view height
    reaches the frame's height times the body width over 3 px."""
    assert payload["default_pair"] == ["pad", "silo_failed"]
    flipped = scene.scene_payload(run_dir, ["silo_failed", "pad"], display_dir=DISPLAY_DIR)
    assert [r["key"] for r in flipped["runs"]] == ["silo_failed", "pad"]
    assert flipped["default_pair"] == ["pad", "silo_failed"]
    alone = scene.scene_payload(run_dir, ["silo_failed"], display_dir=DISPLAY_DIR)
    assert alone["default_pair"] == ["silo_failed"]
    # an explicit selection the rule finds fewer than two in is filled from it in order
    assert scene.opening_pair({"baseline": "pad"}, {}, ["x", "y"]) == ["x", "y"]
    assert scene.opening_pair({"baseline": "pad"}, {}, ["x"]) == ["x"]
    assert scene.opening_pair({"baseline": "pad"}, {}, ["x", "pad", "y"]) == ["pad", "x"]

    names = ["pad", "silo_cold", "silo_hot", "silo_failed"]
    scene_cfg = scene.load_scene_config(DISPLAY_DIR)
    h_min = scene_cfg.camera.min_view_height_m.value
    margin = scene_cfg.camera.margin.value
    a = {"E": 260.0, "x": 0.0, "y": -100.0, "floor": -100.0, "L": 70.0}
    b = {"E": 1200.0, "x": 25.0, "y": 900.0, "floor": 0.0, "L": 70.0}
    harness = """
const fs = require("fs");
const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = {};
out.pairs = input.pairs.map(p => initialPair(p[0], p[1], p[2]));
out.boxes = input.boxes.map(b => panelBoxes(b[0], b[1], 900, 12));
const cam = { min_view_height_m: input.hMin, margin: input.margin };
const view = { x: 0, y: 0, w: 600, h: 430 }, a = input.a;
out.one = sharedCamera([a], cam, view);
out.oneA3 = cameraView(a.E, cam, view, { xMin: Math.min(0, a.x), xMax: Math.max(0, a.x),
  yMin: Math.min(a.floor, a.y), yMax: Math.max(0, a.y) + a.L });
out.ab = sharedCamera([input.a, input.b], cam, view);
out.ba = sharedCamera([input.b, input.a], cam, view);
const frame = { x: 256, y: 0, w: 344, h: 430 };
out.framed = input.frames.map(f => sharedCamera(f, cam, view, frame));
out.inFrame = input.frames.map((f, k) => {
  const c = out.framed[k];
  const px = (x, y) => [view.x + (x - c.x0) * c.ppm, view.y + view.h - (y - c.y0) * c.ppm];
  const tops = f.map(it => px(it.x, Math.max(0, it.y) + it.L));
  return [px(0, 0)].concat(f.map(it => px(it.x, it.y)), tops);
});
out.modes = [vehicleMode(3.66, 3 / 3.66, 3), vehicleMode(3.66, 2.999 / 3.66, 3),
  vehicleMode(3.66, 0.4, 3)];
const box0 = { xMin: 0, xMax: 0, yMin: 0, yMax: 0 };
const eOf = h => Math.sqrt(Math.max(0, h * h - cam.min_view_height_m ** 2)) / cam.margin;
const hAt = h => cameraView(eOf(h), cam, view, box0, frame);
out.cross = [hAt(frame.h * 3.66 / 3 * 0.999), hAt(frame.h * 3.66 / 3 * 1.001)]
  .map(c => vehicleMode(3.66, c.ppm, 3));
process.stdout.write(JSON.stringify(out));
"""
    case = {
        "pairs": [
            [names, ["pad", "silo_cold"], []],
            [names, ["pad", "silo_cold"], ["silo_failed", "pad"]],
            [names, ["pad", "silo_cold"], ["silo_failed"]],
            [["pad"], ["pad"], []],  # a one-run payload: one panel
            [names, ["pad"], []],  # D-SP2-28 found no right-hand run: one panel
            [names, [], []],
            [names, None, []],
            [names, ["gone", "silo_cold"], []],
            [names, ["pad", "pad"], []],
        ],
        "boxes": [
            [{"x": 0, "y": 0, "w": 1222, "h": 560}, 1],
            [{"x": 0, "y": 0, "w": 1222, "h": 560}, 2],
            [{"x": 0, "y": 0, "w": 900, "h": 900}, 2],
            [{"x": 0, "y": 0, "w": 899.5, "h": 1012}, 2],
        ],
        "hMin": h_min,
        "margin": margin,
        "a": a,
        "b": b,
        # what each run's own camera frames, in the frame right of the close-up's column: the
        # vertical rise, the gravity turn and orbit (the screen x and y of each run's base [m])
        "frames": [
            [{"E": 300.0, "x": 0.0, "y": 200.0, "floor": -100.0, "L": 70.0}],
            [
                {"E": 9.0e4, "x": 6.0e4, "y": 4.0e4, "floor": 0.0, "L": 70.0},
                {"E": 7.0e4, "x": 3.0e4, "y": 3.0e4, "floor": -100.0, "L": 70.0},
            ],
            [{"E": 2.0e6, "x": 1.66e6, "y": -2.1e4, "floor": 0.0, "L": 70.0}],
        ],
    }
    out = _run_pure(template, harness, case, tmp_path)
    assert out["pairs"] == [
        ["pad", "silo_cold"],
        ["silo_failed", "pad"],
        ["silo_failed", None],
        ["pad", None],
        ["pad", None],
        ["pad", None],
        ["pad", None],
        ["silo_cold", None],
        ["pad", None],
    ]
    one, side, edge, stacked = out["boxes"]
    assert one == [{"x": 0, "y": 0, "w": 1222, "h": 560}]
    assert side == [
        {"x": 0, "y": 0, "w": 605, "h": 560},
        {"x": 617, "y": 0, "w": 605, "h": 560},
    ]
    assert edge[1]["y"] == 0 and edge[1]["x"] == pytest.approx(456.0)  # from 900 px: side by side
    assert stacked == [
        {"x": 0, "y": 0, "w": 899.5, "h": 500},
        {"x": 0, "y": 512, "w": 899.5, "h": 500},
    ]
    assert out["one"] == pytest.approx(out["oneA3"], rel=1e-12)  # one run: A3's camera
    assert out["ab"] == pytest.approx(out["ba"], rel=1e-12)  # one camera for both panels
    shared = out["ab"]
    assert shared["H"] == pytest.approx(float(display.view_height_m(1200.0, h_min, margin)))
    assert shared["ppm"] == pytest.approx(430.0 / shared["H"])
    assert shared["x0"] + shared["W"] / 2 == pytest.approx(12.5)  # centred on 0 .. 25 m
    assert shared["y0"] + shared["H"] / 2 == pytest.approx((-100.0 + 970.0) / 2)
    # the frame: the law's view height over the frame's height, the content centred in it, so
    # the site, each vehicle and its nose lie right of the close-up's column (x >= 256 px)
    for framed, points, items in zip(out["framed"], out["inFrame"], case["frames"], strict=True):
        e = max(it["E"] for it in items)
        assert framed["H"] == pytest.approx(float(display.view_height_m(e, h_min, margin)))
        assert framed["ppm"] == pytest.approx(430.0 / framed["H"])
        for x, y in points:
            assert 256.0 <= x <= 600.0 and 0.0 <= y <= 430.0, (x, y)
    assert out["modes"] == ["to_scale", "marker", "marker"]
    assert out["cross"] == ["to_scale", "marker"]  # crossing where H = frame.h x D / 3 px

    script = _script(template)
    assert "const pair = initialPair(names, DATA.default_pair, hash.runs);" in script
    assert (
        "const f = frame || view, aspect = f.w / f.h;" in _function_source(template, "cameraAt")[0]
    )
    assert 'cv.classList.toggle("two", panelRuns.length > 1);' in script
    frames = _function_source(template, "sceneFrames")[0]
    assert "frozen = t > end + EVENT_EPS_S, ti = frozen ? end : t;" in frames
    assert "cam: cameraAt(ti, prs, lays[i].view, lays[i].frame)" in frames
    assert (
        "const mode = vehicleMode(g.vehicle.body_diameter_m, cam.ppm, CAM.to_scale_min_body_px);"
        in _function_source(template, "viewPoints")[0]
    )
    assert "const vp = viewPoints(run, st, view, cam);" in _function_source(template, "layoutAt")[0]
    layout = _function_source(template, "panelLayout")[0]
    assert "frameOf = v => ({ x: v.x + col, y: v.y, w: Math.max(1, v.w - col), h: v.h })" in layout
    for mode in ('mode: "column"', 'mode: "overlay"', 'mode: "side"', 'mode: "band"'):
        assert mode in layout, mode
    camera_at = _function_source(template, "cameraAt")[0]
    assert "const tr = Math.min(t, lastT(r))" in camera_at and "sharedCamera(prs.map(" in camera_at
    shared_lay = _function_source(template, "sharedLayouts")[0]
    assert "noteLines: Math.max(" in shared_lay and "bandH: Math.max(" in shared_lay
    (two_up,) = re.findall(r"const TWO_UP_MIN_PX = (\d+);", script)
    (gap,) = re.findall(r"const PANEL_GAP_PX = (\d+);", script)
    (narrow,) = re.findall(r"const NARROW_VIEW_PX = (\d+);", script)
    style = template[: template.index("</style>")]
    rules = re.findall(
        r"@container scenepanel \(width < (\d+)px\) \{\s*#scene\.two \{ height: ([^;]*);", style
    )
    assert [int(w) for w, _ in rules] == [2 * int(narrow) + int(gap), int(two_up), int(narrow)]
    assert rules[0][1] == "clamp(900px, 125vh, 1300px)"  # side by side, each panel a band layout
    assert rules[1][1].startswith("calc(2 * ") and rules[1][1].endswith(f" + {gap}px)")  # stacked
    assert rules[2][1] == f"calc(2 * clamp(900px, 125vh, 1300px) + {gap}px)"


SEPARATION_HARNESS = """
const fs = require("fs");
const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = {};
out.gap = input.gapAt.map(t => stagingGapPx(t, 11, 160));
out.gapNull = stagingGapPx(5, null, 160);
let worstGap = 0;
for (let t = 0; t < 13; t += 0.01) {
  const step = Math.abs(stagingGapPx(t + 0.01, 11, 160) - stagingGapPx(t, 11, 160));
  worstGap = Math.max(worstGap, step);
}
out.worstGap = worstGap;
out.open = input.openAt.map(fairingOpen);
let worstOpen = 0;
for (let t = 0; t < 4; t += 0.01) {
  worstOpen = Math.max(worstOpen, Math.abs(fairingOpen(t + 0.01).angle - fairingOpen(t).angle));
}
out.worstOpen = worstOpen;
out.labels = input.labels.map(c => placeLabels(c.items, c.taken, c.bounds, 4));
out.free = firstFree(input.free.c, input.free.taken, input.free.bounds);
const four = [0, 0.5, 2.5, 7.9], two = [0, 0.5];
out.next = [neighbourTime(four, 0.5, 1, 1e-6), neighbourTime(four, 0.5, -1, 1e-6),
  neighbourTime(two, 0.5, 1, 1e-6), neighbourTime(two, 0.4999995, 1, 1e-6),
  neighbourTime(two, 0.49, 1, 1e-6), neighbourTime([], 1, -1, 1e-6)];
// the fairing halves in the close-up's drawing (side x side px, the axis at its centre) while
// they are drawn: their least margin to its edges and to the top of its caption plate
const h = input.halves, v = h.v, side = h.side, capTop = side - h.capGap - h.capH;
const preL = v.stage2_length_m + v.fairing_length_m;
const postL = v.stage2_length_m + h.stub * v.fairing_length_m;
const fr = halvesFrame(preL, postL, v.stage2_length_m, h.stack, h.minStack, h.hinge);
const D = v.body_diameter_m, Df = Math.max(D, v.fairing_diameter_m);
const dims = { u0: v.stage2_length_m, half: D / 2, dy: Df / 2 - D / 2, F: v.fairing_length_m,
  flare: h.flare, cylinder: h.cyl };
const halves = { edge: Infinity, caption: Infinity, n: 0 };
for (let deg = h.axes[0]; deg <= h.axes[1] + 1e-9; deg += 0.25) {
  const a = deg * Math.PI / 180, dir = [Math.cos(a), -Math.sin(a)];
  for (let tau = 0; tau <= h.show + 1e-9; tau += 0.05) {
    fairingHalves(fairingOpen(tau), dims, fr.kc).forEach(q => halfReach(q).forEach(p => {
      const u = p[0] - fr.up * fr.kc;
      const x = side / 2 + u * dir[0] - p[1] * dir[1], y = side / 2 + u * dir[1] + p[1] * dir[0];
      halves.edge = Math.min(halves.edge, x, y, side - x, side - y);
      halves.caption = Math.min(halves.caption, capTop - y);
      halves.n++;
    }));
  }
}
out.halves = halves;
process.stdout.write(JSON.stringify(out));
"""


def _page_number(script: str, name: str) -> float:
    (value,) = re.findall(rf"const {name} = ([0-9.]+);", script)
    return float(value)


def _halves_case(template: str, payload: dict[str, Any]) -> dict[str, Any]:
    """The close-up's fairing-halves drawing as the page sizes it, for the fixture's vehicle:
    the drawing's side (closeupSide), the caption plate (two lines of 11 px text, its bottom
    CLOSEUP_CAPTION_TOP_PX over the drawing's), the halves' framing constants and the axes."""
    script = _script(template)
    stack = float(payload["camera"]["closeup_stack_px"])
    plume = float(payload["drawing"]["plume_of_stack"])
    pad = _page_number(script, "CLOSEUP_PAD_PX")
    font = _page_number(script, "FONT_SMALL_PX")
    line = round(font * _page_number(script, "PLATE_LINE_OF_FONT"))
    cap_h = 2 * line + 2 * _page_number(script, "PLATE_PAD_PX") - (line - font)
    return {
        "v": payload["display"]["vehicle"],
        "side": (1 + plume) * stack + 2 * pad,
        "capH": cap_h,
        "capGap": _page_number(script, "CLOSEUP_CAPTION_TOP_PX"),
        "stack": stack,
        "minStack": _page_number(script, "CLOSEUP_MIN_STACK_PX"),
        "hinge": _page_number(script, "FAIRING_HINGE_BACK_PX"),
        "stub": _page_number(script, "PAYLOAD_STUB_OF_FAIRING"),
        "flare": _page_number(script, "FAIRING_FLARE"),
        "cyl": _page_number(script, "FAIRING_CYLINDER"),
        "show": _page_number(script, "FAIRING_SHOW_S"),
        "axes": list(HALVES_AXES_DEG),
    }


def _inside(r: dict[str, float], b: dict[str, float]) -> bool:
    return (
        r["x"] >= b["x"]
        and r["y"] >= b["y"]
        and r["x"] + r["w"] <= b["x"] + b["w"]
        and (r["y"] + r["h"] <= b["y"] + b["h"])
    )


def _hit(p: dict[str, float], q: dict[str, float]) -> bool:
    return (
        p["x"] < q["x"] + q["w"]
        and q["x"] < p["x"] + p["w"]
        and p["y"] < q["y"] + q["h"]
        and (q["y"] < p["y"] + p["h"])
    )


HALVES_AXES_DEG = (22.0, 33.0)
"""Close-up axes [deg above the local horizontal] the fairing halves are checked over: the
recorded fairing drops of results/silo_offload_2d and silo_screening_2d draw them at 28.4 to
29.0 deg (A3b QA, round 3), and a few degrees either side."""
HALVES_CLEAR_PX = 0.75
"""The least margin [px] of the halves to the drawing's edges and to the caption plate: over
half the 1.25 px outline."""


@pytest.mark.skipif(NODE is None, reason="node not installed: page functions not run")
def test_separations_labels_and_event_steps_under_node(
    template: str, payload: dict[str, Any], tmp_path: Path
) -> None:
    """The close-up's drawn separations (design 4.9: drawn, not computed): the staging gap
    opens linearly over the coast to 0.4 of the drawn stack, then grows with the square of
    the time since stage-2 ignition, continuously (no jump over 1 px in 0.01 s); the
    fairing halves turn out to 25 deg over 1.5 s, slide back and drift apart, continuously.
    The halves stay wholly inside the close-up's drawing and clear of its caption plate for the
    first FAIRING_SHOW_S after the drop (after it they may slide out across its edge: fix round 4
    draws them on until they have wholly left it), at the
    close-up axes of the recorded fairing drops and a few degrees round them (review round 3:
    their hinge behind the drawing's centre, a slower slide). At MECO the
    close-up frames the stage-1 engines at the scale that draws stage 2 at least 121 px long,
    then pans to stage 2 after the separation; the spent stage carries a tag.
    Label plates lie inside the view and over no plate, marker or other label, or are left
    out; previous and next event step by the clock. The page names the drawings so: the
    close-up's captions, the bodies' labels and the markers' sizes (criterion 16: at least
    4 px across)."""
    case = {
        "gapAt": [-1.0, 0.0, 5.5, 11.0, 13.0],
        "openAt": [0.0, 0.75, 1.5, 2.0, 4.0],
        "labels": [
            {
                # a marker by the view's right edge, with a plate to its lower left
                "items": [
                    {"x": 590.0, "y": 200.0, "r": 6.0, "w": 150.0, "h": 19.0},
                    {"x": 588.0, "y": 204.0, "r": 6.0, "w": 120.0, "h": 19.0},
                    {"x": 300.0, "y": 100.0, "r": 6.0, "w": 140.0, "h": 19.0},
                ],
                "taken": [{"x": 400.0, "y": 205.0, "w": 120.0, "h": 60.0}],
                "bounds": {"x": 5.0, "y": 5.0, "w": 595.0, "h": 420.0},
            },
            {
                # no room anywhere
                "items": [{"x": 50.0, "y": 50.0, "r": 6.0, "w": 150.0, "h": 19.0}],
                "taken": [{"x": 0.0, "y": 0.0, "w": 100.0, "h": 100.0}],
                "bounds": {"x": 0.0, "y": 0.0, "w": 100.0, "h": 100.0},
            },
        ],
        "free": {
            "c": [{"x": 0, "y": 0, "w": 10, "h": 10}, {"x": 20, "y": 0, "w": 10, "h": 10}],
            "taken": [{"x": 5, "y": 5, "w": 2, "h": 2}],
            "bounds": {"x": 0, "y": 0, "w": 40, "h": 40},
        },
        "halves": _halves_case(template, payload),
    }
    out = _run_pure(template, SEPARATION_HARNESS, case, tmp_path)
    assert out["gap"] == pytest.approx([0.0, 0.0, 32.0, 64.0, 64.0 + 20.0 * 4.0])
    assert out["gapNull"] == pytest.approx(64.0)  # no stage-2 ignition: open over 5 s
    assert out["worstGap"] < 1.0
    angles = [o["angle"] for o in out["open"]]
    assert angles == pytest.approx(
        [0.0, math.radians(12.5), math.radians(25.0), math.radians(25.0), math.radians(25.0)]
    )
    assert out["open"][0] == {"angle": 0, "slide": 0, "lateral": 0}
    assert out["open"][3]["slide"] == pytest.approx(0.4) and out["open"][3][
        "lateral"
    ] == pytest.approx(1.2)
    assert out["worstOpen"] < math.radians(1.0)
    for spec, plates in zip(case["labels"], out["labels"], strict=True):
        placed = [p for p in plates if p is not None]
        for p in placed:
            assert _inside(p, spec["bounds"])
            assert not any(_hit(p, q) for q in spec["taken"])
        assert not any(_hit(p, q) for p, q in itertools.combinations(placed, 2))
    first = out["labels"][0]
    assert first[0]["x"] + first[0]["w"] <= 590.0 - 6.0  # left of a marker at the edge
    assert first[2] == {"x": 310.0, "y": 104.0, "w": 140.0, "h": 19.0}  # right and below
    assert out["labels"][1] == [None]
    assert out["free"] == {"x": 20, "y": 0, "w": 10, "h": 10}
    assert out["next"] == [2.5, 0.0, None, None, 0.5, None]  # within 1e-6 s counts as the clock
    halves = out["halves"]
    assert halves["n"] > 1000 and halves["edge"] >= HALVES_CLEAR_PX, halves
    assert halves["caption"] >= HALVES_CLEAR_PX, halves

    script = _script(template)
    frame = _function_source(template, "closeupFrame")[0]
    assert "kcE = CLOSEUP_MIN_STACK_PX / upper.L" in frame  # stage 2 >= 121 px from staging on
    assert "const engines = { kc: kcE, up: ENGINES_BACK_PX / kcE };" in frame
    assert "ease({ kc: kcE, up: engines.up - s1 }, own, tS, tS + STAGING_PAN_S)" in frame
    assert "const hf = halvesFraming(run, g), halves = { kc: hf.kc, up: hf.up };" in frame
    assert (
        "halvesFrame(pre.L, post.L, below + v.stage2_length_m,"
        in (_function_source(template, "halvesFraming")[0])
    )
    assert 'const SPENT_TAG = "spent stage 1: drawn";' in script
    assert "const BODY_MARKER_PX = 9;" in script and "const OTHER_MARKER_PX = 13;" in script
    assert "size_px: BODY_MARKER_PX + RING_PX" in script  # 11 px across (criterion 16: >= 4)
    caption = _function_source(template, "stagingCaption")[0]
    assert '"Gap drawn, not computed: the stages stay within "' in caption
    assert "stg.body.staging_coast_gap_m" in caption
    assert 'const FAIRING_CAPTION = "Fairing halves drawn, not computed: ' in script
    assert "both follow one path" in script
    banner = _function_source(template, "drawBanner")[0]
    assert "endText(run)" in banner
    assert _function_source(template, "endText")[0].count('"Ended "') == 1


def test_controls_capture_and_hook_of_two_panels(template: str) -> None:
    """Previous and next event buttons and the keys [ and ], Left and Right (1 s, 10 s with
    Shift), none of them taken from a form control; every ticker entry jumps to its event;
    the tab's visibility pauses playback from a listener outside the pinned tick, and
    autoplay starts only while the page is visible; captureFrame draws both panels under an
    in-canvas clock band with each panel's phase, at even sides only (a video frame's); the
    hook returns one state per panel, with the rate, the frozen and held flags, the banner
    and what the view painted (the flown path, the event markers, the separated bodies, the
    other panel's vehicle)."""
    script = _script(template)
    assert 'id="prevEvt"' in template and 'id="nextEvt"' in template
    assert 'id="runSel0"' in template and 'id="runSel1"' in template
    for use in (
        'if (e.key === "[") { e.preventDefault(); jumpEvent(-1); }',
        'else if (e.key === "]") { e.preventDefault(); jumpEvent(1); }',
        "stepClock(-(e.shiftKey ? BIG_STEP_S : STEP_S))",
        "stepClock(e.shiftKey ? BIG_STEP_S : STEP_S)",
        "const STEP_S = 1, BIG_STEP_S = 10;",
        'const inControl = ["INPUT", "SELECT", "TEXTAREA"].includes(tag);',
        'b.addEventListener("click", () => jumpTo(t));',
        'document.addEventListener("visibilitychange", () => '
        "{ if (document.hidden && playing) setPlaying(false); });",
        "if (autoplay) setTimeout(startWhenVisible, AUTOPLAY_DELAY_MS);",
    ):
        assert use in script, use
    assert "visibilitychange" not in _function_source(template, "tick")[0]
    start = _function_source(template, "startWhenVisible")[0]
    assert "if (!document.hidden) { setPlaying(true); return; }" in start
    capture = _function_source(template, "captureFrame")[0]
    assert "W % 2 !== 0 || H % 2 !== 0" in capture
    assert (
        "drawCaptureHud(ctx, { x: 0, y: 0, w: W, h: CAPTURE_HUD_PX }, ts, pal, panelRuns);"
        in capture
    )
    assert (
        "sharedLayouts(ctx, pal, panelRuns, "
        "panelBoxes(box, panelRuns.length, TWO_UP_MIN_PX, PANEL_GAP_PX))"
    ) in capture
    hud = _function_source(template, "drawCaptureHud")[0]
    assert "phaseAt(run, Math.min(t, lastT(run)))" in hud and "clockText(t)" in hud
    state = _function_source(template, "panelState")[0]
    for key in (
        "frozen: F.frozen",
        "held_first_row: F.held",
        "banner:",
        "trace_points:",
        "event_marks:",
        "bodies:",
        "others:",
        "staging_gap_px:",
        "fairing_open_deg:",
        "closeup_title:",
        "earth:",
    ):
        assert key in state, key
    assert "return out.map((P, i) => panelState(P, panelRuns[i], t));" in script
    # the two selectors never show one run in both panels
    assert "runs[right] === a ? null" in _function_source(template, "setPanels")[0]
    # the pre-first-row and end labels the readout shows
    assert 'r.pre_label = "Waiting: first recorded row at " + clockText(r.t[0]);' in script
    assert "r.end_label = endText(r);" in script
    assert "if (st.frozen) lines.push(FROZEN_LINE);" in _function_source(template, "hudLines")[0]


def test_run_selector_groups_follow_run_data(template: str) -> None:
    """The selectors group the runs by role (design 4.5) with run_data's own role and offload
    kind strings, so a rename there fails here rather than scattering the runs."""
    script = _script(template)
    block = script[script.index("const ROLE_GROUPS") :]
    block = block[: block.index("];")]
    entries = re.findall(r'\["(\w+)", (null|"[^"]+"), "[^"]+"\]', block)
    assert {role for role, _ in entries} == {
        run_data.ROLE_RUN,
        run_data.ROLE_OFFLOAD,
        run_data.ROLE_CASE,
        run_data.ROLE_BOUND,
        run_data.ROLE_PAIRED_BASELINE,
    }
    assert {kind.strip('"') for _, kind in entries if kind != "null"} == {
        run_data.OFFLOAD_CASE,
        run_data.OFFLOAD_PAIRED_PAD,
        run_data.OFFLOAD_PAD_CONTROL,
    }
    assert "const hit = ROLE_GROUPS.find(" in _function_source(template, "roleGroup")[0]


DISPLAY_HARNESS = """
const fs = require("fs");
const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const f = { clock: t => "T+" + t.toFixed(2) + " s", speed: v => v.toFixed(1),
  length: m => (m / 1000).toFixed(1) + " km" };
const out = {};
out.bodies = input.bodies.map(b => bodyText(b, input.end, Object.assign({ name: b.name }, f)));
out.alias = input.alias.map(a => eventAlias(a[0], a[1], ["stage1", "stage2"]));
out.maxq = [recordedMaxQ({ t: 53.498991, q_pa: 38438.5 }), recordedMaxQ(null),
  recordedMaxQ({ t: 1, q_pa: 0 }), recordedMaxQ({ t: null, q_pa: 5 }),
  recordedMaxQ({ t: 1, q_pa: "5" })];
out.blend = [0, 0.5, 1].map(x => blendFrame({ kc: 1, up: 10 }, { kc: 4, up: 20 }, x));
out.smooth = [-1, 0, 0.5, 1, 2].map(smooth01);
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(NODE is None, reason="node not installed: page functions not run")
def test_bodies_list_aliases_and_max_q_under_node(
    template: str, payload: dict[str, Any], tmp_path: Path
) -> None:
    """Design 4.9: each separated body is listed with its drag-free coast's own impact time,
    speed and downrange (or as still in flight at the run's end, with where its coast would
    come down), saying it is display-only and no landing prediction; every body of the
    fixture's payload gets its speed and downrange. The canvas names the milestones in plain
    words (the event list keeps the model's label beside them; a synthesised event stays marked
    on the canvas, design 4.4); max-Q is the run's recorded one (the payload's max_q, from its
    metrics; A3b fix round 4), none when the run records none or a value is not a finite
    number; the close-up's framing eases with no jump at either end."""
    bodies = [dict(b) for r in payload["runs"] for b in r["bodies"]]
    assert bodies, "the fixture's pad has separated bodies"
    with_impact = next(b for b in bodies if b["impact"] is not None)
    clipped = dict(with_impact, clipped_at_run_end=True, name="clipped")
    clipped["impact"] = dict(with_impact["impact"], within_run=False)
    no_impact = dict(with_impact, impact=None, name="no_impact")
    case = {
        "bodies": [*bodies, clipped, no_impact],
        "end": 523.5,
        "alias": [
            ["propellant", "stage1"],
            ["propellant", "stage2"],
            ["staging", "stage2"],
            ["ignition", "stage2"],
            ["ignition", "stage1"],
            ["fairing", "stage2"],
            ["cutoff", "stage2"],
            ["kick_start", "stage1"],
            ["release", "stage1"],
            ["push_start", "stage1"],
            ["liftoff", "stage1"],
            ["ramp_end", "stage1"],
            ["ignition_failed", "stage1"],
            ["apex", "stage1"],
            ["impact", "stage1"],
            ["end", "stage2"],
            ["unknown_event", "stage1"],
        ],
    }
    out = _run_pure(template, DISPLAY_HARNESS, case, tmp_path)
    for b, text in zip(bodies, out["bodies"][: len(bodies)], strict=True):
        assert "drag-free coast from T+" in text and "not a landing prediction" in text
        assert "display only, not model output" in text
        if b["impact"] is not None:
            assert f"{b['impact']['speed_mps']:.1f} m/s" in text
            assert f"{b['impact']['downrange_m'] / 1000:.1f} km downrange" in text
    clipped_text, none_text = out["bodies"][-2], out["bodies"][-1]
    assert "still in flight at the run's end (T+523.50 s)" in clipped_text
    assert "its drag-free impact would be" in clipped_text
    assert "does not reach the ground" in none_text
    short = [a[0] if a else None for a in out["alias"]]
    assert short == [
        "MECO",
        "stage-2 burnout",
        "stage separation",
        "stage-2 ignition",
        "stage-1 ignition",
        "fairing jettison",
        "SECO",
        "pitch kick starts",
        "release",
        "push starts",
        "liftoff",
        "full thrust",
        "ignition failed",
        "apex",
        "impact",
        "run ends",
        None,
    ]
    # no raw model key on the canvas (review round 3): every alias is plain words
    assert all("_" not in a[0] for a in out["alias"] if a)
    assert out["alias"][6][1] == "SECO: stage-2 energy cutoff"  # the end banner says "in orbit"
    assert out["maxq"] == [{"t": 53.498991, "v": 38438.5}, None, None, None, None]
    assert out["blend"][0] == {"kc": 1, "up": 10} and out["blend"][2] == {"kc": 4, "up": 20}
    assert out["blend"][1] == pytest.approx({"kc": 2.0, "up": 15.0})
    assert out["smooth"] == pytest.approx([0.0, 0.0, 0.5, 1.0, 1.0])

    script = _script(template)
    ticker = _function_source(template, "buildTicker")[0]
    assert "bodyText(b, lastT(run)," in ticker and "longText(run, e)" in ticker
    assert "MAXQ_TICKER_NOTE" in ticker and "not a logged event" in script
    assert 'a[1] + " [" + eventText(e) + "]"' in _function_source(template, "longText")[0]
    assert "r.maxq = recordedMaxQ(r.max_q);" in script and "largestRow" not in script
    marks = _function_source(template, "drawEventMarks")[0]
    assert "display: true" in marks and "maxqText(run)" in marks
    assert (
        "listed under the event list with each body's own computed impact"
        in (scene.DISPLAY_ONLY[2])
    )


def test_review_round_2_fixes_in_the_source(template: str) -> None:
    """A3b review round 1: the readout goes to a free corner (never over this panel's
    vehicle, the separated bodies or the other vehicle when a corner is free), the gauges
    over no other plate; a marker under an opaque plate gets no label; a frozen panel marks
    no other vehicle, and a key on the view always names the ring's run; labels fall back to a
    short text;
    the header puts the time first; the readout drops what the model has no state for
    before a run's first row and the burn's felt load on an unlit cutoff row, and shows q
    and Mach once there is no drive; the note under the canvas and the clock's line follow
    the runs shown."""
    script = _script(template)
    readout = _function_source(template, "drawReadout")[0]
    assert "firstFree(rects, plates.concat(keep), box)" in readout
    assert "L.inset.y + L.inset.h + VIEW_MARGIN_PX" in readout
    assert "gauge.y - VIEW_MARGIN_PX - h" in readout
    assert "firstFree(cands, plates, view)" in _function_source(template, "gaugeRect")[0]
    panel = _function_source(template, "drawPanel")[0]
    assert "const shown = it => !covers.some(r => inRect(it.px, r));" in panel
    assert (
        panel.count(".filter(shown)") == 3
    )  # the bodies on their vehicles, the other bodies, the rest
    assert "(q.name === FAIRING_BODY) - (p.name === FAIRING_BODY)" in panel
    frames = _function_source(template, "sceneFrames")[0]
    assert "const others = frozen ? [] : prs.filter(" in frames
    key = _function_source(template, "drawRingKey")[0]
    assert "const text = otherText(o);" in key and "|| slots[0];" in key  # never dropped
    assert 'o.run.name + " (other panel"' in _function_source(template, "otherText")[0]
    assert "F.others.length ? drawRingKey(" in _function_source(template, "drawView")[0]
    assert "items[i].short" in _function_source(template, "drawLabels")[0]
    header = _function_source(template, "drawHeader")[0]
    assert '"last event " + clockText(mk.t) + ": " + mk.text' in header
    values = _function_source(template, "stateValues")[0]
    assert "const unlit = !before && !thrustOn && plume > 0;" in values
    assert "felt: before || unlit || " in values and "driveF: before ? null :" in values
    assert "q: before ? null :" in values and "mach: before ? null :" in values
    assert '"q " + fmt(st.q / PA_PER_KPA' in _function_source(template, "hudLines")[0]
    assert '<span id="sceneNote">' in template
    note = 'getElementById("sceneNote").textContent = b ? SCENE_NOTE_TWO : SCENE_NOTE_ONE;'
    assert note in script
    # the note's static copy (read without script) is the two-panel note the script writes
    static = re.search(r'<span id="sceneNote">(.*?)</span>', template, re.S)
    (two,) = re.findall(r'const SCENE_NOTE_TWO = "([^"]*)";', script)
    assert static is not None and static.group(1) == two
    assert '"after release, " + (playing ?' in _function_source(template, "draw")[0]
    assert "const STAGING_AFTER_S = 1;" in script and "const FAIRING_SHOW_S = 5;" in script
    hook = _function_source(template, "panelState")[0]
    for key in (
        "hud_rect:",
        "plate_rects:",
        "band_rects:",
        "closeup_px_per_m:",
        "closeup_halves_tip_px:",
        "closeup_halves_bbox_px:",
        "closeup_caption_rect:",
        "closeup_spent_tag:",
        "frame: L.lay.frame",
        "ring_key:",
    ):
        assert key in hook, key


def test_review_round_3_fixes_in_the_source(template: str) -> None:
    """A3b review round 3: the telemetry says when its values are not the clock's (before
    the run's first row, after its end); the other panel's ring and its key say when that
    run still waits for its first row, as they say when it has ended; a captured frame's
    footer carries the payload's frame caveat and each shown pushed run's structure note; the
    wrap memo's size is a page constant; a separated body's short label keeps 'drag-free'."""
    script = _script(template)
    assert '["state", "Shown at"], ["alt", "Altitude"]' in script
    tel = _function_source(template, "updateTelemetry")[0]
    # A3b fix round 4: as the canvas says it, held at the first row, frozen at the end
    assert 'run.pre_label + "; " + HELD_TEXT + " (first row\'s values)"' in tel
    assert 'run.end_label + "; " + frozenText() + " (values at its end)"' in tel
    assert "clockText(tNow)" in tel
    assert "waiting: ti < r.t[0]" in _function_source(template, "sceneFrames")[0]
    word = _function_source(template, "otherWord")[0]
    assert 'o.ended ? "ended" : o.waiting ? "waiting" : ""' in word
    marker = _function_source(template, "drawOtherMarker")[0]
    assert "text: otherText(o)" in marker and "otherWord(o)" in marker
    footer = _function_source(template, "frameFooterLines")[0]
    assert "const lines = footerLines();" in footer
    assert "if (DATA.frame_caveat) lines.push(DATA.frame_caveat);" in footer
    assert "r.structure_note" in footer
    # step A6v: the caller's footer lines (the app server's) replace the payload's frame caveat,
    # each once; without them the payload's caveat stands (the standalone page has no server)
    assert "if (Array.isArray(given)) given.forEach(" in footer
    assert "if (lines.indexOf(text) < 0) lines.push(text);" in footer
    assert "else if (DATA.frame_caveat) lines.push(DATA.frame_caveat);" in footer
    assert "frameFooterLines(prs, given).forEach(" in _function_source(template, "footerWrapped")[0]
    capture = _function_source(template, "captureFrame")[0]
    assert "footerWrapped(ctx, pal, W, panelRuns, given)" in capture
    assert 'footerLines.every(s => typeof s === "string")' in capture
    constants = script[
        script.index(
            "// ------------------------------------------------------------------ page constants"
        ) :
    ]
    constants = constants[
        : constants.index(
            "// ------------------------------------------------------------------ helpers"
        )
    ]
    assert "const WRAP_MEMO_MAX = 256;" in constants
    assert script.count("const WRAP_MEMO_MAX") == 1


CLIP_HARNESS = """
const fs = require("fs");
const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const sched = rateSchedule(input.runs, null);
const out = { clips: [] };
const summary = c => ({ natural_s: c.natural_s, seconds: c.seconds, frames: c.frames,
  n: c.times.length, first: c.times[0], second: c.times[1], last: c.times[c.times.length - 1],
  before_last: c.times[c.times.length - 2],
  monotone: c.times.every((t, i) => i === 0 || t >= c.times[i - 1]),
  decimals: c.times.every(t => Math.abs(t * 1e6 - Math.round(t * 1e6)) < 1e-3) });
const clip = (fps, seconds) => clipTimesFor(fps, seconds, sched, input.tMin, input.tMax, 6);
input.fps.forEach(f => out.clips.push(summary(clip(f, null))));
out.scaled = summary(clip(24, 75));
out.one = clip(1, 0.4).times;
out.two = clip(1, 2).times;
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(NODE is None, reason="node not installed: page functions not run")
def test_clip_times_run_from_the_first_row_to_the_end_state_under_node(
    template: str, tmp_path: Path
) -> None:
    """Step A6v, fix round 1: clipTimesFor on the pair's events gives n = round(fps x natural
    length) frames at every offered rate, spread evenly over the player's wall clock (frame
    k at wall k x natural / (n - 1): the second frame, in the 0.5x push, is half a wall step
    after the first), the first at the first row and the last at the scene's end itself
    (tMax: the end banners and the pad's cutoff marker are in the clip's last frame, where
    wall k / fps alone stopped one frame short of it), the frame before it one wall step
    earlier (at most 3x that in scene time, the end hold), the times non-decreasing on the
    payload's clock; a scaled clip (24 fps over 75 s) has 1800 frames and the same ends; a
    one-frame clip is the first row alone, a two-frame clip the first row and the end; the
    natural length agrees across rates."""
    case = {
        "runs": [PAD_LIKE, SILO_LIKE],
        "tMin": -2.607318,
        "tMax": 536.300685,
        "fps": [10, 15, 20, 24, 30],
    }
    out = _run_pure(template, CLIP_HARNESS, case, tmp_path)
    naturals = [c["natural_s"] for c in out["clips"]]
    assert max(naturals) - min(naturals) < 0.05 and min(naturals) > 60.0
    for fps, clip in zip(case["fps"], out["clips"], strict=True):
        n = clip["frames"]
        assert n == clip["n"] == round(fps * clip["natural_s"]), fps
        assert clip["seconds"] == pytest.approx(clip["natural_s"])
        assert clip["first"] == pytest.approx(case["tMin"], abs=1e-6)
        assert clip["last"] == pytest.approx(case["tMax"], abs=1e-6), fps
        # the wall time between frames: natural / (n - 1), with n within 0.5 of fps x natural
        step = clip["natural_s"] / (n - 1)
        assert (n - 0.5) / (fps * (n - 1)) <= step <= (n + 0.5) / (fps * (n - 1)), (fps, step)
        assert clip["second"] - case["tMin"] == pytest.approx(0.5 * step, abs=2e-6), fps
        gap = case["tMax"] - clip["before_last"]
        assert 0.0 < gap <= 3.0 * step + 1e-6, (fps, gap)
        assert clip["monotone"] and clip["decimals"], fps
    scaled = out["scaled"]
    assert scaled["frames"] == scaled["n"] == 1800 and scaled["seconds"] == 75
    assert scaled["first"] == pytest.approx(case["tMin"], abs=1e-6)
    assert scaled["last"] == pytest.approx(case["tMax"], abs=1e-6)
    step = scaled["natural_s"] / 1799
    assert scaled["second"] - case["tMin"] == pytest.approx(0.5 * step, abs=2e-6)
    gap = case["tMax"] - scaled["before_last"]
    assert 0.0 < gap <= 3.0 * step + 1e-6 and scaled["monotone"]
    assert out["one"] == [pytest.approx(case["tMin"], abs=1e-6)]
    assert out["two"] == [
        pytest.approx(case["tMin"], abs=1e-6),
        pytest.approx(case["tMax"], abs=1e-6),
    ]
    source = _function_source(template, "clipTimesFor")[0]
    assert "sceneTimeAt(map, n > 1 ? natural * k / (n - 1) : 0)" in source


FAIRING_HARNESS = """
const fs = require("fs");
const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = {};
// when the close-up stops drawing the halves: the first sampled time they have left it, capped
out.ends = input.ends.map(c => halvesEndTime(c[1], c[2], 0.1, t => t >= c[0]));
out.calls = 0;
halvesEndTime(189.25, 523.5, 0.1, t => { out.calls++; return t >= 202.2; });
out.seg = input.seg.map(c => segmentDistance(c[0], c[1], c[2]));
out.near = input.near.map(c => nearestOnRect(c[0], c[1]));
out.spots = leaderSpots([100, 100], 20, 50, 10);
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(NODE is None, reason="node not installed: page functions not run")
def test_fairing_seen_from_the_drop_until_clear_under_node(template: str, tmp_path: Path) -> None:
    """A3b fix round 4 (gate G5: at T+190 nothing showed silo_cold_s1's fairing): the close-up
    draws the halves from the drop, at least FAIRING_SHOW_S, until they have wholly left its
    drawing (sampled), never past the run's end or the halves' impact (halvesEndTime,
    fairingEnd); in the view a separated body that touches its vehicle is drawn over it, the
    vehicle marked again by a dot, with a short label on a leader that is never left out
    (drawLeaderLabels), so the view shows and labels the fairing throughout; a body whose label
    finds no place beside it gets its short label on a leader where one fits, before the other
    markers' labels; the leader's spots lie in eight directions at growing distances."""
    case = {
        "ends": [
            # [the time the halves have left the drawing, the least time, the cap]
            [20.0, 5.0, 100.0],  # gone after the least time: then
            [3.0, 5.0, 100.0],  # gone before the least time: the least time
            [200.0, 5.0, 100.0],  # not gone before the cap: the cap
            [3.0, 120.0, 100.0],  # the least time past the cap: the cap
        ],
        "seg": [
            [[5, 5], [0, 0], [10, 0]],
            [[-3, 4], [0, 0], [10, 0]],
            [[13, 4], [0, 0], [10, 0]],
            [[3, 4], [0, 0], [0, 0]],
        ],
        "near": [
            [[0, 0], {"x": 10, "y": 5, "w": 4, "h": 4}],
            [[11, 6], {"x": 10, "y": 5, "w": 4, "h": 4}],
        ],
    }
    out = _run_pure(template, FAIRING_HARNESS, case, tmp_path)
    assert out["ends"] == pytest.approx([20.0, 5.0, 100.0, 100.0], abs=1e-9)
    assert out["calls"] == 131  # 189.25 to 202.25 every 0.1 s: stops once they have left
    assert out["seg"] == pytest.approx([5.0, 5.0, 5.0, 5.0])
    assert out["near"] == [[10, 5], [11, 6]]
    spots = out["spots"]
    assert len(spots) == 8 and spots[0] == {
        "x": 100 + 20 / math.sqrt(2),
        "y": 100 + 20 / math.sqrt(2),
        "w": 50,
        "h": 10,
    }
    for s in spots:  # each touches the leader's end, 20 px from the anchor, with its nearest point
        qx = min(s["x"] + s["w"], max(s["x"], 100.0))
        qy = min(s["y"] + s["h"], max(s["y"], 100.0))
        assert math.hypot(qx - 100.0, qy - 100.0) == pytest.approx(20.0)

    script = _script(template)
    constants = script[
        script.index(
            "// ------------------------------------------------------------------ page constants"
        ) : script.index(
            "// ------------------------------------------------------------------ helpers"
        )
    ]
    for name in ("HALVES_SCAN_S", "LEADER_PX", "LEADER_STEPS", "MARKER_CORE_OF_SIZE", "WRAP_MEMO"):
        assert re.search(rf"^  const {name} = .*// ", constants, re.M), name
    # no page constant is defined among the drawing functions (review: WRAP_MEMO moved up)
    drawing = script[
        script.index(
            "// ------------------------------------------------------------------ drawing:"
        ) : script.index(
            "// ------------------------------------------------------------------ the page"
        )
    ]
    assert not re.search(r"^  const [A-Z][A-Z0-9_]* =", drawing, re.M)
    end = _function_source(template, "fairingEnd")[0]
    assert "halvesEndTime(hf.tF + FAIRING_SHOW_S, capT, HALVES_SCAN_S, gone)" in end
    assert "cameraAt" not in end and "onVehicle" not in end  # the view's separation is not a term
    assert "!overlaps(halvesAt(" in end and "closeupDrawing(lay.inset)" in end
    assert "body.path.t[body.path.t.length - 1]" in end and "lastT(run)" in end
    assert "fairEnd: fairingEnd(run, lays[i])" in _function_source(template, "sceneFrames")[0]
    assert "t <= fairEnd" in _function_source(template, "fairingAt")[0]
    frame = _function_source(template, "closeupFrame")[0]
    assert (
        "t < hEnd + FAIRING_EASE_S" in frame
        and "ease(halves, own, hEnd, hEnd + FAIRING_EASE_S)" in frame
    )
    clear = _function_source(template, "bodyClearPx")[0]
    assert "(CAM.marker_size_px + MARKER_RING_PX + BODY_MARKER_PX + RING_HALO_PX) / 2" in clear
    view = _function_source(template, "drawView")[0]
    # a body on its vehicle is drawn after the vehicle, then the vehicle's dot over both
    assert (
        view.index("const painted =")
        < view.index("{ onVehicle: true }")
        < view.index("MARKER_CORE_OF_SIZE")
    )
    assert "(on[i] ? null : drawBodyMarker(" in view
    panel = _function_source(template, "drawPanel")[0]
    assert "taken, covers, onVehicleText)" in panel  # never left out (relaxed to the opaque plates)
    assert "drawLeaderLabels(ctx, pal, L.view, late, used(), null, it => it.short)" in panel
    assert panel.index("placedB = drawLabels(") < panel.index("placedR = drawLabels(")
    leader = _function_source(template, "drawLeaderLabels")[0]
    assert "firstFree(leaderSpots(it.px, it.r + k * LEADER_PX, w, h), avoid, inner)" in leader
    assert "{ x: inner.x, y: inner.y, w: w, h: h }" in leader  # the last resort: never null
    assert "haloStroke(ctx, pal, pal.ink3, HAIRLINE_PX, PATH_HALO_PX, null)" in leader
    assert 'const ON_VEHICLE_TEXT = ": drawn, display only";' in script
    hook = _function_source(template, "panelState")[0]
    assert "on_vehicle: b.onVehicle === true" in hook and "closeup_fairing_end_s: L.fairEnd" in hook
    # the leader and the vehicle's dot use pairs the contrast table declares; the event
    # diamond's outline against the trace halo too (review: declared and at least 3:1)
    for pair in (
        ("--ink-3", "--sc-halo"),
        ("--sc-body-line", "--sc-halo"),
        ("--run-0", "--sc-halo"),
    ):
        assert pair in SHAPE_PAIRS, pair
    light, dark, _ = _blocks(template)
    for tokens in (light, {**light, **dark}):
        assert _contrast(tokens["--sc-body-line"], tokens["--sc-halo"]) >= SHAPE_CONTRAST
