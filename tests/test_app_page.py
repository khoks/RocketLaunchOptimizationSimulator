"""The app page (SP2 step A5; design section 4.7, decisions D-SP2-05, 06, 07, 22, 25, 27,
28, 33, 36; exit criteria 2, 4, 7, 8, 12, 17): templates/app.html and the server glue it
needs in app.py.

Fast tier. The template is read as package data (app.load_app_template); the form record is
the one GET /api/form serves for the shipped basis (the committed files at HEAD, read-only
git, as the app loads them) or the fixed-guidance basis of tests/app_support.py; nothing is
flown and results/ is never read.

Checked:

- the template: package data, ASCII with LF line ends, one data token, its marker, charset
  and lang; the header mark equals assets/brand/logo-mark.svg and the tab icon
  assets/brand/favicon.svg (a base64 data URI, so it holds no raw '#'); the site's tokens
  in the three-block pattern, unchanged, and the contrast table (text 4.5:1, control
  outlines, borders and the focus ring 3:1) in both themes;
- the script: one inline script whose sha256 is the Content-Security-Policy's (rendered and
  served, for a page opened by the user and one opened from another site); no HTML sink;
  values by textContent; no URL but the SVG namespace; one fetch, inside ``api``, which
  takes only relative /api/ paths; the frame and its link take only scenePath's path;
  ``node --check``;
- exit criterion 17 (GET / is the one route another site can reach): GET / says in its
  data block whether another site opened it (Sec-Fetch-Site same-site or cross-site, or
  anything but one same-origin or none); the page reads location.hash in one function,
  only when the user opened it; it reads no other input another site controls; it takes a
  postMessage only from its frame's own window and origin, and only a height; the launch
  route is named only in ``postLaunch`` and the scene route only in ``scenePath``, both
  behind the may-act guard; a launch only follows a click;
- the pure block under node: parseHash on hostile input (markup, encoded slashes, bad
  escapes, prototype keys, a million parts, duplicates), hashText back, bootPlan and
  mayAct fail safe, scenePath's refusals, pickPair, groupRuns, the formatters; the request
  of every preset left untouched equals its request in GET /api/form exactly (the 200 m
  silo's exit speed with every digit); the disabled-state matrix (pad only, full load,
  failed ignition, a penalty, a solve, an imposed offload, Advanced off and on); and over a
  matrix of choices every request the page builds is one appform.parse_request accepts and
  appform.form_to_request gives back unchanged;
- the server glue: ``from_other_site`` (a missing Sec-Fetch-Site is another site's: fail
  safe); GET /api/form's ``defaults``, ``fixed_defaults``, ``loads_t``, ``silo_fixed`` and
  ``advanced``;
- the page's helpers under node (qty, snapTo, apexWarning, presetText, valueText,
  startPair) and its results panel and job card per launch kind (panelBlocks, jobBlocks,
  stageItems: the order, the outcome labels, 'Reproduction' only over reproduction lines,
  no unit on a missing number, the display-only items of design 4.9);
- the page's contracts: the silo note, the frame (no border, measured, --app-vh and
  scene.html's embed rules), a launch only of the request the check passed (and a
  confirmation hidden by any edit), a scene already in the frame not loaded again.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import importlib.util
import itertools
import json
import re
import shutil
import subprocess
import sys
import threading
from collections.abc import Iterator
from email.message import Message
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from launchsim import app, appform, video


def _load_support() -> ModuleType:
    """tests/app_support.py, loaded by path (any pytest import mode)."""
    name = "app_support"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sup = _load_support()

REPO = sup.REPO_ROOT
DISPLAY_DIR = REPO / "configs" / "display"
LOGO = REPO / "assets" / "brand" / "logo-mark.svg"
FAVICON = REPO / "assets" / "brand" / "favicon.svg"
SITE_CSS = REPO / "site" / "assets" / "site.css"
NODE = shutil.which("node")
START = app.ServerStart(git={"hash": "0123456789ab", "dirty": False, "error": None}, head=None)
POLL_S = 0.02
TIMEOUT_S = 30.0

PURE_BEGIN = (
    "// ------------------------------------------------------------------ pure functions: begin"
)
PURE_END = (
    "// ------------------------------------------------------------------ pure functions: end"
)
MARKER = "Written by launchsim app"
HTML_SINKS = (
    "innerHTML",
    "outerHTML",
    "insertAdjacentHTML",
    "document.write",
    "setHTMLUnsafe",
    "parseHTMLUnsafe",
    "createContextualFragment",
    "DOMParser",
    "srcdoc",
)
REQUEST_APIS = (
    "XMLHttpRequest",
    "WebSocket",
    "EventSource",
    "sendBeacon",
    "importScripts",
    "import(",
    "new Image",
    "window.open",
    "location.assign",
    "location.replace",
    "location.href",
    "window.location =",
    "document.location",
    "Worker(",
    "RTCPeerConnection",
    'createElement("script',
    'createElement("img',
    'createElement("iframe',
    'createElement("link',
    'createElement("a"',
    "@import",
)
"""Request or navigation APIs the script never uses (its one request API is ``fetch``
inside ``api``; the frame's src and the open-as-a-page link's href take scenePath's path)."""
OTHER_SITE_INPUTS = (
    "location.search",
    "location.href",
    "document.URL",
    "document.referrer",
    "window.name",
    "onmessage",
    "opener",
)
"""What another site controls when it opens GET / and the page never reads (the hash is
read once, only when the user opened the page; a message only as the frame's height)."""
SRC_ASSIGNMENTS = (
    # the hash names the runs in the pickers' order (review of A5: without runs= the scene
    # puts its own default pair's order on them) and the clock a picker change keeps
    "frame.src = path + sceneHash(runs, effectiveTheme(), keepT, true);",
    'frame.src = "about:blank";',  # clearScene
    'frame.src = "about:blank";',  # frameLoaded, after a scene that did not start
)
HREF_ASSIGNMENTS = ("link.href = path + sceneHash(runs, effectiveTheme(), null, false);",)

# contrast (WCAG 2.x): text 4.5:1; shapes, control outlines, borders and the focus ring 3:1
TEXT_CONTRAST = 4.5
SHAPE_CONTRAST = 3.0
TEXT_PAIRS = (
    ("--ink", "--panel"),  # body text, labels, the headline, row descriptions
    ("--ink", "--bg"),  # the title
    ("--ink-2", "--panel"),  # headings, why lines, readings, dt
    ("--ink-2", "--bg"),  # the address, the theme label
    ("--ink-3", "--panel"),  # meta lines, the config keys' text, greyed (unplayable) rows
    ("--ink-3", "--bg"),  # the footer
    ("--ink-3", "--code-bg"),  # disabled inputs and buttons, the open row's meta line
    ("--ink", "--code-bg"),  # the open row
    ("--ink-2", "--code-bg"),  # a config key in the open row
    ("--ink", "--caution-bg"),  # the badge, the notice, caution lines, caveat text
    ("--caution", "--caution-bg"),  # the caveat heading
    ("--ink-2", "--caution-bg"),  # the offload caveats' heading
    ("--ink-3", "--caution-bg"),  # the caveats' 'built for' line
    ("--bad", "--panel"),  # refusals, errors, a failed verification, a flagged headline
    ("--bad", "--caution-bg"),  # the caveats box's error line
    ("--good", "--panel"),  # the 'done' pill
    ("--link", "--panel"),  # open as a page
    ("--panel", "--ink"),  # the Launch button's label
)
SHAPE_PAIRS = (
    ("--ink-3", "--panel"),  # input, select and button outlines; radio and check boxes
    ("--ink-3", "--bg"),  # the theme select in the header
    ("--ink-3", "--code-bg"),  # a disabled control's dashed outline
    ("--ink", "--panel"),  # the Launch button, the current stage's border
    ("--focus", "--panel"),  # the keyboard focus ring
    ("--focus", "--bg"),
    ("--focus", "--code-bg"),
    ("--bad", "--panel"),  # an invalid field's border, the failed pill
    ("--good", "--panel"),  # the done pill
    ("--caution", "--bg"),  # the badge's border, the notice's rule
    ("--caution", "--panel"),  # the caveats' rule, a caution line's rule
    ("--caution", "--caution-bg"),  # the confirmation's border
    ("--focus", "--caution-bg"),  # the focus ring on the confirmation's buttons
    ("--ink-3", "--caution-bg"),  # the confirmation's button outlines
)


# ------------------------------------------------------------------ helpers


@pytest.fixture(scope="module")
def template() -> str:
    return app.load_app_template()


def _script(page: str) -> str:
    scripts = re.findall(r"<script>(.*?)</script>", page, re.S)
    assert len(scripts) == 1
    return scripts[0]


def _data_block(page: str) -> Any:
    found = re.findall(r'<script type="application/json" id="app-data">(.*?)</script>', page, re.S)
    assert len(found) == 1
    return _strict(found[0])


def _strict(text: bytes | str) -> Any:
    def refuse(name: str) -> Any:
        raise ValueError(f"non-strict JSON constant {name}")

    return json.loads(text, parse_constant=refuse)


def _skip_to_match(script: str, start: int) -> int:
    """The index of the '}' matching the '{' at ``start``: string literals, template
    literals and comments skipped (the bodies checked here hold no regex literal)."""
    depth, i, quote = 0, start, ""
    while i < len(script):
        ch = script[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = ""
        elif ch in "\"'`":
            quote = ch
        elif script.startswith("//", i):
            i = script.find("\n", i)
            continue
        elif script.startswith("/*", i):
            i = script.find("*/", i) + 1
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise AssertionError("unbalanced braces")


def _function_span(script: str, name: str) -> tuple[int, int]:
    """(start, end) of the body of ``function name(...) { ... }`` (exactly one)."""
    found = [m.start() for m in re.finditer(rf"\bfunction {re.escape(name)}\(", script)]
    assert len(found) == 1, (name, found)
    brace = script.index("{", script.index(")", found[0]))
    return brace, _skip_to_match(script, brace)


def _body(script: str, name: str) -> str:
    start, end = _function_span(script, name)
    return script[start + 1 : end]


def _first_statement(body: str) -> str:
    """The body's first statement, comments skipped."""
    lines = [ln.strip() for ln in body.splitlines()]
    code = [ln for ln in lines if ln and not ln.startswith("//")]
    return code[0]


def _calls_outside_definition(script: str, name: str) -> list[int]:
    """Positions of every call ``name(`` that is not the definition."""
    return [
        m.start()
        for m in re.finditer(rf"(?<![\w.]){re.escape(name)}\(", script)
        if not script[max(0, m.start() - 9) : m.start()].endswith("function ")
    ]


def _inside(script: str, pos: int, name: str) -> bool:
    start, end = _function_span(script, name)
    return start < pos < end


def _click_spans(script: str) -> list[tuple[int, int]]:
    """Bodies of the arrow functions registered as click handlers with
    addEventListener("click", () => { ... })."""
    spans = []
    for m in re.finditer(r'addEventListener\("click", \(\) => \{', script):
        brace = m.end() - 1
        spans.append((brace, _skip_to_match(script, brace)))
    return spans


def _blocks(css_text: str) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """(light, dark under prefers-color-scheme, dark under data-theme) token dicts of a
    stylesheet in the site's three-block pattern."""

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


def _headers(*pairs: tuple[str, str]) -> Message:
    msg = Message()
    for name, value in pairs:
        msg[name] = value
    return msg


@contextlib.contextmanager
def _serving(root: Path, basis: appform.Basis) -> Iterator[app.AppServer]:
    """An AppServer on 127.0.0.1:0 over ``root`` serving in a daemon thread."""
    server = app.AppServer(
        port=0,
        basis=basis,
        server_start=START,
        results_root=root,
        repo_root=root.parent,
        display_dir=DISPLAY_DIR,
    )
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": POLL_S}, daemon=True
    )
    with server:
        thread.start()
        assert server.wait_serving(TIMEOUT_S)
        yield server
    thread.join(TIMEOUT_S)
    assert not thread.is_alive()


def _get(port: int, path: str, headers: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
    import http.client

    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT_S)
    try:
        conn.request("GET", path, headers=headers)
        response = conn.getresponse()
        return response.status, {k.lower(): v for k, v in response.getheaders()}, response.read()
    finally:
        conn.close()


@pytest.fixture(scope="module")
def shipped_info(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """GET /api/form's record on the shipped basis (AppServer.form_info, the socket bound
    to a free port and closed; nothing served)."""
    basis = sup.shipped_basis()
    root = tmp_path_factory.mktemp("app_page_root")
    with app.AppServer(
        port=0,
        basis=basis,
        server_start=START,
        results_root=root,
        repo_root=REPO,
        display_dir=DISPLAY_DIR,
    ) as server:
        info = server.form_info()
    return json.loads(json.dumps(info))


def _run_pure(template: str, harness: str, case: Any, tmp_path: Path) -> Any:
    """The template's pure block with ``harness`` appended, run under node on ``case``
    (JSON in a file, argv[2]); the harness writes one JSON value to stdout."""
    assert NODE is not None
    start, end = template.index(PURE_BEGIN), template.index(PURE_END)
    js = tmp_path / "pure.js"
    js.write_text(template[start:end] + harness, encoding="utf-8", newline="\n")
    data = tmp_path / "case.json"
    data.write_text(json.dumps(case), encoding="utf-8", newline="\n")
    proc = subprocess.run(
        [NODE, str(js), str(data)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


HARNESS_HEAD = """
const fs = require("fs");
const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
"""


# ------------------------------------------------------------------ the template


def test_template_is_package_data_ascii_with_one_token(template: str) -> None:
    """Read through importlib.resources; ASCII with LF ends; the data token once (read with
    JSON.parse of its textContent); the marker; charset and lang; the persistent badge."""
    assert template.isascii() and "\r" not in template
    assert template.startswith('<!doctype html>\n<html lang="en">')
    assert '<meta charset="utf-8">' in template
    assert template.count(app.APP_DATA_TOKEN) == 1
    assert MARKER in template and "step A5" in template
    assert 'JSON.parse(document.getElementById("app-data").textContent)' in template
    assert re.search(r'<p class="badge" id="badge">Exploratory runs, not findings</p>', template)
    assert '<iframe id="frame" title="Launch scene"' in template


def test_mark_and_tab_icon_are_the_brand_files(template: str) -> None:
    """D-SP2-33: the header mark is assets/brand/logo-mark.svg inlined byte for byte; the
    tab icon is favicon.svg as a base64 data URI (no raw '#', which a percent-encoded URI
    would have to write as %23)."""
    assert LOGO.read_text(encoding="utf-8").strip() in template
    (href,) = re.findall(r'<link rel="icon" type="image/svg\+xml" href="([^"]*)">', template)
    prefix = "data:image/svg+xml;base64,"
    assert href.startswith(prefix) and "#" not in href
    assert base64.b64decode(href[len(prefix) :]) == FAVICON.read_bytes()


def test_site_tokens_and_contrast_in_both_themes(template: str) -> None:
    """Every token of site/assets/site.css's three blocks is in the page's with the same
    value; both dark blocks are identical; color-scheme in both themes; every text pair
    reaches 4.5:1 and every outline, border and focus-ring pair 3:1 (WCAG 2.x)."""
    ours, theirs = _blocks(template), _blocks(SITE_CSS.read_text(encoding="utf-8"))
    for mine, site in zip(ours, theirs, strict=True):
        for key, value in site.items():
            assert mine.get(key) == value, key
    assert ours[1] == ours[2]
    assert "color-scheme: light;" in template and template.count("color-scheme: dark;") == 2
    light, dark, _ = ours
    low = []
    for theme, tokens in {"light": light, "dark": {**light, **dark}}.items():
        for pairs, need in ((TEXT_PAIRS, TEXT_CONTRAST), (SHAPE_PAIRS, SHAPE_CONTRAST)):
            for fg, bg in pairs:
                ratio = _contrast(tokens[fg], tokens[bg])
                if ratio < need:
                    low.append(f"{theme}: {fg} on {bg} is {ratio:.2f}, needs {need}")
    assert not low, low
    style = re.search(r"<style>(.*?)</style>", template, re.S)
    assert style is not None
    css = style.group(1)
    # the outlines the table checks are the ones the stylesheet draws; an invalid field is
    # marked by its border, so the outline on it stays the focus ring (review of A5)
    for rule in (
        "border: 1px solid var(--ink-3)",
        "outline: 2px solid var(--focus)",
        "border-color: var(--bad); box-shadow: 0 0 0 1px var(--bad)",
        "border: 1px dashed var(--ink-3)",
    ):
        assert rule in css, rule
    assert "outline: 2px solid var(--bad)" not in css


# ------------------------------------------------------------------ the script


def test_csp_hash_is_the_scripts_rendered_and_served(template: str, tmp_path: Path) -> None:
    """render_app_page's policy allows the page's one script by its sha256; the served
    page's header carries the same policy for a page the user opened and one another site
    opened (the script is the same; only the data block's from_other_site differs)."""
    page, csp = app.render_app_page({"url": "u", "boot_id": "b", "version": "v"})
    script = _script(page.decode("ascii"))
    assert script == _script(template)
    digest = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode()
    assert csp == app.APP_CSP_TEMPLATE.format(script=f"sha256-{digest}")
    with _serving(tmp_path / "root", sup.fixed_basis()) as server:
        own = {"Host": f"127.0.0.1:{server.port}"}
        responses = {
            site: _get(server.port, "/", {**own, **({"Sec-Fetch-Site": site} if site else {})})
            for site in ("", "none", "same-origin", "same-site", "cross-site", "bogus")
        }
    for site, (status, headers, body) in responses.items():
        text = body.decode("ascii")
        assert status == 200
        assert _script(text) == script
        assert headers["content-security-policy"] == csp
        assert _data_block(text) == {
            "url": server.url,
            "boot_id": server.boot_id,
            "version": app.__version__,
            "from_other_site": site not in ("none", "same-origin"),
        }


def test_no_html_sink_and_values_by_text(template: str) -> None:
    """No HTML sink appears in the script at all (not even in a comment); values reach
    the DOM by textContent and createElement."""
    script = _script(template)
    for sink in HTML_SINKS:
        assert sink not in script, sink
    assert "textContent" in script and "createElement" in script


def test_requests_only_to_the_apps_own_relative_api_paths(template: str) -> None:
    """No URL in the template but the SVG namespace; no request or navigation API but one
    ``fetch``, inside ``api``, which refuses a path that does not start with /api/; every
    ``api(`` call names a literal /api/ path; the frame's src and the link's href are set
    only from scenePath's path (or about:blank); no stylesheet url() and no element
    source but the data: tab icon."""
    assert re.findall(r"https?://[^\s\"']+", template) == ["http://www.w3.org/2000/svg"]
    script = _script(template)
    for name in REQUEST_APIS:
        assert name not in script, name
    assert script.count("fetch(") == 1 and _inside(script, script.index("fetch("), "api")
    assert 'path.indexOf("/api/") !== 0' in _body(script, "api")
    calls = _calls_outside_definition(script, "api")
    assert calls
    for pos in calls:
        assert script.startswith('api("/api/', pos), script[pos : pos + 40]
    srcs = sorted(ln.strip() for ln in script.splitlines() if ".src =" in ln)
    assert srcs == sorted(SRC_ASSIGNMENTS)
    assert [ln.strip() for ln in script.splitlines() if ".href =" in ln] == list(HREF_ASSIGNMENTS)
    assert "const path = scenePath(" in _body(script, "loadScene")
    for line in SRC_ASSIGNMENTS[:1] + HREF_ASSIGNMENTS:
        assert line in _body(script, "loadScene")
    style = re.search(r"<style>(.*?)</style>", template, re.S)
    assert style is not None and "url(" not in style.group(1)
    links = re.findall(r"<link\b[^>]*>", template)
    assert len(links) == 1 and 'rel="icon"' in links[0]
    for src in re.findall(r"\bsrc=\"([^\"]*)\"", template):
        assert src.startswith("data:"), src
    for href in re.findall(r"\bhref=\"([^\"]*)\"", template):
        assert href.startswith("data:"), href


def test_criterion_17_the_page_acts_only_when_the_user_did(template: str) -> None:
    """GET / is the one route another site can reach (exit criterion 17). The script reads
    none of OTHER_SITE_INPUTS; location.hash once, in readHash, called at load only when
    the page was not opened from another site and on a hashchange only by hashChanged,
    which returns first on such a page (whose hash boot drops); one message listener,
    heightMessage, which takes only the frame's own window and this origin, and only a
    number (then measures the frame itself); the launch route only
    in postLaunch and the scene route only in scenePath, both behind the may-act guard
    (scenePath is called only from loadScene, which starts with it); mayActNow fails safe
    (anything but from_other_site false is another site's); a real launch only after a
    click (startLaunch from the Launch button's click, through launchClicked, or the
    confirmation's); the user's first trusted event is what lets the page act."""
    script = _script(template)
    for name in OTHER_SITE_INPUTS:
        assert name not in script, name
    assert script.count("location.hash") == 1
    assert _inside(script, script.index("location.hash"), "readHash")
    calls = _calls_outside_definition(script, "readHash")
    assert len(calls) == 2
    assert sorted(
        next(f for f in ("boot", "hashChanged") if _inside(script, c, f)) for c in calls
    ) == ["boot", "hashChanged"]
    assert "S.fromOtherSite ? null : readHash()" in script
    assert _first_statement(_body(script, "hashChanged")) == "if (S.fromOtherSite) return;"
    assert script.count('addEventListener("hashchange"') == 1
    assert 'window.addEventListener("hashchange", hashChanged);' in script
    boot = _body(script, "boot")
    drop = 'try { history.replaceState(null, "", "/"); }'
    assert drop in boot and boot.index(drop) < boot.index("readHash()")
    assert boot.index("if (S.fromOtherSite) {") < boot.index(drop)
    assert "fromOtherSite: DATA.from_other_site !== false" in script
    assert script.count('addEventListener("message"') == 1
    assert 'window.addEventListener("message", heightMessage);' in script
    message = _body(script, "heightMessage")
    assert 'e.source !== $("frame").contentWindow || e.origin !== SELF_ORIGIN' in message
    assert "Number.isFinite(h)" in message and "d.type !== HEIGHT_MESSAGE" in message
    assert message.rstrip().endswith("fitFrame();")
    assert script.count("/api/launches") == 1
    assert _inside(script, script.index("/api/launches"), "postLaunch")
    assert _first_statement(_body(script, "postLaunch")).startswith("if (!mayActNow()) return")
    assert script.count("/scene/") == 1 and _inside(script, script.index("/scene/"), "scenePath")
    for pos in _calls_outside_definition(script, "scenePath"):
        assert _inside(script, pos, "loadScene")
    assert _first_statement(_body(script, "loadScene")).startswith("if (!mayActNow()) return")
    assert "return mayAct(S.fromOtherSite ? true : false, S.userActed);" in script
    first = _body(script, "firstAction")
    assert "if (!e.isTrusted || S.userActed) return;" in first
    clicks = _click_spans(script)
    for name in ("startLaunch", "launchClicked"):
        for pos in _calls_outside_definition(script, name):
            in_click = any(a < pos < b for a, b in clicks)
            assert in_click or (name == "startLaunch" and _inside(script, pos, "launchClicked")), (
                name,
                pos,
            )
    posts = _calls_outside_definition(script, "postLaunch")
    assert len(posts) == 2
    assert _inside(script, posts[0], "sendDryRun") or _inside(script, posts[1], "sendDryRun")
    assert _inside(script, posts[0], "startLaunch") or _inside(script, posts[1], "startLaunch")
    dry = _body(script, "sendDryRun")
    assert dry.index("if (!mayActNow())") < dry.index("postLaunch(")
    assert "dry_run: true" in dry


def test_from_other_site_reads_sec_fetch_site() -> None:
    """from_other_site: one same-origin or one none is the user's own; same-site (another
    port on this loopback address), cross-site, anything unknown, more than one value, or
    none at all (fail safe: a browser without Fetch Metadata cannot say, so its page waits
    for the user) is another site's."""
    assert app.from_other_site(_headers()) is True
    for value in ("same-origin", "none", " Same-Origin ", "NONE"):
        assert app.from_other_site(_headers(("Sec-Fetch-Site", value))) is False, value
    for value in ("same-site", "cross-site", "bogus", ""):
        assert app.from_other_site(_headers(("Sec-Fetch-Site", value))) is True, value
    two = _headers(("Sec-Fetch-Site", "same-origin"), ("Sec-Fetch-Site", "same-origin"))
    assert app.from_other_site(two) is True


@pytest.mark.skipif(NODE is None, reason="node not installed: the script is not checked")
def test_inline_script_is_valid_javascript(template: str, tmp_path: Path) -> None:
    js = tmp_path / "inline.js"
    js.write_text(_script(template), encoding="utf-8", newline="\n")
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


# ------------------------------------------------------------------ the pure block under node

CRAFTED_HASHES: tuple[tuple[Any, dict[str, Any]], ...] = (
    ("#dir=silo_offload_2d/20261003T112934Z", {"dir": ["silo_offload_2d", "20261003T112934Z"]}),
    ("#dir=app/20261006T101010Z-2", {"dir": ["app", "20261006T101010Z-2"]}),
    ("#dir=<img src=x onerror=1>/20261003T112934Z", {}),
    ("#dir=%3Cimg%20src%3Dx%3E/20261003T112934Z", {}),
    ("#dir=../../etc/20261003T112934Z", {}),
    ("#dir=silo%2Foffload/20261003T112934Z", {}),
    ("#dir=silo/20261003T112934Z%00", {}),
    ("#dir=silo/2026", {}),
    ("#dir=/20261003T112934Z", {}),
    ("#dir=%E0%A4%A/20261003T112934Z", {}),
    ("#runs=pad,<svg onload=1>,silo_cold_s1,x", {"runs": ["pad", "silo_cold_s1"]}),
    ("#runs=a%2Bb,a+b,a%20b", {"runs": ["a+b"]}),
    ("#runs=,,", {}),
    ('#theme="><script>', {}),
    ("#theme=%22%3E%3Cscript%3E", {}),
    ("#theme=DARK", {}),
    ("#theme=dark&theme=light", {"theme": "dark"}),
    ("#preset=javascript:alert(1)", {}),
    ("#preset=silo_cold_s1_dry%2B8.1t", {"preset": "silo_cold_s1_dry+8.1t"}),
    ("#preset=" + "a" * 129, {}),
    ("#__proto__=1&constructor=2&toString=3&hasOwnProperty=4", {}),
    (
        "#dir=silo_screening_2d/20260930T175743Z&runs=pad,silo_failed&theme=light&preset=pad",
        {
            "dir": ["silo_screening_2d", "20260930T175743Z"],
            "runs": ["pad", "silo_failed"],
            "theme": "light",
            "preset": "pad",
        },
    ),
    ("", {}),
    ("#", {}),
    (None, {}),
    (42, {}),
)
HASH_DEFAULTS = {"dir": None, "runs": [], "theme": None, "preset": None}

PURE_HARNESS = (
    HARNESS_HEAD
    + """
const out = {};
out.hash = input.hashes.map(h => parseHash(h));
out.big_parts = parseHash("#" + new Array(1000000).fill("x=1").join("&"));
out.big_runs = parseHash("#runs=" + new Array(100000).fill("pad").join(",")).runs;
out.late_key = parseHash("#" + new Array(20).fill("x=1").join("&") + "&theme=dark").theme;
out.round = input.round.map(h => parseHash("#" + hashText(parseHash(h))));
out.hash_text = hashText({ dir: { experiment: "a+b", timestamp: "20261003T112934Z" },
  runs: ["pad", "x+y"], theme: "dark", preset: "silo_cold_s1_dry+8.1t" });
out.boot = [false, true, undefined, "false", 0, null].map(c => bootPlan(c, { theme: "dark" }));
out.may = [[false, false], [true, false], [true, true], ["no", false], [undefined, false],
  [false, "x"]].map(c => mayAct(c[0], c[1]));
out.scene = input.scenes.map(c => scenePath(c[0], c[1], c[2]));
out.pairs = input.pairs.map(c => pickPair(c[0], c[1], c[2]));
out.groups = groupRuns(input.runs).map(g => [g.label, g.runs.map(r => r.name)]);
out.numbers = ["3", " 3.0 ", "-0.5", "1e3", ".5", "3.", "1e999", "NaN", "Infinity", "0x10", "3 m",
  "", "true", "+2", "--1"].map(numberFrom);
out.fmt = [3, 3.0, 76.70717046013364, 0.05, 20.545, 94.57444092026729, 1e21, NaN].map(fmtNum);
out.fx = [[41262.90803733282, 2], [-0.0004, 2], [1596625983.68, 0], [NaN, 1]]
  .map(c => fx(c[0], c[1]));
out.dur = [0, 16, 89.4, 90, 100, 370, 3600, -1, NaN].map(fmtDuration);
out.range = [[16, 100], [0, 0], [57, 370], null].map(fmtRange);
out.size = [[74260469, false], [17635887, true], [999, false], [null, false], [0, false],
  [312, true], [1000, false]].map(c => fmtSize(c[0], c[1]));
out.scene_hash = [
  sceneHash(["silo_cold", "silo_cold_s1_dry+8.1t"], "dark", null, true),
  sceneHash(["silo_cold", "silo_cold_s1"], "light", 9.3, true),
  sceneHash(["pad"], "light", -3.33, false),
  sceneHash(["pad", "<svg>", "a/b", "silo"], "DARK", NaN, true),
  sceneHash([], null, Infinity, false),
  sceneHash("pad", "dark", 1e-7, false)
];
out.scene_hash_read = parseHash(out.scene_hash[0].replace("embed=1&", "")).runs;
const now = Date.UTC(2026, 9, 6, 10, 15, 0);
out.age = ["20261003T112934Z", "20261006T101000Z", "bad"].map(s => ageText(s, now));
process.stdout.write(JSON.stringify(out));
"""
)
SCENE_CASES = (
    (
        ("silo_offload_2d", "20261003T112934Z", ["pad", "silo_cold_s1"]),
        ("/scene/silo_offload_2d/20261003T112934Z/pad,silo_cold_s1"),
    ),
    (
        ("app", "20261006T101010Z-2", ["silo_cold_s1_dry+8.1t"]),
        ("/scene/app/20261006T101010Z-2/silo_cold_s1_dry%2B8.1t"),
    ),
    (("app", "20261006T101010Z", ["pad", "pad"]), None),
    (("app", "20261006T101010Z", []), None),
    (("app", "20261006T101010Z", ["a", "b", "c", "d", "e"]), None),
    (("app", "20261006T101010Z", ["../x"]), None),
    (("app", "20261006T101010Z", ["a/b"]), None),
    (("app", "20261006T101010Z", "pad"), None),
    (("../app", "20261006T101010Z", ["pad"]), None),
    (("app", "2026", ["pad"]), None),
    (("app", "20261006T101010Z", [None]), None),
)
RUNS = [
    {"name": "pad", "role": "run", "offload_kind": None, "has_rows": True},
    {"name": "silo_cold", "role": "run", "offload_kind": None, "has_rows": True},
    {"name": "silo_cold_s1", "role": "offload", "offload_kind": "offload case", "has_rows": True},
    {
        "name": "silo_cold_s1__pad",
        "role": "offload",
        "offload_kind": "paired pad",
        "has_rows": True,
    },
    {
        "name": "pad__offload_stage1",
        "role": "offload",
        "offload_kind": "pad control",
        "has_rows": False,
    },
    {"name": "silo_cold__aero_bound", "role": "bound", "offload_kind": None, "has_rows": True},
    {"name": "pad__aero_bound", "role": "paired_baseline", "offload_kind": None, "has_rows": True},
    {"name": "odd", "role": None, "offload_kind": None, "has_rows": True},
]
PAIR_CASES = (
    ((RUNS, ["pad", "silo_cold_s1"], []), ["pad", "silo_cold_s1"]),
    (
        (RUNS, ["pad", "silo_cold_s1"], ["silo_cold", "silo_cold_s1__pad"]),
        ["silo_cold", "silo_cold_s1__pad"],
    ),
    ((RUNS, ["pad", "silo_cold_s1"], ["silo_cold"]), ["silo_cold"]),
    ((RUNS, ["pad", "silo_cold_s1"], ["pad__offload_stage1"]), ["pad", "silo_cold_s1"]),
    ((RUNS, ["pad", "silo_cold_s1"], ["pad", "pad"]), ["pad", "silo_cold_s1"]),
    ((RUNS, ["pad", "silo_cold_s1"], ["unknown"]), ["pad", "silo_cold_s1"]),
    (
        (RUNS, ["pad", "silo_cold", "silo_cold_s1"], ["pad", "silo_cold", "odd"]),
        ["pad", "silo_cold"],
    ),
    ((RUNS, ["pad__offload_stage1", "pad"], None), ["pad"]),
    (([], [], ["pad"]), []),
)


@pytest.mark.skipif(NODE is None, reason="node not installed: page functions not run")
def test_hash_scene_path_and_helpers_under_node(template: str, tmp_path: Path) -> None:
    """The page's pure block under node: parseHash keeps only what is exactly its contract
    (checked names, light or dark, at most two distinct runs) and ignores everything else
    (markup, encoded slashes, bad escapes, prototype keys, keys past its sixteenth part, a
    million parts, a non-string); hashText writes what parseHash reads back; bootPlan
    restores the view and checks the form only when from_other_site is exactly false, and
    mayAct fails safe the same way; scenePath builds the one scene path from checked names,
    each segment encoded once, and refuses the rest; pickPair takes the wanted runs only
    when each has a time series, else the default pair; groupRuns groups by role; the
    number reader takes only a finite decimal; the formatters."""
    case = {
        "hashes": [h for h, _ in CRAFTED_HASHES],
        # hashText writes runs only with their directory
        "round": [
            h for h, want in CRAFTED_HASHES if want and ("dir" in want or "runs" not in want)
        ],
        "scenes": [list(c) for c, _ in SCENE_CASES],
        "pairs": [list(c) for c, _ in PAIR_CASES],
        "runs": RUNS,
    }
    out = _run_pure(template, PURE_HARNESS, case, tmp_path)
    for (text, want), got in zip(CRAFTED_HASHES, out["hash"], strict=True):
        expected = {**HASH_DEFAULTS, **want}
        if expected["dir"] is not None:
            expected["dir"] = {"experiment": want["dir"][0], "timestamp": want["dir"][1]}
        assert got == expected, text
    assert out["big_parts"] == HASH_DEFAULTS
    assert out["big_runs"] == ["pad"]
    assert out["late_key"] is None  # only the first 16 parts are read
    for text, got in zip(case["round"], out["round"], strict=True):
        assert got == out["hash"][case["hashes"].index(text)], text
    assert out["hash_text"] == (
        "dir=a%2Bb/20261003T112934Z&runs=pad,x%2By&theme=dark&preset=silo_cold_s1_dry%2B8.1t"
    )
    assert out["boot"][0] == {"restore": {"theme": "dark"}, "dryRun": True}
    assert all(b == {"restore": None, "dryRun": False} for b in out["boot"][1:])
    assert out["may"] == [True, False, True, False, False, True]
    assert out["scene"] == [want for _, want in SCENE_CASES]
    assert out["pairs"] == [want for _, want in PAIR_CASES]
    assert out["groups"] == [
        ["Experiment runs", ["pad", "silo_cold"]],
        ["Offload cases", ["silo_cold_s1"]],
        ["Paired pads", ["silo_cold_s1__pad"]],
        ["Pad controls", ["pad__offload_stage1"]],
        ["Bounds", ["silo_cold__aero_bound"]],
        ["Paired baselines", ["pad__aero_bound"]],
        ["Other run folders", ["odd"]],
    ]
    assert out["numbers"] == [
        3,
        3,
        -0.5,
        1000,
        0.5,
        3,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        2,
        None,
    ]
    assert out["fmt"] == ["3", "3", "76.70717", "0.05", "20.545", "94.574441", "1e+21", ""]
    assert out["fx"] == ["41,262.91", "0.00", "1,596,625,984", "not recorded"]
    assert out["dur"] == [
        "0 s",
        "16 s",
        "89 s",
        "1 min 30 s",
        "1 min 40 s",
        "6 min 10 s",
        "60 min",
        "unknown",
        "unknown",
    ]
    assert out["range"] == ["16 s to 1 min 40 s", "under a second", "57 s to 6 min 10 s", "unknown"]
    # under 1 kB in bytes: a directory holding only FAILED.txt is small, never "0 kB"
    assert out["size"] == [
        "74.3 MB",
        "at least 17.6 MB",
        "999 B",
        "size not known yet",
        "0 B",
        "at least 312 B",
        "1 kB",
    ]
    # the frame's hash (review of A5): the runs in the pickers' order, each encoded once
    # (a '+' as %2B), the clock a picker change keeps; bad names, themes and times dropped
    assert out["scene_hash"] == [
        "#embed=1&theme=dark&runs=silo_cold,silo_cold_s1_dry%2B8.1t",
        "#embed=1&theme=light&runs=silo_cold,silo_cold_s1&t=9.3",
        "#theme=light&runs=pad&t=-3.33",
        "#embed=1&runs=pad,silo",
        "",
        "#theme=dark&t=1e-7",
    ]
    assert out["scene_hash_read"] == ["silo_cold", "silo_cold_s1_dry+8.1t"]
    assert out["age"] == ["2 days ago", "5 min ago", ""]


PRESET_HARNESS = (
    HARNESS_HEAD
    + """
const info = input.info;
const keys = info.fields.map(f => f.key);
function presetValues(p) {
  const values = Object.assign({}, info.defaults);
  Object.keys(p.request).forEach(k => { if (k !== "preset") values[k] = p.request[k]; });
  return values;
}
const out = {};
out.presets = info.presets.map(p => {
  const view = viewOf(presetValues(p), info.advanced);
  const built = buildRequest(view.values, keys, p.name);
  return { name: p.name, json: JSON.stringify(built.request), blank: built.blank };
});
out.matrix = input.matrix.map(c => {
  const values = Object.assign({}, info.defaults, c);
  if (c.fixed_key !== undefined) values.fixed_value = info.fixed_defaults[c.fixed_key];
  const view = viewOf(values, info.advanced);
  const built = buildRequest(view.values, keys, "silo_cold");
  return { request: built.request, blank: built.blank };
});
process.stdout.write(JSON.stringify(out));
"""
)


def _matrix() -> list[dict[str, Any]]:
    """Choice combinations a user can reach: site, push, ramp start, startup, failed
    ignition, propellant with each of its forms, Advanced, a penalty and a paired pad."""
    out: list[dict[str, Any]] = []
    for site, push_by, ramp_by, startup, fails in itertools.product(
        appform.SITES, appform.PUSH_KEYS, appform.RAMP_BY, appform.STARTUPS, (False, True)
    ):
        base = {
            "site": site,
            "push_by": push_by,
            "ramp_by": ramp_by,
            "startup": startup,
            "fails": fails,
        }
        out.append({**base, "propellant": appform.PROPELLANT_FULL})
        if ramp_by not in (appform.RAMP_TIME_RELEASE, appform.RAMP_DEPTH) or startup != "ramp":
            continue  # the offload forms on a subset of the push and ignition choices
        for advanced, penalty, paired in itertools.product((False, True), (0, 2), (False, True)):
            extra = {"advanced": advanced, "stage1_dry_mass_added_t": penalty, "paired_pad": paired}
            for key in appform.FIXED_KEYS:
                out.append(
                    {**base, **extra, "propellant": appform.PROPELLANT_FIXED, "fixed_key": key}
                )
            for mode in appform.SOLVE_MODES:
                out.append(
                    {**base, **extra, "propellant": appform.PROPELLANT_SOLVE, "solve_mode": mode}
                )
    return out


@pytest.mark.skipif(NODE is None, reason="node not installed: the form mapping is not run")
def test_form_to_request_under_node(
    template: str, shipped_info: dict[str, Any], tmp_path: Path
) -> None:
    """On the shipped basis's GET /api/form record: the request the page sends for every
    preset left untouched (the defaults overlaid by the preset's request, through the
    disabled-state rules) equals the preset's request exactly, as JSON values and with
    the 200 m silo's exit speed written with every digit; over a matrix of the choices a
    user can reach (the disabled-state rules applied), no used field is ever blank and
    every request is one appform.parse_request accepts and form_to_request writes back
    unchanged (so the page never sends a field the choices do not use, or misses one)."""
    matrix = _matrix()
    out = _run_pure(template, PRESET_HARNESS, {"info": shipped_info, "matrix": matrix}, tmp_path)
    by_name = {p["name"]: p for p in shipped_info["presets"]}
    assert len(out["presets"]) == len(appform.PRESETS) == len(by_name)
    for got in out["presets"]:
        want = by_name[got["name"]]["request"]
        assert got["blank"] == [], got["name"]
        assert json.loads(got["json"]) == want, got["name"]
        sent = json.loads(got["json"])
        assert list(sent) == list(want), got["name"]  # the same keys in the same order
        for key, value in want.items():  # a number stays a number, a boolean a boolean
            assert sent[key] == value and (type(sent[key]) is bool) == (type(value) is bool), key
    assert '"exit_speed_mps":76.70717046013364' in next(
        p["json"] for p in out["presets"] if p["name"] == "silo_cold_200m"
    )
    assert len(out["matrix"]) == len(matrix) > 1000
    for choice, got in zip(matrix, out["matrix"], strict=True):
        assert got["blank"] == [], choice
        form = appform.parse_request(got["request"])
        assert isinstance(form, appform.Form), (choice, form)
        assert appform.form_to_request(form) == got["request"], choice


MATRIX_HARNESS = (
    HARNESS_HEAD
    + """
const info = input.info;
const views = input.cases.map(c => viewOf(Object.assign({}, info.defaults, c), info.advanced));
process.stdout.write(JSON.stringify(views));
"""
)
MATRIX_CASES = {
    "silo_full": {},
    "pad": {"site": "pad", "ramp_by": "depth", "propellant": "solve", "advanced": True},
    "fails": {"fails": True, "propellant": "fixed"},
    "solve": {"propellant": "solve"},
    "fixed": {"propellant": "fixed"},
    "penalty": {"propellant": "solve", "stage1_dry_mass_added_t": 2, "paired_pad": True},
    "advanced_off": {"propellant": "solve", "solve_mode": "both", "advanced": False},
    "advanced_off_fixed": {"propellant": "fixed", "fixed_key": "stage2_t", "advanced": False},
    "advanced_on": {"propellant": "solve", "solve_mode": "both", "advanced": True},
    "pad_time": {"site": "pad", "ramp_by": "time_release"},
    "fixed_s2_pre": {
        "propellant": "fixed",
        "fixed_key": "stage2_t",
        "advanced": True,
        "stage2_offload_t": 5,
    },
    "solve_s2_pre": {
        "propellant": "solve",
        "solve_mode": "stage2",
        "advanced": True,
        "stage2_offload_t": 5,
    },
    "fixed_s1_pre": {"propellant": "fixed", "fixed_key": "stage1_t", "stage2_offload_t": 5},
}


@pytest.mark.skipif(NODE is None, reason="node not installed: the disabled-state matrix is not run")
def test_disabled_state_matrix_under_node(
    template: str, shipped_info: dict[str, Any], tmp_path: Path
) -> None:
    """Design 4.7's disabled states, each with its reason: pad only disables the push, the
    silo details, the push-relative ramp starts (a stored one falls back to the time from
    release), the offload and the penalty; a full load disables the pre-offload, the
    paired pad, the penalty and Advanced; a failed ignition disables the offload; a penalty
    clears and disables the paired pad; a solve shows the pad control locked on, an imposed
    offload none; Advanced off disables the stage-2 and both forms (a stored one falls back
    to stage 1); the stored values are never changed."""
    cases = list(MATRIX_CASES.values())
    got = dict(
        zip(
            MATRIX_CASES,
            _run_pure(template, MATRIX_HARNESS, {"info": shipped_info, "cases": cases}, tmp_path),
            strict=True,
        )
    )
    full = {"preoffload", "paired_pad", "penalty", "advanced"}
    assert set(got["silo_full"]["why"]) == full and got["silo_full"]["off"].keys() >= {
        "solve_mode:stage2",
        "fixed_key:both_fraction",
    }
    assert got["silo_full"]["padControl"] is None
    pad = got["pad"]
    assert set(pad["why"]) == {"push", "silo", "ramp_by", "propellant", *full}
    assert pad["why"]["propellant"].startswith("Pad only: an offload needs the silo")
    assert pad["why"]["penalty"] == pad["why"]["propellant"]
    assert pad["values"]["propellant"] == "full" and pad["values"]["ramp_by"] == "time_release"
    assert pad["values"]["advanced"] is False
    assert {k for k in pad["off"] if k.startswith("ramp_by:")} == {
        f"ramp_by:{w}" for w in appform.RAMP_BY if w != appform.RAMP_TIME_RELEASE
    }
    fails = got["fails"]
    assert fails["why"]["propellant"].startswith("Failed ignition")
    assert fails["values"]["propellant"] == "full"
    assert "push" not in fails["why"] and "silo" not in fails["why"]
    assert got["solve"]["padControl"] == "on" and got["fixed"]["padControl"] == "none"
    assert not set(got["solve"]["why"]) & {"preoffload", "paired_pad", "penalty", "advanced"}
    penalty = got["penalty"]
    assert penalty["values"]["paired_pad"] is False and penalty["why"]["paired_pad"].startswith(
        "Cleared by the assumed penalty"
    )
    off = got["advanced_off"]
    assert off["values"]["solve_mode"] == "stage1" and off["why"]["solve_mode"].startswith(
        "Advanced is off"
    )
    assert got["advanced_off_fixed"]["values"]["fixed_key"] == "stage1_t"
    on = got["advanced_on"]
    assert on["values"]["solve_mode"] == "both" and "solve_mode" not in on["why"]
    assert not any(k.startswith("solve_mode:") for k in on["off"])
    # pad only: the ramp-start way's reason shows even when the stored way is the time
    # from release (the other ways are disabled with it)
    assert got["pad_time"]["why"]["ramp_by"] == pad["why"]["ramp_by"]
    assert got["pad_time"]["why"]["ramp_by"].startswith("Pad only: the ramp start is a time")
    # a stage-2 pre-offload goes with a stage-1 offload only (appform refuses it with a
    # stage-2 or both-stage case): disabled with its reason and never sent
    for name in ("fixed_s2_pre", "solve_s2_pre", "advanced_on"):
        assert got[name]["why"]["preoffload"].startswith("A stage-2 pre-offload goes with"), name
        assert got[name]["values"]["stage2_offload_t"] == 0, name
    assert "preoffload" not in got["fixed_s1_pre"]["why"]
    assert got["fixed_s1_pre"]["values"]["stage2_offload_t"] == 5


# ------------------------------------------------------------------ the server glue


def test_form_record_gives_defaults_and_the_read_only_silo(shipped_info: dict[str, Any]) -> None:
    """GET /api/form on the shipped basis: a starting value for every form field (the
    request-only preset and dry_run aside): booleans false; a pre-offload, a penalty and a
    paired pad none; the others the first preset's (the default preset first: 100 m, 3 g0,
    +0.5 s), the 200 m silo's exit speed with every digit; the depth and speed ways
    silo_hot_ramp_on_track's own ramp start converted, the height silo_cold's; the startup
    ramp the vehicle's 2 s; every number inside its range. An imposed fraction starts at
    SP1's 5% and an imposed mass at 5% of the stage's load; the silo details the form shows
    read-only are the committed silo's brake, drive efficiency, shaft and track; the
    Advanced forms with their readings."""
    defaults = shipped_info["defaults"]
    fields = {f["key"]: f for f in shipped_info["fields"]}
    assert set(defaults) == set(fields) - {"preset", "dry_run"}
    for key, value in defaults.items():
        spec = fields[key]
        if spec["kind"] == "bool":
            assert value is False, key
        elif spec["kind"] == "choice":
            assert value in spec["choices"], key
        else:
            assert isinstance(value, int | float) and spec["lo"] <= value <= spec["hi"], key
    assert defaults["stage2_offload_t"] == 0 and defaults["stage1_dry_mass_added_t"] == 0
    assert (defaults["stroke_m"], defaults["net_accel_g"], defaults["t_ign_s"]) == (100, 3.0, 0.5)
    assert defaults["exit_speed_mps"] == 76.70717046013364
    assert defaults["t_ramp_s"] == 2.0 and defaults["tau_s"] == 1.0
    assert defaults["at_depth_m"] == pytest.approx(94.574, abs=1e-3)
    assert defaults["at_speed_mps"] == pytest.approx(17.867, abs=1e-3)
    assert defaults["at_height_m"] == pytest.approx(37.132, abs=1e-3)
    assert shipped_info["fixed_defaults"] == {
        "stage1_t": 20.545,
        "stage1_fraction": 0.05,
        "stage2_t": 5.375,
        "stage2_fraction": 0.05,
        "both_fraction": 0.05,
    }
    assert [(s["key"], s["config_key"]) for s in shipped_info["silo_fixed"]] == [
        ("brake_decel_g", "assist.brake_decel_g"),
        ("drive_efficiency", "assist.drive_efficiency"),
        ("shaft", "assist.shaft"),
        ("track", "assist.track"),
    ]
    assert [s["value"] for s in shipped_info["silo_fixed"]][:3] == [5, 0.5, "vented"]
    assert shipped_info["advanced"] == {
        "solve_modes": list(appform.ADVANCED_SOLVE_MODES),
        "fixed_keys": list(appform.ADVANCED_FIXED_KEYS),
        "solve_reading": appform.ADVANCED_SOLVE_READING,
        "fixed_reading": appform.ADVANCED_FIXED_READING,
    }
    # review of A5: where each converted ramp-start default comes from, the vehicle's own
    # startup, and where launches are written (a folder outside the repository: no path)
    sources = shipped_info["default_sources"]
    assert set(sources) == {"at_depth_m", "at_speed_mps", "at_height_m"}
    assert sources["at_depth_m"]["preset"] == "silo_hot_ramp_on_track"
    assert sources["at_depth_m"]["time_after_release_s"] == pytest.approx(-2.0, abs=1e-9)
    assert sources["at_height_m"]["preset"] == "silo_cold"
    assert sources["at_height_m"]["time_after_release_s"] == pytest.approx(0.5, abs=1e-9)
    assert shipped_info["vehicle_startup"] == {
        "kind": "ramp",
        "t_ramp_s": 2.0,
        "tau_s": None,
        "vehicle": "configs/vehicles/generic_f9_class_2d.yaml",
    }
    assert shipped_info["results_root"] == {"path": None, "tracked": False}


def test_describe_names_an_imposed_offload_in_words() -> None:
    """Review of A5 (usability): a form's one-line description (a preset's label, the job
    card's and the run list's line) names an imposed offload by its tanks, in words, never
    by its config key."""
    basis = sup.shipped_basis()
    text = appform.describe(appform.preset_form(basis, "silo_cold_fix5pct"))
    assert "imposed offload from stage 1: 5% of its load" in text
    assert "stage1_fraction" not in text
    assert set(appform.FIXED_KEY_WORDS) == set(appform.FIXED_KEYS)


def test_results_root_view_names_only_a_folder_of_the_repository(tmp_path: Path) -> None:
    """GET /api/form ``results_root``: the repository's results/ by its relative path and
    tracked; another folder of the repository by its relative path, not tracked; a folder
    outside the repository without its path (the page names no local path)."""
    repo = tmp_path / "repo"
    (repo / "results").mkdir(parents=True)
    (repo / "scratch" / "deep").mkdir(parents=True)
    assert app.results_root_view(repo / "results", repo) == {"path": "results", "tracked": True}
    assert app.results_root_view(repo / "scratch" / "deep", repo) == {
        "path": "scratch/deep",
        "tracked": False,
    }
    assert app.results_root_view(tmp_path / "elsewhere", repo) == {"path": None, "tracked": False}


def test_form_record_of_a_basis_without_offload_presets(tmp_path: Path) -> None:
    """On the fixed-guidance basis (its offload presets unavailable) no preset imposes a
    fraction, so no imposed offload has a starting value; every other default is there."""
    with app.AppServer(
        port=0,
        basis=sup.fixed_basis(),
        server_start=START,
        results_root=tmp_path,
        repo_root=REPO,
        display_dir=DISPLAY_DIR,
    ) as server:
        info = server.form_info()
    assert set(info["fixed_defaults"].values()) == {None}
    assert info["defaults"]["fixed_value"] is None and info["defaults"]["solve_mode"] is None
    assert info["defaults"]["stroke_m"] == 100 and info["defaults"]["t_ramp_s"] == 2.0
    assert info["loads_t"]["stage1"] > info["loads_t"]["stage2"] > 0


def test_form_record_gives_each_stages_load(shipped_info: dict[str, Any]) -> None:
    """GET /api/form ``loads_t``: the full propellant load of stage 1, stage 2 and both, in
    tonnes, of the baseline's vehicle (the page states the tonnes ranges against them;
    appform refuses an imposed mass at or beyond the load)."""
    loads = shipped_info["loads_t"]
    assert loads["stage1"] == pytest.approx(410.9, abs=0.05)
    assert loads["stage2"] == pytest.approx(107.5, abs=0.05)
    assert loads["both"] == pytest.approx(loads["stage1"] + loads["stage2"])
    stage1_t = shipped_info["fixed_defaults"]["stage1_t"]
    assert stage1_t == pytest.approx(0.05 * loads["stage1"], abs=1e-3)


# ------------------------------------------------------------------ the panel and job text

HELPERS_HARNESS = (
    HARNESS_HEAD
    + """
const out = {};
out.qty = [[null, 2, "MN", 1e6], [undefined, 1, "s", 1, "T+"], [NaN, 0, "kWh"], [0, 2, "MN", 1e6],
  [25.25, 1, "s", 1, "T+"], [26054.4, 1, "kg"], [22000, 1, "t", 1e3]]
  .map(c => qty(c[0], c[1], c[2], c[3], c[4]));
out.snap = [[0.5000000000000002, [0.5, 0.4]], [0.5000001, [0.5]],
  [76.70717046013364, [undefined, 76.70717046013364]], [3, []], [94.5, [null, 94.5]]]
  .map(c => snapTo(c[0], c[1]));
out.apex = [["height_event", 300.9, 301.0609], ["height_event", 290, 301.06],
  ["height_event", 297, 301.06], ["height_closed_form", 300.9, 301.06], ["depth", 1, 2],
  ["height_event", null, 301]].map(c => apexWarning(c[0], c[1], c[2]));
out.preset = [presetText({ name: "silo_cold_s1", label: "silo 100 m" }, "silo_cold_s1"),
  presetText({ name: "silo_cold", label: "silo 100 m" }, "silo_cold_s1")];
out.value = [valueText({ angle_deg: 90, exit_altitude_m: 0 }), valueText("vented"), valueText(5)];
out.plural = [plural(1, "other entry", "other entries"), plural(3, "other entry", "other entries")];
out.start = input.starts.map(c => startPair(c[0], c[1]));
process.stdout.write(JSON.stringify(out));
"""
)
START_RUNS = [
    {"name": "pad", "has_rows": True},
    {"name": "silo_cold", "has_rows": True},
    {"name": "silo_cold_fix5pct", "has_rows": True},
    {"name": "silo", "has_rows": False},
]


def _start(pair: list[str] | None, default: list[str]) -> dict[str, Any]:
    return {
        "runs": START_RUNS,
        "default_pair": default,
        "panel": None if pair is None else {"pair": pair},
    }


@pytest.mark.skipif(NODE is None, reason="node not installed: the page helpers are not run")
def test_page_helpers_under_node(template: str, tmp_path: Path) -> None:
    """qty gives a missing number as 'not recorded' alone (no unit, no 'T+', no made-up
    zero) and a recorded one scaled with its unit; snapTo takes a stored value a converted
    one equals to 1e-9 (so a round trip through another ramp-start way sends the committed
    number); apexWarning warns of a height-event ramp start within 5 m (or 1%) of the
    drag-free apex, and of nothing else; a preset's option leads with its name, SP1's case
    marked; a config value in words; startPair opens a directory on its results panel's
    runs that have a time series (an app run's launched run; a run that did not fly
    dropped), else its default pair, the wanted runs first."""
    starts = [
        [_start(["pad", "silo_cold_fix5pct"], ["pad", "silo_cold"]), []],
        [_start(["pad", "silo"], ["pad"]), []],
        [_start(None, ["pad", "silo_cold"]), []],
        [_start(["pad", "silo_cold_fix5pct"], ["pad", "silo_cold"]), ["silo_cold"]],
        [_start(["silo"], ["pad", "silo_cold"]), ["silo"]],
    ]
    out = _run_pure(template, HELPERS_HARNESS, {"starts": starts}, tmp_path)
    assert out["qty"] == [
        "not recorded",
        "not recorded",
        "not recorded",
        "0.00 MN",
        "T+25.3 s",
        "26,054.4 kg",
        "22.0 t",
    ]
    assert out["snap"] == [0.5, 0.5000001, 76.70717046013364, 3, 94.5]
    assert out["apex"][0].startswith("Within 0.16 m of the drag-free apex (301.06 m)")
    assert out["apex"][2] == (
        "Within 4.06 m of the drag-free apex (301.06 m): with drag the coast peaks lower, so "
        "the rocket may never reach this height, stage 1 would never light and the run would "
        "not fly."
    )
    assert [out["apex"][i] for i in (1, 3, 4, 5)] == ["", "", "", ""]
    assert out["preset"] == [
        "silo_cold_s1 (SP1's headline case): silo 100 m",
        "silo_cold: silo 100 m",
    ]
    assert out["value"] == ["angle 90 deg, exit altitude 0 m", "vented", "5"]
    assert out["plural"] == ["1 other entry", "3 other entries"]
    assert out["start"] == [
        ["pad", "silo_cold_fix5pct"],
        ["pad"],
        ["pad", "silo_cold"],
        ["silo_cold"],
        ["pad", "silo_cold"],
    ]


DISPLAY_ONLY = ["Every shape and length: drawn.", "The plume inside the shaft: drawn."]
CAVEATS = ["EXPLORATORY app run, not a finding.", "Planar 2-D point-mass model."]
SP1_TEXT = (
    "not SP1's silo_cold_s1: 2 settings differ from it, so this figure is not SP1's headline "
    "(results/silo_offload_2d/20261003T112934Z)"
)
DRIVE_NOTE = (
    "Under the prescribed constant-acceleration drive the carriage mass and the impingement "
    "fraction change only the drive's force, energy and peak power: not the release speed, the "
    "payload or the offload."
)
G0_NOTE = "Here g is g0 = 9.80665 m/s^2, the unit of the rows below and of the form."
NOT_COMPARED = (
    "SP1's headline is an offload at the pad's payload (silo_cold_s1); this launch has no "
    "offload, so it is not compared with it."
)
JOB_TAG = (
    "Exploratory app run: not a finding. Its caveats (and SP1's caveat groups, when it "
    "reproduces SP1's case) are in the results panel below."
)
OUTCOME_LABELS = {
    "complete": "Complete",
    "flagged": "Complete, flagged",
    "not_in_orbit": "Complete, not in orbit",
    "did_not_fly": "Complete: the run did not fly",
    "offload_found_nothing": "Complete: the offload found nothing",
    "crashed": "Crashed (FAILED.txt)",
}
"""The page's outcome labels of the launch kinds (templates/app.html OUTCOME_LABELS)."""


def _push(value: float | None) -> dict[str, Any]:
    keys = (
        "push_time_s felt_g_peak interface_force_peak_N electrical_energy_kWh "
        "peak_drive_power_W braking_distance_m facility_length_m carriage_mass_kg"
    ).split()
    return {
        **dict.fromkeys(keys, value),
        "text": "vertical silo, 3 g net push",
        "model": "constant_accel",
    }


def _flight(value: float | None) -> dict[str, Any]:
    keys = (
        "liftoff_mass_kg meco_after_release_s peak_q_alpha peak_felt_axial_g_flight payload_kg"
    ).split()
    return {
        **dict.fromkeys(keys, value),
        "status": "inserted" if value is not None else "impact",
        "ignition": "stage 1 lit T+0.5 s after release",
        # as app.flight_view writes it: its own "max-Q " first
        "max_q_text": None if value is None else "max-Q 33.1 kPa at T+60.0 s, below the pad's",
    }


def _record(kind: str, **panel: Any) -> dict[str, Any]:
    """A GET /api/results/app/<stamp> record of one launch kind (the shapes results_panel
    serves; the values made up)."""
    base: dict[str, Any] = {
        "tag": {
            "kind": "exploratory",
            "text": "Exploratory app run: not a finding",
            "git": {"hash": "0123456789ab", "state": "clean"},
            "server_start": {"hash": "0123456789ab", "state": "clean"},
            "launch_tree": "clean",
            "label": "exploratory",
        },
        "shown": "silo",
        "pair": ["pad", "silo"],
        "headline": {"kind": "payload", "text": "Payload capacity 27,553.2 kg, +1,498.8 kg"},
        "sp1_headline": None,
        "reproduces": [],
        "sp1_comparison": {
            "case": "silo_cold_s1",
            "reproduces": False,
            "differs": ["assist.stroke_m: 150 (SP1's silo_cold_s1: 100)"],
            "text": SP1_TEXT,
        },
        "push": _push(1.0e6),
        "flight": _flight(26_000.0),
        "flags": [],
        "verification": None,
        "outcome": {
            "kind": kind,
            "message": f"{kind}: the message",
            "notes": [f"{kind}: the message"],
        },
        "caveats": CAVEATS,
        "offload_caveats": [],
        "built_for": ["pad", "silo"],
        "error": None,
        "display_only": DISPLAY_ONLY,
    }
    base.update(panel)
    runs = [
        {"name": "pad", "role": "run", "note": "", "has_rows": True},
        {"name": "silo", "role": "run", "note": "", "has_rows": True},
    ]
    return {
        "row": {
            "experiment": "app",
            "timestamp": "20261006T000000Z",
            "state": "complete",
            "description": "silo 100 m deep, 3 g0 net",
        },
        "runs": runs,
        "default_pair": ["pad", "silo"],
        "panel": base,
        "panel_error": None,
    }


def _records() -> dict[str, dict[str, Any]]:
    """A record per launch kind (design 4.6's table: complete, flagged, not in orbit, did
    not fly, offload found nothing, crashed)."""
    out = {
        "complete": _record(
            "complete", reproduces=["silo_cold: same configuration as the committed silo_cold"]
        ),
        "flagged": _record(
            "flagged",
            headline={"kind": "payload", "text": "Payload 27,000.0 kg (flagged)", "flagged": True},
            flags=["silo: a flag"],
            outcome={
                "kind": "flagged",
                "message": "silo: a flag",
                "notes": ["silo: a flag", "pad__offload_stage2: 1 flag"],
            },
        ),
        "not_in_orbit": _record(
            "not_in_orbit",
            headline={
                "kind": "not_in_orbit",
                "text": "silo_failed did not reach the target orbit (status impact)",
            },
            flight={**_flight(None), "liftoff_mass_kg": 569_100.0},
        ),
        "did_not_fly": _record(
            "did_not_fly",
            headline={
                "kind": "did_not_fly",
                "status": "search_failed",
                "text": "The run did not fly: search_failed (grid)",
            },
            push=_push(None),
            flight={**_flight(None), "liftoff_mass_kg": 569_100.0},
            flags=["search_failed: grid: first failure: no_ignition: the coast peaked below"],
            built_for=["pad"],
        ),
        "offload_found_nothing": _record(
            "offload_found_nothing",
            shown="silo_s1",
            pair=["pad", "silo_s1"],
            headline={"kind": "offload", "text": "No offload found at P_ref"},
            verification={"passed": True, "text": "verification passed (+0.01 kg against 2.6 kg)"},
            offload_caveats=["offload caveat, word for word"],
        ),
    }
    out["offload_found_nothing"]["runs"] += [
        {
            "name": "silo_s1",
            "role": "offload",
            "offload_kind": "offload case",
            "note": "offload case silo_s1 of silo: none found",
            "has_rows": True,
        },
        {
            "name": "pad__offload_stage1",
            "role": "offload",
            "offload_kind": "pad control",
            "note": "pad control (stage1): none found",
            "has_rows": False,
        },
    ]
    out["crashed"] = {
        "row": {
            "experiment": "app",
            "timestamp": "20261006T000001Z",
            "state": "failed",
            "reason": "failed",
            "line": "ValueError: boom",
        },
        "runs": [],
        "default_pair": [],
        "panel": None,
        "panel_error": None,
    }
    return out


def _job(kind: str | None, state: str = "done") -> dict[str, Any]:
    """A GET /api/job snapshot (its shape; the values made up)."""
    outcome = None
    if kind is not None:
        outcome = {
            "kind": kind,
            "message": f"{kind}: the message",
            "notes": [f"{kind}: the message", "a note"],
            "reproduces": ["silo_cold_s1: same configuration"] if kind == "complete" else [],
        }
    return {
        "id": 3,
        "state": state,
        "stage_index": 3 if state == "running" else 4,
        "stages": ["preflight", "pad", "variant", "comparison", "writing"],
        "pad_cached": True,
        "elapsed_s": 50.0,
        "expected_s": [49.0, 320.0],
        "longer_than_expected": state == "running",
        "description": "silo_cold_s1",
        "preset": "silo_cold_s1",
        "directory": {"experiment": "app", "timestamp": "20261006T000000Z"},
        "outcome": outcome,
    }


STAGE_PARTS = [
    ["variant silo_cold", 8, 50],
    ["pad control stage1", 8, 60],
    ["solve silo_cold_s1", 25, 160],
    ["paired pad silo_cold_s1__pad", 8, 50],
]
"""A launch's expected parts as its dry run names them (appform.expected_work's labels)."""
NO_IGNITION_FLAG = (
    "search_failed: grid: at P0 = 22800 kg: no gamma* grid point flies at P = 22800 kg "
    "(first failure: no_ignition: the coast after release reached its apex at 300.649873 m "
    "(t = 10.45 s), 0.250127 m below the ignition altitude 300.9 m of height_method: event: "
    "stage 1 never lights); at P = 0: no gamma* grid point flies at P = 0 kg (first failure: "
    "no_ignition: the coast after release reached its apex at 300.629453 m (t = 10.4497 s), "
    "0.270547 m below the ignition altitude 300.9 m of height_method: event: stage 1 never "
    "lights)"
)
"""A did-not-fly run's first flag as a launch near the apex recorded it (planar.py's
no_ignition text inside the search's): the plain line reads its first failure."""
IDLE_LINE = (
    "No launch in this server session yet. Every launch writes app/<UTC time>/ under the "
    "server's results root (results/ unless the server was started with --results-root) and "
    "is exploratory, not a finding."
)


def _check_panel(kind: str, record: dict[str, Any], lines: list[list[str]]) -> None:
    """The text panelBlocks writes for one launch kind (see the test below)."""
    tags = [t for t, _ in lines]
    texts = [x for _, x in lines]
    heads = [x for t, x in lines if t in ("h3", "h4", "summary")]
    panel = record["panel"]
    # the tag names the directory and the next line what was launched (review of A5: the
    # panel never reads as the results of another launch)
    assert tags[:4] == ["p.tag exploratory", "p.meta", "p.meta", "p.meta"], kind
    assert texts[0] == "Exploratory app run: not a finding: app/20261006T000000Z", kind
    assert texts[1] == "Launched: silo 100 m deep, 3 g0 net", kind
    assert texts[3].startswith("Run shown: ") and tags[4].startswith("p.headline"), kind
    assert texts[4] == panel["headline"]["text"]
    assert (tags[4] == "p.headline bad") == bool(panel["headline"].get("flagged"))
    outcomes = [h for h in heads if h.startswith("Outcome of the whole directory: ")]
    if kind == "complete":
        assert not outcomes
    else:
        assert outcomes == [f"Outcome of the whole directory: {OUTCOME_LABELS[kind]}"], kind
        assert texts.index(outcomes[0]) < texts.index("Flags and verification")
        assert texts.index(outcomes[0]) > 4
    assert ("Reproduction" in heads) == (kind == "complete"), kind
    if kind == "complete":
        assert texts[texts.index("Reproduction") + 1].startswith("silo_cold: same configuration")
    assert "Against SP1's silo_cold_s1" in heads
    assert texts.index("Against SP1's silo_cold_s1") > 4
    if any(r["role"] == "offload" for r in record["runs"]):
        assert SP1_TEXT in texts
        assert "What differs from SP1's silo_cold_s1, by config key" in heads
    else:  # SP1's headline is an offload: a launch without one is not compared with it
        assert SP1_TEXT not in texts and not any(h.startswith("What differs") for h in heads)
        assert texts[texts.index("Against SP1's silo_cold_s1") + 1] == NOT_COMPARED
    if kind == "did_not_fly":
        assert "Push" not in heads and "Flight" not in heads
        assert texts[5].startswith("Why, in the search's own words: search_failed")
        assert any(x.startswith("No push or flight figures") for x in texts)
        assert DRIVE_NOTE not in texts
    else:
        assert texts.index("Push") < texts.index("Flight") < texts.index("Flags and verification")
        assert texts.index("Against SP1's silo_cold_s1") < texts.index("Push")
        assert texts[texts.index("Push") + 2] == DRIVE_NOTE, kind
        # the push and the flight in two columns of one box (side by side on a wide panel)
        push, flight = texts.index("Push"), texts.index("Flight")
        assert tags[push - 2 : push] == ["box.numbers", "box.numcol"], kind
        assert tags[flight - 2 : flight] == ["/box", "box.numcol"], kind
    if kind == "flagged":
        assert any(x.startswith("A count of flags names its run only") for x in texts)
    if kind == "offload_found_nothing":
        assert "Offload runs of this launch (2)" in heads
        assert "offload case silo_s1 of silo: none found" in texts
        # folded, its summary counting what it holds (round 3: the scene stays near the
        # headline, every caveat stays on the page)
        at = lines.index(
            [
                "summary",
                "1 caveat recorded with this directory's offload block (metrics.json "
                "offload.caveats), word for word",
            ]
        )
        assert lines[at + 1] == ["li", "offload caveat, word for word"]
    if kind == "not_in_orbit":
        assert ["kv", "MECO after release: not recorded"] in lines
        assert ["kv", "Payload: not recorded"] in lines
        assert ["kv", "Liftoff mass: 569.1 t"] in lines
    if kind == "did_not_fly":
        # the run shown has no trajectory: the line says it is not in the scene
        assert texts[3] == (
            "Run shown: silo (did not fly: no trajectory, so it is not in the scene) beside pad"
        )
    else:
        assert texts[3] == "Run shown: " + panel["shown"] + " beside pad", kind
    if kind in ("complete", "flagged"):
        # one unit of acceleration on the page, g0 (round 3); the max-Q row says max-Q once;
        # the push text's "g" is said to be g0
        assert ["kv", "Felt on the track (peak): 1,000,000.00 g0"] in lines
        assert ["kv", "Peak felt axial g in flight: 26,000.00 g0"] in lines
        assert ["kv", "Max-Q: 33.1 kPa at T+60.0 s, below the pad's"] in lines
        assert texts[texts.index("Push") + 3] == G0_NOTE, kind
    for tag, text in lines:
        if tag == "kv":
            value = text.split(": ", 1)[1]
            assert value == "not recorded" or "not recorded" not in value, (kind, text)
            assert not value.startswith("max-Q"), (kind, text)
            assert not re.search(r"\d g$", value), (kind, text)
    assert tags[-1] == "/box" and "box.caveats" in tags
    assert (
        heads[-1] == "What the scene draws that the model does not compute (display only): 2 items"
    )
    assert tags[-2 - len(DISPLAY_ONLY)] == "summary"
    assert texts[-1 - len(DISPLAY_ONLY) : -1] == DISPLAY_ONLY
    caveats = texts.index("Read before quoting: the caveats of the runs shown")
    assert caveats > texts.index("Flags and verification")
    # the run's own caveats stay open (a list, not a fold) right under their heading
    assert tags[caveats + 2 : caveats + 2 + len(CAVEATS)] == ["li"] * len(CAVEATS)
    assert texts[caveats + 2 : caveats + 2 + len(CAVEATS)] == CAVEATS
    assert not any(re.search(r"\bsaved\b", h, re.I) for h in heads)


@pytest.mark.skipif(NODE is None, reason="node not installed: the panel text is not run")
def test_panel_and_job_text_per_launch_kind_under_node(template: str, tmp_path: Path) -> None:
    """Design 5, A5 row: the panel text per launch kind (complete, flagged, not in orbit,
    did not fly, offload found nothing, crashed) as the page writes it (panelBlocks and
    jobBlocks under node): the tag, the run shown and its headline first; the whole
    directory's outcome after the headline and above the numbers, with its label, and a
    pointer to summary.md for a count of flags; 'Reproduction' only over reproduction
    lines, SP1's comparison under 'Against SP1's <case>' with what differs; the offload
    runs with their notes; no push or flight for a run that did not fly, the search's
    reason under its headline; a missing number 'not recorded' alone (never 'T+not
    recorded s', 'not recorded kg' or a made-up 0); flags and verification, then the
    caveats box with the offload caveats and the display-only items last; a crashed
    directory its line. The job card: the outcome label per kind, durations as estimates
    (never 'measured on this machine'), the parts of a running launch, the opened panel's
    headline, the stages, and the idle line naming the results root."""
    records = _records()
    kinds = list(OUTCOME_LABELS)
    jobs: list[Any] = [[_job(k), {"headline": "Payload capacity 27,553.2 kg"}] for k in kinds]
    jobs += [
        [_job(None, "running"), {"items": [["solve silo_cold_s1", 25, 160]]}],
        [_job("complete"), {"runs": ["pad"], "times": {"0": 0.4, "1": 0.0, "3": 2.5}}],
        [None, {"root": {"path": "results", "tracked": True}}],
        [None, {}],
        # round 3: the running stage's time so far (from the elapsed time at which the page
        # first saw it running) and its expected range (the launched form's parts that run
        # in it); past the range, longer than expected; a stage the page did not see start
        # has no time so far
        [_job(None, "running"), {"mark": {"index": 3, "elapsed": 20.0}, "items": STAGE_PARTS}],
        [
            _job(None, "running"),
            {"mark": {"index": 3, "elapsed": 0.0}, "items": [["solve x", 5, 10]]},
        ],
        [_job(None, "running"), {"mark": {"index": 2, "elapsed": 0.0}, "items": STAGE_PARTS}],
        # a launch that did not fly: why, from its panel's first flag, in plain words
        [_job("did_not_fly"), {"why": NO_IGNITION_FLAG}],
        [_job("did_not_fly"), {"why": "search_failed: grid: first failure: drive_limit: x"}],
    ]
    case = {"details": list(records.values()), "jobs": jobs}
    out = _run_pure(template, sup.PAGE_BLOCKS_HARNESS, case, tmp_path)
    for (kind, record), lines in zip(records.items(), out["panels"], strict=True):
        if kind == "crashed":
            assert lines == [
                ["p.tag", "app/20261006T000001Z: failed (failed)"],
                ["p.meta", "ValueError: boom"],
            ]
        else:
            _check_panel(kind, record, lines)
    for kind, lines in zip(kinds, out["jobs"], strict=False):
        texts = [x for _, x in lines]
        assert f"Outcome: {OUTCOME_LABELS[kind]}" in texts, kind
        assert "Expected 49 s to 5 min 20 s (an estimate, not a countdown)." in texts
        assert "Directory: app/20261006T000000Z" in texts
        # the launch's headline goes with the exploratory tag and the pointer to the
        # caveats, and not where the outcome line already says the run did not reach
        # orbit or did not fly (review of A5)
        said = kind in ("not_in_orbit", "did_not_fly")
        assert ("Payload capacity 27,553.2 kg" in texts) == (not said), kind
        if not said:
            at = lines.index(["p.headline", "Payload capacity 27,553.2 kg"])
            assert lines[at - 1] == ["p.tag exploratory", JOB_TAG], kind
        assert ("Reproduction" in texts) == (kind == "complete")
        assert not any("measured on this machine" in x for x in texts)
    base = len(kinds)
    running, pad_only, tracked, idle = out["jobs"][base : base + 4]
    assert ["summary", "What this launch runs, each part an estimate"] in running
    assert ["li", "solve silo_cold_s1: 25 s to 2 min 40 s"] in running
    assert ["p.caution", "Longer than expected: past the upper end of the estimate."] in running
    assert idle == [["p.meta", IDLE_LINE]]
    assert tracked == [
        [
            "p.meta",
            "No launch in this server session yet. Every launch writes results/app/<UTC time>/ "
            "in the repository (tracked: each launch's summary.md is committed and public) and "
            "is exploratory, not a finding.",
        ]
    ]
    assert "Directory: app/20261006T000000Z" in [x for _, x in pad_only]
    # the page did not see the stage start (no mark): its range, no time so far
    now_unseen = {"ran": None, "span": [25, 160], "over": False}
    assert out["stages"][base] == [
        {"label": "Preflight", "state": "done", "took": None},
        {"label": "Pad baseline, cached", "state": "done", "took": None},
        {"label": "Variant", "state": "done", "took": None},
        {"label": "Comparison and offload", "state": "now", "took": None, **now_unseen},
        {"label": "Writing the results", "state": "to come", "took": None},
    ]
    # the comparison stage's parts are the pad control, the solve and the paired pad (the
    # variant runs in its own stage): 41 s to 4 min 30 s; 30 s so far (50 - 20)
    assert out["stages"][base + 4][3] == {
        "label": "Comparison and offload",
        "state": "now",
        "took": None,
        "ran": 30.0,
        "span": [41, 270],
        "over": False,
    }
    assert out["now"][base + 4] == ["30 s (expected 41 s to 4 min 30 s)"]
    assert out["now"][base + 5] == ["50 s (expected 5 s to 10 s; longer than expected)"]
    # the mark names another stage: the page did not see this one start, so no time so far
    assert out["stages"][base + 6][3]["ran"] is None
    assert out["now"][base + 6] == ["(expected 41 s to 4 min 30 s)"]
    assert out["now"][base] == ["(expected 25 s to 2 min 40 s)"]
    plain, raw = out["jobs"][base + 7], out["jobs"][base + 8]
    assert [
        "p.caution",
        "Stage 1 never lit: the coast after release peaked at 300.65 m, 0.25 m below its "
        "ramp-start altitude of 300.90 m. A ramp start below the coast's peak lets it light.",
    ] in plain
    assert [
        "p.caution",
        "Why, in the search's own words: search_failed: grid: first failure: drive_limit: x",
    ] in raw
    assert not any(
        "never lit" in x or "own words" in x for _, x in out["jobs"][kinds.index("complete")]
    )
    # a pad-only launch (its dry run named one run) has no variant; each finished stage
    # carries the duration the page saw
    assert out["stages"][base + 1] == [
        {"label": "Preflight", "state": "done", "took": 0.4},
        {"label": "Pad baseline, cached", "state": "done", "took": 0.0},
        {"label": "Variant (none: pad only)", "state": "done", "took": None},
        {"label": "Comparison and offload", "state": "done", "took": 2.5},
        {"label": "Writing the results", "state": "done", "took": None},
    ]


# ------------------------------------------------------------------ the page's contracts


def test_silo_note_display_only_and_the_frame_contract(template: str) -> None:
    """The Silo details group says what the carriage mass and the impingement fraction
    change under the prescribed drive (honesty review 02 on 4.10), and the results panel
    says the same beside every push of that drive (review of A5); the panel names what
    the scene draws that the model does not compute (design 4.9, from the record's
    display_only); the frame: no border of its own, the page measures the scene's body
    (plus the frame's border) and gives the scene its own window's height as --app-vh,
    which scene.html's embed rules read instead of vh (the frame's own height), and the
    scene's own run selectors are hidden in the frame (the page's pickers choose)."""
    silo = template[
        template.index('<fieldset id="g-silo">') : template.index('<fieldset id="g-ramp">')
    ]
    assert '<p class="meta" id="siloNote"></p>' in silo
    script = _script(template)
    note = (
        'const DRIVE_NOTE = "Under the prescribed constant-acceleration drive the carriage mass '
        'and the impingement fraction " +\n    "change only the drive\'s force, energy and peak '
        'power: not the release speed, the payload or the offload.";'
    )
    assert note in script
    assert '$("siloNote").textContent = DRIVE_NOTE;' in _body(script, "buildForm")
    assert "if (p.push.model === CONSTANT_ACCEL)" in _body(script, "panelBlocks")
    assert "p.display_only" in _body(script, "panelBlocks")
    fit = _body(script, "fitFrame")
    assert "const chrome = frame.offsetHeight - frame.clientHeight;" in fit
    assert "doc.body.getBoundingClientRect().height" in fit
    assert 'setProperty("--app-vh"' in _body(script, "giveViewHeight")
    assert "giveViewHeight(doc);" in _body(script, "frameLoaded")
    assert "#frame { display: block; width: 100%; height: 640px; border: 0;" in template
    scene_html = (REPO / "src" / "launchsim" / "templates" / "scene.html").read_text(
        encoding="utf-8"
    )
    embed = scene_html[
        scene_html.index("/* In the app's frame") : scene_html.index(
            "@media (prefers-reduced-motion"
        )
    ]
    assert 'html[data-embed="1"] .runpick { display: none; }' in embed
    rules = re.findall(r'html\[data-embed="1"\] #scene(?:\.two)? \{ height: ([^;]*); \}', embed)
    assert len(rules) == 7 and all("var(--app-vh, 100vh)" in r for r in rules)
    assert "vh" not in "".join(rules).replace("var(--app-vh, 100vh)", "")


def test_a_launch_sends_only_the_request_the_check_passed(template: str) -> None:
    """Review of A5: the confirmation names one request; editing the form (a field, a
    choice, a check box or a preset) hides it; startLaunch launches only when the Launch
    button is enabled, the dry run passed this very request and, when a confirmation was
    shown, it named this request; launching the configuration just launched asks again
    (review 06 finding 7)."""
    script = _script(template)
    start = _body(script, "startLaunch")
    guard = (
        'if ($("launchBtn").disabled || S.derivedFor !== sent || '
        "(confirmed !== null && confirmed !== sent)) return;"
    )
    assert guard in start and start.index(guard) < start.index("postLaunch(")
    assert "hideConfirm();" in _body(script, "edited")
    assert "hideConfirm();" in _body(script, "choosePreset")
    assert "S.confirmFor = null;" in _body(script, "hideConfirm")
    clicked = _body(script, "launchClicked")
    assert "S.confirmFor = sent;" in clicked
    assert "S.lastLaunched !== null && sent === S.lastLaunched" in clicked
    assert "Launch the same configuration again? It writes another results directory." in clicked
    assert "S.lastLaunched = sent;" in start


def test_a_scene_already_in_the_frame_is_not_loaded_again(template: str) -> None:
    """Opening the scene the frame shows (or is loading) changes no src: a new src that
    differs only in its fragment is a same-document navigation with no load event, which
    would leave the page waiting for the frame and stop the keys and the theme reaching
    it. A scene that did not start leaves the frame on about:blank, so asking for it again
    is a real navigation; frameLoaded acts only on the load it waits for."""
    script = _script(template)
    load = _body(script, "loadScene")
    same = 'if (current === path && (S.frameState === "ready" || S.frameState === "loading")) {'
    assert same in load and load.index(same) < load.index("frame.src = path")
    assert (
        "const current = S.scene ? scenePath(S.scene.experiment, S.scene.timestamp, "
        "S.scene.runs) : null;" in load
    )
    loaded = _body(script, "frameLoaded")
    assert 'if (!S.scene || S.frameState !== "loading") return;' in loaded
    assert 'S.frameState = "failed";' in loaded and 'frame.src = "about:blank";' in loaded


def test_keys_theme_and_what_a_finished_launch_opens(template: str) -> None:
    """Review of A5 (compliance): keys reach the player only from outside form controls
    and buttons (a Space on a focused Launch button presses it, review 06 finding 7), and
    every one of them (Space, [, ], the arrows) only while the scene is on screen, so a
    Space with the scene out of sight scrolls the page and never counts as touching the
    player (round 3); Shift passed; the hint says so; a frame with focus inside it draws
    the focus ring; the frame's theme is set by
    data-theme when the theme changes and when a scene loads; a finished launch opens its
    scene only if the player was not touched after Launch (design 4.7), and the user's own
    choice of a scene (the run list, the pickers, Open this launch, SP1's recorded run)
    counts as a touch, so it is never replaced; restoring a view and showing the new
    launch do not count; the job card shows no second button for the launch the 'Show the
    new launch' button offers; a long or repeated launch's confirmation focuses 'Not now',
    so one Space never confirms a launch that cannot be cancelled."""
    script = _script(template)
    forward = _body(script, "forwardKey")
    assert _first_statement(forward) == "const arrow = has(ARROW_KEYS, e.key);"
    assert "if ((!has(FORWARD_KEYS, e.key) && !arrow)" in forward
    assert '"INPUT", "SELECT", "TEXTAREA", "BUTTON"' in forward
    assert "t.isContentEditable" in forward
    assert "if (!doc || !frameOnScreen()) return;" in forward and "shiftKey: e.shiftKey" in forward
    assert forward.index("if (!doc || !frameOnScreen()) return;") < forward.index(
        "e.preventDefault();"
    )
    assert forward.index("if (!doc || !frameOnScreen()) return;") < forward.index(
        "S.playerTouchedAt"
    )
    assert "While the scene is on screen, Space plays or pauses" in template
    assert (
        "#frame:focus-within { outline: 2px solid var(--focus); outline-offset: -2px; }" in template
    )
    assert 'const FORWARD_KEYS = [" ", "[", "]"];' in script
    assert 'const ARROW_KEYS = ["ArrowLeft", "ArrowRight"];' in script
    theme = 'doc.documentElement.setAttribute("data-theme", effectiveTheme())'
    assert theme in _body(script, "applyTheme") and theme in _body(script, "frameLoaded")
    assert "S.playerTouchedAt > S.launchedAt" in _body(script, "jobFinished")
    load = _body(script, "loadScene")
    assert "S.playerTouchedAt = chosen === true ? Date.now() : 0;" in load
    assert "if (chosen === true) S.playerTouchedAt = Date.now();" in load
    # a change of the pickers is the user's own choice and keeps the clock (round 3)
    assert "pair, false, true, frameTime());" in _body(script, "pickersChanged")
    assert 'doc.getElementById("scrub")' in _body(script, "frameTime")
    assert "pair, focus, chosen);" in _body(script, "openDirectory")
    calls = _calls_outside_definition(script, "openDirectory")
    assert len(calls) == 5
    for pos in calls:
        call = script[pos : script.index(";", pos)]
        if _inside(script, pos, "showNewLaunch") or _inside(script, pos, "restoreView"):
            assert not call.endswith(", true, true)"), call
        else:
            assert call.endswith("[], true, true)"), call
    assert "!offerPending(dir)" in _body(script, "renderJob")
    assert _body(script, "showNewLaunch").rstrip().endswith("renderJob();")
    clicked = _body(script, "launchClicked")
    assert '$("confirmNo").focus();' in clicked and '"confirmYes").focus' not in clicked


def test_job_card_notice_refusal_and_browser_rules(template: str) -> None:
    """Review of A5: the job card is no live region (it is rebuilt on every poll); one
    status line announces a change of the job's state or stage only; the job card's
    headline is the launch's own (its directory's default panel), never that of a pair
    the pickers chose later; the notice heads the layout, so on a wide screen it tops the
    right-hand column and the form card's top stays at the header's foot (its max-height
    assumes it); a page another site opened says it does not check the form until used,
    and checks it as the form arrives when the user acted first; a refused field's line is
    the server's own (no label in front); the penalty's caveat is said once; a failed
    row's FAILED.txt line is not repeated after its description."""
    script = _script(template)
    assert '<section class="card" id="jobCard" aria-labelledby="jobTitle">' in template
    assert '<p class="vh" id="jobLive" role="status"></p>' in template
    assert "if (key === S.jobLiveKey) return;" in _body(script, "announceJob")
    assert "announceJob(job);" in _body(script, "handleJob")
    render = _body(script, "renderJob")
    assert "S.detail.panel" not in render and "S.dirHeadline" in render
    opened = _body(script, "openDirectory")
    assert "S.dirHeadline = {" in opened and "experiment: dir.experiment, timestamp:" in opened
    # the job card's plain reason of a launch that did not fly is its own panel's first flag
    assert "why: h && h.kind === DID_NOT_FLY && flags.length ? String(flags[0]) : null" in opened
    assert "why: launchHead ? launchHead.why : null" in render
    assert "S.dirHeadline" not in _body(script, "loadPanel")
    layout = template[template.index('<div class="layout">') :]
    assert layout.startswith(
        '<div class="layout">\n<p class="notice" id="notice" role="status" hidden></p>\n'
        '<section class="card" id="formCard"'
    )
    assert ".layout > .notice { grid-column: 2; grid-row: 1;" in template
    assert "#formCard { grid-column: 1; grid-row: 1 / span 2;" in template
    boot = _body(script, "boot")
    assert "Until you use the page it does not check the form" in boot
    assert "It checks the form" not in boot
    assert "if (plan.dryRun || mayActNow()) scheduleDryRun(0);" in boot
    assert "S.refusal = { field: field, message: message };" in _body(script, "showRefusal")
    assert template.count("a parametric stand-in for the structure a push needs") == 1
    assert 'row.state !== "complete" && row.state !== "failed"' in _body(script, "renderBrowser")
    assert _body(script, "rampStartText").count('"The ramp start') == 2
    # the stage-2 pre-offload's reading follows the propellant choice: under a stage-1
    # solve (whose pad control runs) it never says 'no pad control'
    pre = _body(script, "preReading")
    assert "before the stage-1 solve: the solved x* is the stage-1 offload" in pre
    assert '"A stage-2 pre-offload is imposed on stage 2 before the stage-1 offload: "' in pre
    assert pre.index("if (v.propellant === SOLVE)") < pre.index("adv.fixed_reading")
    assert '$("readingPre").textContent = preReading(v);' in _body(script, "renderForm")


FOLD_HARNESS = (
    HARNESS_HEAD
    + """
const out = {};
out.titles = [sp1FoldTitle(input.head, true), sp1FoldTitle(input.head, false)];
out.edited = input.edits.map(c => editedKeys(c, input.base, input.keys, {}));
const d = { experiment: "app", timestamp: "20261006T000000Z" };
const roots = [{ path: "results", tracked: true }, { path: "scratch", tracked: false },
  { path: null, tracked: false }];
out.dirs = [dirText(d, roots[0]), dirText(d, roots[2]), dirText(d, null)];
out.roots = roots.map(rootText);
process.stdout.write(JSON.stringify(out));
"""
)
EDIT_BASE = {
    "site": "silo",
    "stroke_m": 100,
    "push_by": "net_accel_g",
    "net_accel_g": 3.0,
    "exit_speed_mps": 76.70717046013364,
    "carriage_mass_t": 0,
    "exhaust_impingement_fraction": 0,
    "ramp_by": "time_release",
    "t_ign_s": 0.5,
    "startup": "vehicle_default",
    "propellant": "full",
    "fails": False,
    "advanced": False,
}


@pytest.mark.skipif(NODE is None, reason="node not installed: the page helpers are not run")
def test_sp1_fold_edited_list_and_results_root_under_node(template: str, tmp_path: Path) -> None:
    """Review of A5: SP1's headline sits folded in a results panel, its summary saying what
    an app run reproduces of it (the case's x* only: the penalty rows, the range, the
    screening ratio and the bridge come from SP1's runs) or that the directory is SP1's
    own, and the run's own numbers follow; an offload launch's comparison lists what
    differs by config key, with a note when the push is stated the other way; the 'Edited
    from' list is the fields whose effective value differs from the preset's (a field
    changed back, or a converted value that snapped back, is not listed); where launches
    are written, as the job card and the idle line say it."""
    head = app.SP1_HEADLINE.record()
    out = _run_pure(
        template,
        FOLD_HARNESS,
        {
            "head": head,
            "base": EDIT_BASE,
            "keys": [*EDIT_BASE, "preset"],
            "edits": [
                EDIT_BASE,
                {**EDIT_BASE, "push_by": "exit_speed_mps"},
                {**EDIT_BASE, "t_ign_s": 0.5000000000000002},
                {**EDIT_BASE, "stroke_m": 150},
            ],
        },
        tmp_path,
    )
    assert out["titles"] == [
        "SP1's headline. This launch reproduces only its silo_cold_s1 figure (x* 41.26 t): a "
        "reproduction, not new evidence. The penalty rows, the +/-10% range, the screening "
        "ratio and the README-loads bridge come from SP1's runs, not from this launch. Its "
        "text and its 6 caveat groups.",
        "SP1's headline: this directory is SP1's own run of its case (silo_cold_s1). Its text "
        "and its 6 caveat groups.",
    ]
    assert out["edited"] == [[], ["push_by", "net_accel_g", "exit_speed_mps"], [], ["stroke_m"]]
    # a folder outside the repository: no local path from the server, so the page says
    # where it is (the server's console prints it at start; review of A5, usability)
    where = 'its full path is the "results root" line the server printed in its console at start'
    assert out["dirs"] == [
        "results/app/20261006T000000Z",
        f"app/20261006T000000Z under the --results-root folder ({where})",
        "app/20261006T000000Z",
    ]
    assert out["roots"][0].startswith("results/app/<UTC time>/ in the repository (tracked")
    assert out["roots"][1].endswith("(not the tracked results/)")
    assert f"outside the repository (not tracked; {where})" in out["roots"][2]
    assert 'say(f"  results root: {results}")' in (REPO / "src" / "launchsim" / "cli.py").read_text(
        encoding="utf-8"
    )
    differs = [
        "assist.net_accel_g: not set (SP1's silo_cold_s1: 3.0)",
        "assist.exit_speed_mps: 76.70717046013364 (SP1's silo_cold_s1: not set)",
    ]
    record = _record(
        "complete",
        sp1_headline=head,
        sp1_comparison={
            "case": "silo_cold_s1",
            "reproduces": False,
            "differs": differs,
            "text": SP1_TEXT,
        },
    )
    record["runs"].append(
        {
            "name": "s1",
            "role": "offload",
            "offload_kind": "offload case",
            "note": "n",
            "has_rows": True,
        }
    )
    lines = _run_pure(template, sup.PAGE_BLOCKS_HARNESS, {"details": [record]}, tmp_path)["panels"][
        0
    ]
    tags = [t for t, _ in lines]
    texts = [x for _, x in lines]
    fold = tags.index("fold.sp1")
    assert texts[fold] == out["titles"][0]
    assert tags[fold + 1] == "p" and texts[fold + 1] == head["text"]
    assert "h3" not in tags[fold : tags.index("/fold")]
    assert tags.index("/fold") < texts.index("Push")
    at = texts.index("What differs from SP1's silo_cold_s1, by config key")
    assert texts[at + 1 : at + 4] == [
        *differs,
        "Compared by config key: a push stated as exit speed instead of net acceleration (or "
        "the reverse) is listed under both keys even when it is the same push; the form's "
        "derived values show whether it is.",
    ]


# ------------------------------------------------------------------ round 3 of the A5 review


def test_a_server_restart_resets_the_per_job_state(template: str) -> None:
    """Review of A5, round 3 (compliance): a new server numbers its jobs from 1 again, so a
    restart clears every piece of the page's state keyed by job id (the stage times, the
    stage mark, the launch this page started, the announced state); a launch's reply from
    a new server resets that state before the page records its own launch (its runs and
    parts), and the page's own launch starts its stage clock at 0."""
    script = _script(template)
    restarted = _body(script, "serverRestarted")
    resets = (
        "S.stageTimesFor = null;",
        "S.stageTimes = {};",
        "S.stageMark = null;",
        "S.jobStarted = null;",
        'S.jobLiveKey = "";',
    )
    for line in resets:
        assert line in restarted, line
        assert restarted.index("S.job = null;") < restarted.index(line), line
    start = _body(script, "startLaunch")
    accepted = start[start.index("if (res.status === 202 && body.job) {") :]
    accepted = accepted[: accepted.index("} else if (res.status === 409")]
    boot = "if (body.job.boot_id !== S.bootId) serverRestarted(body.job);"
    assert _first_statement(accepted.split("{", 1)[1]) == boot
    for line in ("S.lastLaunched = sent;", "S.launchItems = items;", "S.launchRuns = runs;"):
        assert accepted.index(boot) < accepted.index(line), line
    assert accepted.index("S.stageTimesFor = null;") < accepted.index("markStages(body.job);")
    assert accepted.index("S.jobStarted = body.job.id;") < accepted.index("markStages(body.job);")


WAY_HARNESS = (
    HARNESS_HEAD
    + """
const out = {};
out.way = [["note", "depth", "depth"], ["note", "depth", "time_release"], ["", "depth", "depth"],
  [null, null, "time_release"]].map(c => wayNoteText(c[0], c[1], c[2]));
const loads = input.loads;
out.offload = input.values.map(v => offloadRows(v, loads));
out.none = offloadRows({ propellant: "fixed", fixed_key: "stage1_t", fixed_value: 20 }, null);
process.stdout.write(JSON.stringify(out));
"""
)


@pytest.mark.skipif(NODE is None, reason="node not installed: the page helpers are not run")
def test_way_note_and_offload_rows_under_node(
    template: str, tmp_path: Path, shipped_info: dict[str, Any]
) -> None:
    """Review of A5, round 3 (usability): the ramp-start way's note shows only under the
    way it was written for (choosing the depth, then Pad only, which shows the time from
    release, hides it); the derived values state an imposed offload in tonnes and as a
    share of its stage's load whichever way it is typed (GET /api/form loads_t), a
    both-stage fraction per stage, a stage-2 pre-offload against stage 2's load, and say a
    solve's figure comes after the launch; nothing without the loads."""
    values = [
        {"propellant": "fixed", "fixed_key": "stage1_fraction", "fixed_value": 0.05},
        {"propellant": "fixed", "fixed_key": "stage1_t", "fixed_value": 30, "stage2_offload_t": 2},
        {"propellant": "fixed", "fixed_key": "stage2_t", "fixed_value": 5.375},
        {"propellant": "fixed", "fixed_key": "both_fraction", "fixed_value": 0.05},
        {"propellant": "solve", "solve_mode": "stage1", "stage2_offload_t": 0},
        {"propellant": "full", "stage2_offload_t": 2},
        {"propellant": "fixed", "fixed_key": "stage1_t", "fixed_value": None},
    ]
    loads = {"stage1": 410.9, "stage2": 107.5, "both": 518.4}
    out = _run_pure(template, WAY_HARNESS, {"values": values, "loads": loads}, tmp_path)
    assert out["way"] == ["note", "", "", ""]
    assert out["offload"] == [
        [["Imposed offload", "20.55 t, 5.00% of stage 1's 410.9 t load"]],
        [
            ["Imposed offload", "30.00 t, 7.30% of stage 1's 410.9 t load"],
            [
                "Stage-2 pre-offload",
                "2.00 t, 1.86% of stage 2's 107.5 t load (a property of the vehicle model, "
                "not netted)",
            ],
        ],
        [["Imposed offload", "5.38 t, 5.00% of stage 2's 107.5 t load"]],
        [
            [
                "Imposed offload",
                "20.55 t from stage 1 and 5.38 t from stage 2 (5.00% of each load, 410.9 t and "
                "107.5 t): 25.92 t in all",
            ]
        ],
        [["Offload", "solved at the pad's payload: the figure appears after the launch"]],
        [],
        [],
    ]
    assert out["none"] == []
    # the page reads the loads GET /api/form serves
    assert set(shipped_info["loads_t"]) == {"stage1", "stage2", "both"}
    script = _script(template)
    assert "offloadRows(v, S.info ? S.info.loads_t : null)" in _body(script, "renderDerived")
    render = _body(script, "renderForm")
    assert (
        'setText("rampWayNote", wayNoteText(S.form.wayNote, S.form.wayNoteFor, v.ramp_by));'
        in render
    )
    assert "S.form.wayNoteFor = value;" in _body(script, "onChoice")


def test_preset_label_reset_footer_and_push_start_default(
    template: str, shipped_info: dict[str, Any]
) -> None:
    """Review of A5, round 3: the preset's whole label is written under the select (the
    select cuts a long option off); while fields are edited a 'Reset to <preset>' button
    sits in the edited note and chooses the preset again (its request again: choosePreset
    takes the preset's request, which the preset test checks), then checks the form; the
    footer says what the code check refuses and what it does not (an uncommitted edit);
    the time-from-push-start way shows the default stated from push start (GET /api/form
    push_start_default: silo_cold's +0.5 s after release), never the release default."""
    assert (
        '<div class="why" id="presetEdited" hidden><p id="presetEditedText"></p>'
        '<button type="button" id="resetPreset"></button></div>' in template
    )
    script = _script(template)
    render = _body(script, "renderForm")
    assert '$("presetCommitted").textContent = !preset ? "" : preset.label + ". "' in render
    assert '$("presetEdited").hidden = changed.length === 0;' in render
    assert '$("resetPreset").textContent = "Reset to " + S.form.preset;' in render
    reset = _body(script, "resetPreset")
    assert reset.index("choosePreset(S.form.preset);") < reset.index("scheduleDryRun(0);")
    assert 'addEventListener("click", () => { resetPreset(); });' in script
    foot = _body(script, "buildForm")
    assert (
        "a launch is refused once HEAD moves to a commit that changes src, configs, experiments, "
        in foot
    )
    assert (
        "(an uncommitted edit is not refused: each launch records the working tree's state)" in foot
    )
    assert "a launch is refused after a code change" not in template
    assert "pushStart ? pushStartDefault()" in _body(script, "metaLine")
    default = shipped_info["push_start_default"]
    assert default["preset"] == "silo_cold"
    assert default["time_after_release_s"] == pytest.approx(0.5, abs=1e-9)
    # 100 m at 3 g0 net: the push lasts sqrt(2 L / a) = 2.6073 s, so +0.5 s after release
    # is 3.1073 s after the push starts
    assert default["value"] == pytest.approx(3.1073181789953295, abs=1e-6)


# ------------------------------------------------------------------ the video control (step A6v)


def test_video_control_structure_and_routes(template: str) -> None:
    """Step A6v (design 4.8, D-SP2-30, review 06 finding 9): the Save video (MP4) control
    sits in the scene card beside the frame with fps and width selects, the natural
    length, Save, Cancel, a progress line, the path with a copy button and an error line;
    the frame rate and width come from GET /api/form's video block at its defaults; a
    video starts only from its button's click; the frame loop captures each frame with the
    server's footer lines and awaits each POST (no timer in it); the finish is followed
    by a poll; every video route is a literal /api/ path; the control is disabled with a
    reason while a launch runs or when the export is off."""
    card = template[
        template.index('<section class="card" id="sceneCard"') : template.index(
            '<section class="card" id="browser"'
        )
    ]
    for part in (
        '<div class="video" id="videoBox" aria-labelledby="videoTitle">',
        '<h3 id="videoTitle" class="grouplabel">Save video (MP4)</h3>',
        '<select id="videoFps" aria-describedby="videoLength">',
        '<select id="videoWidth" aria-describedby="videoLength">',
        '<button type="button" id="videoStart" disabled>Save video (MP4)</button>',
        '<button type="button" id="videoCancel" hidden>Cancel</button>',
        '<p class="meta" id="videoLength"></p>',
        '<p class="why" id="videoWhy" hidden></p>',
        '<p class="meta" id="videoProgress" hidden></p>',
        '<code id="videoPath"></code><button type="button" id="videoCopy">Copy the path</button>',
        '<p class="err" id="videoErr" role="alert" hidden></p>',
    ):
        assert part in card, part
    assert card.index('id="videoBox"') < card.index('<iframe id="frame"')
    script = _script(template)
    build = _body(script, "buildVideoControls")
    assert "fps.value = String(info.default_fps);" in build
    assert "width.value = String(info.default_width);" in build
    # a video only from the button's click
    clicks = _click_spans(script)
    for pos in _calls_outside_definition(script, "startVideo"):
        assert any(a < pos < b for a, b in clicks), pos
    start = _body(script, "startVideo")
    assert (
        'if ($("videoStart").disabled || S.video.active || !mayActNow() || jobRunning()) return;'
        in start
    )
    assert 'api("/api/videos", { method: "POST"' in start
    assert "frames: plan.frames, times: plan.times" in start
    assert "return captureLoop(v);" in start
    assert 'encodeURIComponent(v.id) + "/finish"' in start and "pollVideo(v);" in start
    loop = _body(script, "captureLoop")
    assert "v.hook.captureFrame(v.times[k], v.width, v.height, v.footer)" in loop
    assert (
        'api("/api/videos/" + encodeURIComponent(v.id) + "/frames/" + k, '
        '{ method: "POST", headers: { "Content-Type": "image/png" }, body: blob })' in loop
    )
    assert "return next(k + 1, 0);" in loop and "if (v.cancel) return Promise.resolve" in loop
    # no timer drives the frame cadence: each POST is awaited; the one timer of a capture is
    # the pause before a lost POST is looked into (retryPause, outside the loop; fix round 3)
    assert (
        "setTimeout" not in loop
        and "setInterval" not in loop
        and "requestAnimationFrame" not in loop
    )
    assert "if (!res.ok) throw new Error" in loop
    # fix round 3 (compliance pass 3 finding 5, honesty pass 3): a frame POST that gets no
    # response (a TypeError from fetch: the connection was lost) is looked into after
    # retryPause through the session's record, and the loop resumes at received (k or k + 1);
    # after VIDEO_FRAME_RETRIES losses of one frame the save fails naming the frame
    assert "const VIDEO_RETRY_MS = 1000;" in script and "const VIDEO_FRAME_RETRIES = 3;" in script
    assert "setTimeout(resolve, VIDEO_RETRY_MS)" in _body(script, "retryPause")
    assert "retryPause().then(() => fetchVideo(v))" in loop
    assert (
        'if (rec.state !== "capturing" || (rec.received !== k && rec.received !== k + 1)) '
        "throw lost(k);" in loop
    )
    assert "return next(rec.received, rec.received === k ? losses : 0);" in loop
    assert "if (!(err instanceof TypeError) || losses >= VIDEO_FRAME_RETRIES) throw" in loop
    assert '"the connection was lost while posting frame " + k + " of " + v.frames' in loop
    assert "return next(0, 0);" in loop
    poll = _body(script, "pollVideo")
    assert "fetchVideo(v).then(rec =>" in poll
    assert "setTimeout(() => pollVideo(v), VIDEO_POLL_MS)" in poll
    assert '$("videoPath").textContent = rec.path;' in poll
    fetch = _body(script, "fetchVideo")
    assert 'api("/api/videos/" + encodeURIComponent(v.id))' in fetch
    assert "if (!res.ok || !res.body || !res.body.video) throw new Error(errorText(res));" in fetch
    # fix round 1: after a failure on the page's side (a frame POST whose refusal was lost with
    # its connection) the server's own record is read once, and a failed session's error shown
    assert ".catch(err => recordAfterFailure(v).then(rec =>" in start
    assert 'videoFailed("Video not saved: " + (failed ? rec.error : err.message));' in start
    assert "if (v.id && open) cancelSession(v, true)" in start
    after = _body(script, "recordAfterFailure")
    assert "if (!v.id) return Promise.resolve(null);" in after
    assert "return fetchVideo(v).catch(() => null);" in after
    assert 'encodeURIComponent(v.id) + "/cancel"' in _body(script, "cancelSession")
    # the literals: create, frames, finish, cancel, the record (comments name the routes too)
    assert len(re.findall(r'"/api/videos', script)) == 5
    # the note follows the planned clip (fix round 1: "the player's default rate" only when the
    # clip is not scaled), so renderVideo writes it, not buildVideoControls
    assert '$("videoNote")' not in build
    render = _body(script, "renderVideo")
    assert '$("videoNote").textContent = info && info.available ? videoNoteText(' in render
    assert "videoNoteText(info.folder, scaled)" in render
    assert "scaled = !!(plan && plan.scaled);" in render
    # fix round 2 (compliance pass 2): while a clip is being saved the note and the length
    # line describe that clip's own plan (scaled or not), carried on the active record
    assert (
        'let why = "", length = active ? active.lengthText : "", '
        "scaled = active ? active.scaled === true : false;" in render
    )
    assert (
        "scaled: plan.scaled === true, lengthText: clipLengthText(plan, plan.natural_s, " in start
    )
    assert "maxFrameBytes: Number(info.max_frame_bytes)" in start
    # fix round 2 (security pass 2): a captured frame over the server's frame cap is refused
    # on the page before the POST (the server answers such a body 413 unread, which the
    # browser can report as a lost connection), with capture=true so Save stays off for the
    # size until the scene changes
    assert "if (Number.isFinite(v.maxFrameBytes) && blob && blob.size > v.maxFrameBytes) {" in loop
    assert "const e = new Error(frameTooLarge(k, blob.size, v.maxFrameBytes));" in loop
    assert loop.count("e.capture = true;") == 2
    assert loop.index("blob.size > v.maxFrameBytes") < loop.index('"/frames/" + k')
    assert '"A launch is running: a launch and a video never run together."' in render
    assert '"The MP4 export is off: " + (info.reason || "no reason given")' in render
    assert '"Load a scene first: the video films the scene in the frame."' in render
    assert "const plan = videoPlan(hook);" in render
    # the fit check: a frame of the chosen size drawn once per scene and size before Save is
    # offered (two panels under the caveat footer do not fit 960 x 540 px); a capture that
    # fails during a save keeps the size off and its message on the page
    assert "const fit = videoFit(hook, c, plan);" in render
    assert "hook.captureFrame(plan.times[0], c.width, c.height)" in _body(script, "videoFit")
    assert "if (err.capture === true) S.video.fit = " in start
    assert "cancelSession(v, true)" in start
    assert "if (quiet === true) return;" in _body(script, "cancelSession")
    assert "hook.clipTimes(c.fps)" in _body(script, "videoPlan")
    assert "clipPlan(natural.natural_s, c.fps, info.max_frames)" in _body(script, "videoPlan")
    assert "renderVideo();" in _body(script, "renderLaunch")
    assert "renderVideo();" in _body(script, "frameLoaded")
    assert "renderVideo();" in _body(script, "clearScene")
    assert "navigator.clipboard.writeText(text)" in _body(script, "copyVideoPath")
    assert "scenePath(" not in _body(script, "sceneKey")


VIDEO_HARNESS = (
    HARNESS_HEAD
    + """
const out = {};
out.plans = input.plans.map(c => clipPlan(c[0], c[1], c[2]));
out.texts = input.plans.map(c => {
  const p = clipPlan(c[0], c[1], c[2]);
  return clipLengthText(p, c[0], c[1], 1280, 720, c[2]);
});
out.progress = [videoProgressText(0, 1800, 0), videoProgressText(12, 1800, 1020),
  videoProgressText(1800, 1800, 150000)];
out.notes = [videoNoteText("C:\\\\work", false), videoNoteText("C:\\\\work", true)];
const g = input.gate;
out.gate = [clipPlan(g[0], g[1], g[2]), clipPlan(g[0], 24, g[2])];
out.gateText24 = clipLengthText(clipPlan(g[0], 24, g[2]), g[0], 24, 1280, 720, g[2]);
out.tooLarge = frameTooLarge(7, input.cap + 1, input.cap);
process.stdout.write(JSON.stringify(out));
"""
)

CAPTURE_LOOP_HARNESS = """
const calls = [];
function api(path, opts) {
  calls.push(path);
  return Promise.resolve({ ok: true, status: 200, body: {} });
}
function sameScene(v) { return true; }
function renderVideoProgress(v) {}
function errorText(res) { return "HTTP " + res.status; }
const cap = input.cap;
const base = { id: "abc", frames: 3, times: [0, 1, 2], width: 1280, height: 720, footer: [],
  sent: 0, cancel: false, maxFrameBytes: cap };
const hookOf = size => ({ captureFrame: () => Promise.resolve({ size: size }) });
const over = Object.assign({}, base, { hook: hookOf(cap + 1) });
const fits = Object.assign({}, base, { hook: hookOf(cap) });
const out = {};
captureLoop(over)
  .then(r => { out.over = { outcome: r }; },
        e => { out.over = { error: e.message, capture: e.capture === true }; })
  .then(() => { out.callsAfterOver = calls.length; return captureLoop(fits); })
  .then(r => { out.fits = { outcome: r, sent: fits.sent, calls: calls.slice() }; },
        e => { out.fits = { error: e.message }; })
  .then(() => process.stdout.write(JSON.stringify(out)));
"""


def _function_source(script: str, name: str) -> str:
    """The whole text of ``function name(...) { ... }`` in the page's script."""
    start = re.search(rf"\bfunction {re.escape(name)}\(", script)
    assert start is not None, name
    _brace, end = _function_span(script, name)
    return script[start.start() : end + 1]


@pytest.mark.skipif(NODE is None, reason="node not installed: the clip plan is not run")
def test_clip_plan_under_node(template: str, tmp_path: Path) -> None:
    """clipPlan: round(fps x natural) frames over the natural length; over the server's
    limit the clip is scaled to limit / fps seconds with the limit's frames; bad inputs
    give null; the length line (the clip from the first row to the end; a scaled clip's
    clock against the player's) and the progress line say so; the note promises the player's
    default rate only for an unscaled clip (fix round 1); the gate pair's natural clip (86.4
    s) is not scaled at the default frame rate, and would be at 24 fps."""
    plans = [
        [72.63, 24, 1800],
        [72.63, 30, 1800],
        [75.0, 24, 1800],
        [75.1, 24, 1800],
        [0.01, 10, 1800],
        [0, 24, 1800],
        [None, 24, 1800],
        [72.63, 24, 0],
        ["x", 24, 1800],
    ]
    gate = [86.4, video.DEFAULT_FPS, video.MAX_FRAMES]
    out = _run_pure(
        template,
        VIDEO_HARNESS,
        {"plans": plans, "gate": gate, "cap": video.MAX_FRAME_BYTES},
        tmp_path,
    )
    # fix round 2: the length line of the gate pair at 24 fps (what the page keeps showing
    # while such a clip is saved) and the page's own frame-cap refusal
    assert out["gateText24"] == (
        "Natural length 86.4 s at 24 fps would be 2074 frames, over the limit of 1800: the clip "
        "is scaled to 75.0 s (1800 frames of 1280 x 720 px, the same scene from the first row to "
        "the end at a clock 1.15x the player's)."
    )
    assert out["tooLarge"] == (
        f"frame 7 is {video.MAX_FRAME_BYTES + 1} bytes, over the server's "
        f"{video.MAX_FRAME_BYTES}-byte frame cap: choose a narrower frame"
    )
    assert out["plans"][0] == {"frames": 1743, "seconds": 72.63, "scaled": False}
    assert out["plans"][1] == {"frames": 1800, "seconds": 60.0, "scaled": True}
    assert out["plans"][2] == {"frames": 1800, "seconds": 75.0, "scaled": False}
    assert out["plans"][3] == {"frames": 1800, "seconds": 75.0, "scaled": True}
    assert out["plans"][4] == {"frames": 1, "seconds": 0.01, "scaled": False}
    assert out["plans"][5:] == [None, None, None, None]
    assert out["texts"][0] == (
        "Natural length 72.6 s at 24 fps: 1743 frames of 1280 x 720 px, from the first row to "
        "the end."
    )
    assert out["texts"][1] == (
        "Natural length 72.6 s at 30 fps would be 2179 frames, over the limit of 1800: the clip "
        "is scaled to 60.0 s (1800 frames of 1280 x 720 px, the same scene from the first row to "
        "the end at a clock 1.21x the player's)."
    )
    assert out["texts"][5] == "The clip's length could not be measured."
    assert out["gate"][0] == {"frames": 1728, "seconds": 86.4, "scaled": False}
    assert out["gate"][1]["scaled"] is True and out["gate"][1]["frames"] == 1800
    assert out["notes"][0].startswith(
        "The clip plays the scene in the frame at the player's default rate, from the first row "
        "to the end, with the caveat footer on every frame; it is written to C:\\work (the "
        "server's working directory)"
    )
    assert out["notes"][1].startswith(
        "The clip plays the scene in the frame at a clock faster than the player's default rate "
        "(its natural length at this frame rate passes the frame limit: the length line says by "
        "how much), from the first row to the end,"
    )
    assert "player's default rate" in out["notes"][0] and "faster than" not in out["notes"][0]
    for note in out["notes"]:
        assert note.endswith(", never into a results tree, and never over an existing file.")
    assert out["progress"] == [
        "Saving frame 0 of 1800; elapsed 0 s.",
        "Saving frame 12 of 1800; elapsed 1 s, 85 ms per frame.",
        "Saving frame 1800 of 1800; elapsed 2 min 30 s, 83 ms per frame.",
    ]


@pytest.mark.skipif(NODE is None, reason="node not installed: the capture loop is not run")
def test_capture_loop_refuses_an_oversized_frame_under_node(template: str, tmp_path: Path) -> None:
    """Fix round 2 (security pass 2): captureLoop, run under node with a stub hook and a
    recording api: a captured frame of max_frame_bytes + 1 rejects the loop with the frame-cap
    text (capture=true, so Save stays off for the size) and posts nothing; frames at the cap
    are posted in order and the loop ends 'done'."""
    harness = (
        HARNESS_HEAD + _function_source(_script(template), "captureLoop") + CAPTURE_LOOP_HARNESS
    )
    cap = video.MAX_FRAME_BYTES
    out = _run_pure(template, harness, {"cap": cap}, tmp_path)
    assert out["over"] == {
        "error": f"frame 0 is {cap + 1} bytes, over the server's {cap}-byte frame cap: choose a "
        "narrower frame",
        "capture": True,
    }
    assert out["callsAfterOver"] == 0
    assert out["fits"] == {
        "outcome": "done",
        "sent": 3,
        "calls": [f"/api/videos/abc/frames/{k}" for k in range(3)],
    }


RESUME_HARNESS = """
const VIDEO_RETRY_MS = 10;
const VIDEO_FRAME_RETRIES = 3;
const log = [];
let plan = null;
function api(path, opts) {
  if (opts && opts.method === "POST") {
    const k = Number(path.slice(path.lastIndexOf("/") + 1));
    log.push("post " + k);
    if (plan.rejectFrame === k && plan.rejects > 0) {
      plan.rejects -= 1;
      plan.received = plan.took ? k + 1 : k;  // the server took the frame, or did not
      return Promise.reject(new TypeError("Failed to fetch"));
    }
    plan.received = k + 1;
    return Promise.resolve({ ok: true, status: 200, body: { received: k + 1 } });
  }
  log.push("get");
  const video = { state: plan.state, received: plan.received };
  return Promise.resolve({ ok: true, status: 200, body: { video: video } });
}
function sameScene(v) { return true; }
function renderVideoProgress(v) {}
function errorText(res) { return "HTTP " + res.status; }
const hook = { captureFrame: () => Promise.resolve({ size: 100 }) };
const base = { id: "abc", frames: 3, times: [0, 1, 2], width: 1280, height: 720, footer: [],
  sent: 0, cancel: false, maxFrameBytes: 1000, hook: hook };
const out = {};
const run = (name, p) => {
  const defaults = { state: "capturing", received: 0, took: false, rejectFrame: -1, rejects: 0 };
  plan = Object.assign(defaults, p);
  log.length = 0;
  const v = Object.assign({}, base);
  return captureLoop(v).then(
    r => { out[name] = { outcome: r, sent: v.sent, log: log.slice() }; },
    e => { out[name] = { error: e.message, sent: v.sent, log: log.slice() }; });
};
run("lostResponse", { rejectFrame: 1, rejects: 1, took: true })
  .then(() => run("lostRequest", { rejectFrame: 1, rejects: 1, took: false }))
  .then(() => run("fourLosses", { rejectFrame: 1, rejects: 4, took: false }))
  .then(() => run("threeLosses", { rejectFrame: 2, rejects: 3, took: false }))
  .then(() => run("sessionGone", { rejectFrame: 0, rejects: 1, took: false, state: "failed" }))
  .then(() => process.stdout.write(JSON.stringify(out)));
"""


@pytest.mark.skipif(NODE is None, reason="node not installed: the capture loop is not run")
def test_capture_loop_resumes_after_a_lost_frame_post_under_node(
    template: str, tmp_path: Path
) -> None:
    """Fix round 3 (compliance pass 3 finding 5; honesty pass 3): captureLoop with a stub api
    whose POST of one frame rejects with a TypeError (no response). The record then says
    received 2 (the response was lost: the loop goes on at 2 without re-posting 1) or
    received 1 (the request was lost: frame 1 is posted again); both end 'done' with the
    posted indices recorded. Four losses of one frame end with the error naming the frame;
    three are survived (VIDEO_FRAME_RETRIES). A record that is not capturing fails too."""
    harness = (
        HARNESS_HEAD
        + _function_source(_script(template), "retryPause")
        + _function_source(_script(template), "fetchVideo")
        + _function_source(_script(template), "captureLoop")
        + RESUME_HARNESS
    )
    out = _run_pure(template, harness, {}, tmp_path)
    assert out["lostResponse"] == {
        "outcome": "done",
        "sent": 3,
        "log": ["post 0", "post 1", "get", "post 2"],
    }
    assert out["lostRequest"] == {
        "outcome": "done",
        "sent": 3,
        "log": ["post 0", "post 1", "get", "post 1", "post 2"],
    }
    assert out["fourLosses"]["error"] == "the connection was lost while posting frame 1 of 3"
    assert out["fourLosses"]["sent"] == 1
    assert out["fourLosses"]["log"] == ["post 0"] + ["post 1", "get"] * 3 + ["post 1"]
    assert out["threeLosses"] == {
        "outcome": "done",
        "sent": 3,
        "log": ["post 0", "post 1"] + ["post 2", "get"] * 3 + ["post 2"],
    }
    assert out["sessionGone"]["error"] == "the connection was lost while posting frame 0 of 3"
    assert out["sessionGone"]["log"] == ["post 0", "get"]
