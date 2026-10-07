"""Build the launch-assist-sim GitHub Pages site into ``_site/``.

The site is static. This script:

1. copies ``site/`` (the landing page, the slide deck, the examples gallery and the shared
   CSS and JavaScript) into ``_site/``, leaving out this script and the page templates;
2. copies the brand files (``assets/brand/*.svg`` and ``*.png``) to ``_site/assets/brand/``;
3. renders every ``docs/manual/*.md`` to ``_site/manual/<name>.html`` (``README.md`` becomes
   ``index.html``) with one shared template (``site/templates/manual.html``): a chapter
   sidebar, previous and next links, links between chapters rewritten from ``.md`` to
   ``.html``, and links to anything else in the repository pointed at the file on GitHub.
   Images the manual shows are copied to ``_site/manual/files/<repository path>``;
   The replay pages in ``examples/`` (written by ``launchsim replay``, whose template belongs
   to the simulator) get the site's frame added on the way: a favicon, a top bar back to the
   gallery and the home page, the all-rights-reserved notice and the site's contrast tokens
   (``site/templates/replay-frame.html``), plus the template patches in
   ``REPLAY_TEXT_FIXES`` and the editorial additions in ``REPLAY_PAGE_FIXES``; scene pages
   in ``examples/`` (written by ``launchsim scene``) get the same frame in the form their
   Content-Security-Policy allows (the logo as a ``data:`` image, no icon link) and no text
   fix, and the build fails for one written from ``results/app/`` or flagged exploratory
   (D-SP2-37); the files in ``site/examples/`` stay as written. Command code blocks in the
   manual wrap at spaces; console output, the usage synopsis and file trees scroll sideways;
4. writes the "Last updated" stamp (commit date and hash) between the
   ``<!-- stamp -->`` and ``<!-- /stamp -->`` markers of every copied page (the landing page
   must have them) and into every manual page;
5. checks every link in every page it wrote and exits with status 1 if an internal link is
   broken: a missing page, file or anchor on the site, or a missing or git-ignored
   repository path (or a missing heading anchor in a Markdown file) behind a
   ``github.com/khoks/RocketLaunchOptimizationSimulator/blob/main/...`` link.

Python-Markdown is used only by this script, in CI and for local previews. It is
deliberately not a dependency of the launchsim package (it is in neither pyproject.toml nor
uv.lock). From the repository root:

    uvx --with markdown==3.11 python site/build.py
    python -m http.server 8000 --directory _site --bind 127.0.0.1

``--allow-broken-links`` reports broken links without failing, for local previews while the
manual is still being written; CI never passes it.

Copyright (c) 2026 Rahul Singh Khokhar. All rights reserved (see LICENSE).
"""

import argparse
import base64
import html
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as etree
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

try:
    import markdown
    from markdown.extensions import Extension
    from markdown.extensions.toc import TocExtension
    from markdown.treeprocessors import Treeprocessor, UnescapeTreeprocessor
except ImportError:  # pragma: no cover - only without the package
    sys.exit(
        "site/build.py needs Python-Markdown, which is deliberately not a project dependency.\n"
        "Run it as: uvx --with markdown==3.11 python site/build.py"
    )

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_SRC = REPO_ROOT / "site"
BRAND_SRC = REPO_ROOT / "assets" / "brand"
MANUAL_SRC = REPO_ROOT / "docs" / "manual"
MANUAL_TEMPLATE = SITE_SRC / "templates" / "manual.html"
REPLAY_FRAME = SITE_SRC / "templates" / "replay-frame.html"
DEFAULT_OUT = REPO_ROOT / "_site"

GITHUB_REPO = "https://github.com/khoks/RocketLaunchOptimizationSimulator"
GITHUB_BLOB = f"{GITHUB_REPO}/blob/main/"
GITHUB_TREE = f"{GITHUB_REPO}/tree/main/"
GITHUB_PATH_RE = re.compile(rf"^{re.escape(GITHUB_REPO)}/(?P<kind>blob|tree)/main/(?P<path>[^?#]*)")

MARKDOWN_PIN = "3.11"  # keep in step with .github/workflows/pages.yml
SITE_SKIP_TOP = frozenset({"build.py", "templates"})
SITE_SKIP_ANY = frozenset({"__pycache__", ".DS_Store"})
BRAND_SUFFIXES = frozenset({".svg", ".png"})
MANUAL_FILES_DIR = "files"  # images shown by the manual: _site/manual/files/<repo path>
MANUAL_INDEX_SOURCE = "README.md"
NAV_LINE_TEXT = "Manual contents"  # each chapter's own GitHub navigation line starts so
BUILD_MARKER = ".launchsim-site-build"  # marks an output folder this script may replace
STAMP_RE = re.compile(r"(<!-- stamp -->)(.*?)(<!-- /stamp -->)", re.DOTALL)
REPLAY_DIR = "examples"  # replay and scene pages live here, next to the gallery's index.html
REPLAY_MARKER = "Written by launchsim replay"  # in the CSS comment of every replay page
# Scene pages (written by `launchsim scene`, SP2) get the same frame as the replay pages and no
# text fix: their caveats and provenance footer come from the command itself. A scene page
# carries a meta Content-Security-Policy (default-src 'none'; img-src data:; a sha256 pin on its
# one script), which the build leaves as it is: the frame it inserts adds no script and no
# same-origin URL (scene_frame_parts: no icon link, the page keeps its own data: icon, and the
# bar's logo as a data: image), so the framed page loads with no policy violation
# (check_scene_frame). A framed scene page must come from a recorded experiment directory, never
# from an app launch (results/app/, every one exploratory and never public material: design
# D-SP2-37): the build reads the page's data block and refuses a source path under
# APP_RESULTS_PREFIX (with either slash) and a block flagged exploratory (`exploratory` true or
# `label` "exploratory", which an app launch keeps when its directory is copied elsewhere).
SCENE_MARKER = "Written by launchsim scene"  # in the CSS comment of every scene page
SCENE_DATA_RE = re.compile(
    r'<script type="application/json" id="scene-data">(.*?)</script>', re.DOTALL
)
APP_RESULTS_PREFIX = "results/app/"
EXPLORATORY_LABEL = "exploratory"  # the data block's label of an app launch (results_io)
SCENE_FRAME_ICON_RE = re.compile(r'<link rel="icon"[^>]*>\n?')  # the frame's icon link
FRAME_LOGO_SRC = 'src="{{root}}assets/brand/logo-mark.svg"'  # the frame's logo image
SCENE_FRAME_FORBIDDEN = ('src="../', 'href="../assets')  # never in a framed scene page
FRAME_PART_RE = re.compile(r"<!-- (head|top|bottom) -->\n(.*?)<!-- /\1 -->", re.DOTALL)
BODY_OPEN_RE = re.compile(r"<body\b[^>]*>")
EM_COMMA_RE = re.compile(r"<em>([^<]*,[^<]*)</em>")
PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
LIST_ITEM_RE = re.compile(r"^ {0,3}(?:[-*+]|\d{1,9}[.)])[ \t]")
ATX_HEADING_RE = re.compile(r"^ {0,3}#{1,6}[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")
HTML_STASH_RE = re.compile("\x02wzxhzdk:\\d+\x03")
MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)  # fmt: skip
DESCRIPTION_CHARS = 180
CODE_BREAK_MIN = 12  # longer inline code words may wrap after "_", "." or "/"
CODE_PIECE_MIN = 5  # a shorter piece ("1d.", "yaml") stays joined to its neighbour
CMD_PIECE_MAX = 28  # in a command, a path piece longer than this may also wrap after "_", "."
CMD_PREFIXES = ("uv ", "python ", "pip ", "git ", "cd ", ".venv", "ffmpeg ")
CODE_BLOCK_RE = re.compile(
    r'<pre><code(?: class="language-(?P<lang>[\w-]+)")?>(?P<body>.*?)</code></pre>', re.DOTALL
)
TREEPROCESSOR_PRIORITY = 7  # after inline links exist (20), before toc permalinks (5)
# Short hyphenated terms that must not break at the hyphen ("2-" / "D"); the manual wraps them
# in <span class="nb"> (site.css: nowrap), as the landing page, deck and gallery do by hand.
NB_TERM_RE = re.compile(r"((?<![\w-])(?:[1-6]-D(?:OF)?|[Ss]tage-[12]|max-Q|q-alpha)(?![\w-]))")
NB_SKIP_TAGS = frozenset({"code", "pre", "script", "style"})
# Patches for the replay pages, applied while they are copied (the files in site/examples/
# stay as `launchsim replay` wrote them). Since SP2 step A1a (D-SP2-23, KI-029) the pages'
# caveat text is fixed at source in src/launchsim/replay.py (the drive caveat built from the
# runs shown, the structure caveat naming each pushed run's own load, the paired-pad label
# and note, two-decimal offload figures, the subtitle, "leaves"), so no wording pair remains
# here. What remains in REPLAY_TEXT_FIXES is three JavaScript patches of the replay template
# (src/launchsim/templates/replay.html is frozen for SP2, D-SP2-21; its sha256 is pinned by
# tests/test_caveat_wording.py::test_replay_template_is_frozen_for_sp2), a known issue owned
# by a later phase: drop each once the template does it itself and the pages are
# regenerated. REPLAY_STALE_TEXT is the build's tripwire: the sentence the
# drive caveat ended with before A1a ("Each of these favours the assisted runs.", which read,
# next to the payload numbers, as if the massless carriage and the missing shaft drag raised
# the payload); a page that still carries it was written by an older replay and fails the
# build until it is regenerated.
REPLAY_STALE_TEXT = "Each of these favours the assisted runs."
# The gallery index's own tripwire: until A1a its paired-pad entry said the site build
# corrected the page's caveat, label and subtitle; since A1a `replay` words them itself and the
# build only adds editorial sentences, so a gallery text that still claims a build-time
# correction is stale and fails the build.
GALLERY_INDEX = Path(REPLAY_DIR) / "index.html"
GALLERY_STALE_TEXT = "corrected when the site is built"
REPLAY_TEXT_FIXES = (
    # The close-up's "silo floor, 100 m down" label hangs below its dashed line and, with the
    # shaft drawn 1.6 depths deep, overprints the time axis's tick labels. Deepen the panel's
    # lower bound until the line sits at least 16 px above the axis (scaling only).
    (
        "const yr = [deepest > 0 ? -1.6 * deepest : -0.05 * ymax, ymax * 1.05];",
        "const yr = [deepest > 0 ? -Math.max(1.6 * deepest, box.h > 32 ? (deepest * box.h + "
        "16 * ymax * 1.05) / (box.h - 16) : 0) : -0.05 * ymax, ymax * 1.05];",
    ),
    # Labels centred on a point near a canvas edge are cut off there: the last x-axis tick
    # label of a plot ("2,000" shows as "2,00") and the timeline's last event marker ("Orbit"
    # shows as "Orbi"; its canvas keeps only 8 px each side). Keep each label inside its canvas
    # (the tick or marker itself does not move). Drop both once
    # src/launchsim/templates/replay.html clamps them itself and the pages are regenerated.
    (
        "ctx.fillText(fmt(x, xs < 1 ? 1 : 0), px, box.y + box.h + 4);",
        "{ const s = fmt(x, xs < 1 ? 1 : 0), hw = ctx.measureText(s).width / 2; "
        "ctx.fillText(s, Math.max(hw + 1, Math.min(px, ctx.canvas.clientWidth - hw - 1)), "
        "box.y + box.h + 4); }",
    ),
    (
        "if (x - lastX > 60) { ctx.fillText(EVENT_LABEL[e.name] || e.name, x, 0); lastX = x; }",
        "if (x - lastX > 60) { const s = EVENT_LABEL[e.name] || e.name, "
        "hw = ctx.measureText(s).width / 2; ctx.fillText(s, Math.max(hw, Math.min(x, w - hw)), "
        "0); lastX = x; }",
    ),
)
# Editorial additions to one replay page each (file name in site/examples/ -> (old, new)
# pairs), applied after REPLAY_TEXT_FIXES: sentences the gallery adds to a caveat the page
# already states correctly, keyed on the page's own text so a regenerated page that words the
# caveat differently is noticed (the build warns when an entry no longer matches its page and
# its replacement is absent). The page text sits in a JSON block, so the new text is ASCII
# with no double quotes. Numbers: docs/findings/RQ1-fuel-offload-2d.md (run 20261003T112934Z)
# and docs/findings/RQ3-silo-screening-2d.md (run 20260930T175743Z).
# What the source says itself since A1a and is no longer patched here: the offload in the
# drive caveat's invariants, the two-decimal offload figures, the paired-pad label and note
# (its stage named), the subtitle of a page without the baseline, and what a paired pad, a
# pad control and a stage-2 or both-stage solve measure.
# The drive caveat of all five pages says the missing shaft drag biases the drive energy,
# peak power and interface force low; the gallery adds the size of that bias, RQ3-2d's own
# estimate for silo_cold's push (the same 100 m, 3 g, 76.7 m/s push on every silo run of
# these pages), which no page can compute from its runs. Added to the three pages that
# compare a payload or an offload with the pad (pad-vs-silo-cold, pad-vs-silo-offload,
# offload-vs-paired-pad; REPLAY_PAGE_FIXES). Not added to ignition-timing.html (its hot
# starts have smaller drive figures, so their shares differ) nor to failed-ignition.html
# (its runs are cold starts of that push, but the page is about the abort coast and gets
# no editorial addition); the pages' own text carries no percentage (design 4.3).
REPLAY_SHAFT_BIAS_SOURCE = (
    "and the missing shaft drag biases the drive energy, peak power and interface force low."
)
REPLAY_SHAFT_BIAS = (
    REPLAY_SHAFT_BIAS_SOURCE,
    "and the missing shaft drag biases the drive energy, peak power and interface force low (by "
    "about 0.87 MJ, 1.3 MW and 17 kN for this 76.7 m/s exit, 0.04%, 0.08% and 0.08% of "
    "silo_cold's full-stack figures: docs/findings/RQ3-silo-screening-2d.md's own estimate from "
    "q = 3.6 kPa at the exit, C_D 0.46 and a drag growing along the shaft, not a measured value).",
)
# The structure caveat names the pushed run's own load; the gallery adds the size of the
# structure that would cancel the offload (findings note, "Structural penalty rows and
# break-even"), which no run on the page measures.
REPLAY_OFFLOAD_STRUCTURE_SOURCE = (
    "No structural mass is charged for the assist load case: silo_cold_s1 (531.1 t at push "
    "start, 41.26 t less propellant) feels up to 4.0 g during the push."
)
REPLAY_OFFLOAD_STRUCTURE = (
    REPLAY_OFFLOAD_STRUCTURE_SOURCE,
    REPLAY_OFFLOAD_STRUCTURE_SOURCE + " An assumed +8.1 t of stage-1 dry mass leaves 1.98 t of "
    "the offload, and about 8.5 t (extrapolated) leaves nothing; no structural model exists yet "
    "(docs/findings/RQ1-fuel-offload-2d.md, 'Structural penalty rows and break-even').",
)
# The comparison caveat says what the offload run measures; the gallery adds the
# pre-registered reading of the paired pad and, on the headline page, the bridge to the
# README-loads vehicle.
REPLAY_OFFLOAD_CASE_SOURCE = (
    "silo_cold_s1 is a run of the offload block, not compared with pad here: it flies P_ref = "
    "26,054.4 kg and measures propellant saved at the same payload and orbit, not a payload "
    "change (summary.md, 'Propellant saved at fixed payload', with its caveats)."
)
REPLAY_PAIRED_PAD_SOURCE = (
    "silo_cold_s1__pad and silo_cold_s1 are runs of the offload block, not compared with pad "
    "here. silo_cold_s1 flies P_ref = 26,054.4 kg and measures propellant saved at the same "
    "payload and orbit, not a payload change (summary.md, 'Propellant saved at fixed payload', "
    "with its caveats). silo_cold_s1__pad is the paired pad (pad with the same offload and no "
    "push), flies its own payload capacity and measures a payload change (its payload against "
    "P_ref = 26,054.4 kg), not propellant saved."
)
# The subtitle of the paired-pad page says what each run carries to orbit and that the
# baseline is absent (unnamed, design 4.3); the gallery adds what the two runs are (the same
# vehicle, 41.26 t short of a full stage-1 load, flown out of the silo and from the pad with no
# push) and that the absent baseline is the full-load pad, which the page's generic sentence
# cannot know.
REPLAY_PAIRED_SUBTITLE_SOURCE = (
    "compare what each run carries to orbit (the baseline is not on this page)."
)
REPLAY_PAIRED_SUBTITLE = (
    REPLAY_PAIRED_SUBTITLE_SOURCE,
    "compare what each run carries to orbit: the same vehicle, 41.26 t short of a full stage-1 "
    "load, flown out of the silo and from the pad with no push (the full-load baseline, pad, is "
    "not on this page).",
)
REPLAY_PAGE_FIXES: dict[str, tuple[tuple[str, str], ...]] = {
    "pad-vs-silo-cold.html": (REPLAY_SHAFT_BIAS,),
    "pad-vs-silo-offload.html": (
        REPLAY_SHAFT_BIAS,
        REPLAY_OFFLOAD_STRUCTURE,
        # The headline page has no paired pad, so it states the pre-registered reading (most
        # of the offload is the lighter stack's thrust-to-weight) and the bridge in words.
        (
            REPLAY_OFFLOAD_CASE_SOURCE,
            REPLAY_OFFLOAD_CASE_SOURCE + " Read as pre-registered, most of the offload is the "
            "lighter stack's thrust-to-weight: the pad flown with the same 41.26 t offload and "
            "no push falls only 1,402.0 kg short of the full-load pad's 26,054.4 kg, 3.4% of the "
            "offload (the note reports this verdict, and argues that it compares payload "
            "kilograms with propellant kilograms); a delta-v reading chosen after the run gives "
            "the lighter stack 28 to 29% (the paired-pad replay draws both runs). On the "
            "README-loads vehicle, which calibrates inside the band (+8.3%), the same case "
            "removes 36.01 t, 9.10% of its stage-1 load (docs/findings/RQ1-fuel-offload-2d.md, "
            "with its caveats).",
        ),
    ),
    "offload-vs-paired-pad.html": (
        REPLAY_SHAFT_BIAS,
        REPLAY_OFFLOAD_STRUCTURE,
        REPLAY_PAIRED_SUBTITLE,
        (
            REPLAY_PAIRED_PAD_SOURCE,
            REPLAY_PAIRED_PAD_SOURCE + " Its payload capacity, 24,652.4 kg, falls 1,402.0 kg "
            "short of P_ref. Read as pre-registered, that shortfall is small against the offload "
            "(3.4%), so most of the offload is the lighter stack's thrust-to-weight (the note "
            "reports this verdict, and argues that it compares payload kilograms with "
            "propellant kilograms); a delta-v reading chosen after the run gives the lighter "
            "stack 28 to 29% (summary.md, 'Propellant saved at fixed payload'; "
            "docs/findings/RQ1-fuel-offload-2d.md, with its caveats).",
        ),
    ),
}


class BuildError(Exception):
    """A problem that stops the build."""


@dataclass(frozen=True)
class Stamp:
    """The commit the site is built from."""

    full_hash: str
    short_hash: str
    iso_date: str  # committer date, ISO 8601 with offset
    dirty: bool  # the working tree had uncommitted changes

    def as_html(self) -> str:
        """Return the "Last updated" sentence as HTML."""
        year, month, day = (int(x) for x in self.iso_date[:10].split("-"))
        when = f"{day} {MONTHS[month - 1]} {year}"
        url = f"{GITHUB_REPO}/commit/{self.full_hash}"
        commit = f'<a href="{url}"><code>{self.short_hash}</code></a>'
        local = " plus uncommitted local changes" if self.dirty else ""
        when_html = f'<time datetime="{self.iso_date}">{when}</time>'
        return f"Last updated {when_html} from commit {commit}{local}."

    def as_text(self) -> str:
        """Return the stamp as plain text for the console."""
        local = " plus uncommitted local changes" if self.dirty else ""
        return f"{self.iso_date[:10]}, commit {self.short_hash}{local}"


@dataclass
class Chapter:
    """One manual page: its source and what rendering found in it."""

    source: Path
    out_name: str
    title: str = ""
    description: str = ""
    body: str = ""
    sections: list[tuple[str, str]] = field(default_factory=list)  # (id, text) of each h2

    @property
    def label(self) -> str:
        """The source path relative to the repository, for messages and the source link."""
        return self.source.relative_to(REPO_ROOT).as_posix()

    @property
    def nav_label(self) -> str:
        """The chapter's name in the sidebar and the pager."""
        return "Overview and contents" if self.source.name == MANUAL_INDEX_SOURCE else self.title

    @property
    def page_title(self) -> str:
        """The chapter's name in the browser tab."""
        return "Overview" if self.source.name == MANUAL_INDEX_SOURCE else self.title


@dataclass
class BuildLog:
    """Errors, warnings and the files to copy, collected over the build."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    images: dict[Path, str] = field(default_factory=dict)  # repo file -> path under manual/


# ---------------------------------------------------------------------------------------------
# git


def run_git(*args: str, stdin: str | None = None, ok_codes: Iterable[int] = (0,)) -> str:
    """Run git in the repository and return its standard output."""
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), *args],
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except FileNotFoundError as exc:
        raise BuildError("git is not on PATH; the stamp and the link check need it") from exc
    if result.returncode not in tuple(ok_codes):
        raise BuildError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def read_stamp() -> Stamp:
    """Read the date and hash of the checked-out commit, and whether the tree is dirty."""
    full_hash, short_hash, iso_date = run_git("log", "-1", "--format=%H%n%h%n%cI").split("\n")[:3]
    dirty = bool(run_git("status", "--porcelain").strip())
    return Stamp(full_hash, short_hash, iso_date, dirty)


def git_ignored(paths: Iterable[str]) -> set[str]:
    """Return the repository paths that git ignores (they never reach GitHub)."""
    wanted = sorted({p for p in paths if p})
    if not wanted:
        return set()
    # NUL-separated, so neither Windows newline translation nor git's quoting gets in the way.
    stdin = "\0".join(wanted) + "\0"
    out = run_git("check-ignore", "--stdin", "-z", stdin=stdin, ok_codes=(0, 1))
    return {p for p in out.split("\0") if p}


# ---------------------------------------------------------------------------------------------
# anchors


def github_slug(text: str) -> str:
    """Return GitHub's anchor for a heading: lower case, punctuation removed, spaces to '-'."""
    return re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")


def unique_slug(slug: str, used: set[str]) -> str:
    """Return ``slug``, or ``slug-1``, ``slug-2``... as GitHub does for repeated headings."""
    candidate, n = slug, 0
    while candidate in used:
        n += 1
        candidate = f"{slug}-{n}"
    used.add(candidate)
    return candidate


def markdown_heading_text(source: str) -> str:
    """Reduce a Markdown heading to the text GitHub slugs (link targets and tags dropped)."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", source)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def markdown_anchors(path: Path) -> set[str]:
    """Return the heading anchors GitHub generates for a Markdown file, plus explicit ids."""
    used: set[str] = set()
    fence: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = FENCE_RE.match(line)
        if fence is not None:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence):
                fence = None
            continue
        if match:
            fence = match.group(1)
            continue
        heading = ATX_HEADING_RE.match(line)
        if heading:
            unique_slug(github_slug(markdown_heading_text(heading.group(1))), used)
        used.update(re.findall(r'<a\s+(?:id|name)="([^"]+)"', line))
    return used


# ---------------------------------------------------------------------------------------------
# Markdown rendering


def gfm_compat(text: str, label: str, log: BuildLog) -> str:
    """Make GitHub-flavoured list habits render the same way in Python-Markdown.

    GitHub starts a list directly after a paragraph line; Python-Markdown needs a blank line,
    so one is inserted. A nested item indented by fewer than four spaces is flattened by
    Python-Markdown; that is reported as a warning, not changed.
    """
    lines: list[str] = []
    fence: str | None = None
    in_list = False
    prev_blank = True
    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE_RE.match(line)
        if fence is not None:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence):
                fence = None
            lines.append(line)
            continue
        if match:
            fence = match.group(1)
        elif not line.strip():
            prev_blank = True
            lines.append(line)
            continue
        elif LIST_ITEM_RE.match(line):
            if not in_list and not prev_blank:
                lines.append("")
            if in_list and re.match(r"^ {1,3}\S", line):
                log.warnings.append(
                    f"{label}:{number}: nested list item indented by fewer than 4 spaces; "
                    "Python-Markdown flattens it (GitHub nests it)"
                )
            in_list = True
        elif line.startswith("#") or (prev_blank and not line.startswith((" ", "\t"))):
            in_list = False
        prev_blank = False
        lines.append(line)
    return "\n".join(lines) + "\n"


class ManualContext:
    """What every chapter's link rewriting needs: the chapter list and the build log."""

    def __init__(self, chapters: list[Chapter], log: BuildLog) -> None:
        self.out_names = {c.source.name: c.out_name for c in chapters}
        self.log = log

    def rewrite(self, url: str, chapter: Chapter, is_image: bool) -> str:
        """Return the site URL for a link or image source written in a manual chapter.

        Absolute URLs and same-page fragments are kept (the page check validates them).
        Another chapter becomes its ``.html`` page. An image is copied next to the manual.
        Anything else in the repository becomes its github.com blob (file) or tree (folder)
        URL; whether it exists is checked with every other GitHub link after the build.
        """
        parts = urlsplit(url)
        if parts.scheme or parts.netloc or not parts.path:
            return url
        fragment = f"#{parts.fragment}" if parts.fragment else ""
        target = (chapter.source.parent / unquote(parts.path)).resolve()
        try:
            rel = target.relative_to(REPO_ROOT)
        except ValueError:
            self.log.errors.append(f"{chapter.label}: {url!r} points outside the repository")
            return url
        if is_image:
            if not target.is_file():
                self.log.errors.append(f"{chapter.label}: image {url!r} does not exist ({rel})")
                return url
            dest = f"{MANUAL_FILES_DIR}/{rel.as_posix()}"
            self.log.images[target] = dest
            return quote(dest) + fragment
        if target.parent == MANUAL_SRC and target.suffix == ".md":
            name = self.out_names.get(target.name, f"{target.stem}.html")
            return name + fragment
        if rel == Path("."):
            return GITHUB_REPO + fragment
        is_dir = target.is_dir() or parts.path.endswith("/")
        base = GITHUB_TREE if is_dir else GITHUB_BLOB
        return base + quote(rel.as_posix()) + fragment


def join_short_pieces(pieces: list[str]) -> list[str]:
    """Join every piece shorter than ``CODE_PIECE_MIN`` to the next one (the last to the one
    before), so a name never wraps into a lone "1d." or "yaml"."""
    out: list[str] = []
    carry = ""
    for piece in pieces:
        piece = carry + piece
        carry = ""
        if len(piece) < CODE_PIECE_MIN:
            carry = piece
        else:
            out.append(piece)
    if carry:
        if out:
            out[-1] += carry
        else:
            out.append(carry)
    return out


def inline_code_pieces(token: str) -> list[str]:
    """Cut an inline code word into pieces that may wrap between them: after "_", "." or "/"
    in words longer than ``CODE_BREAK_MIN`` (never inside "//")."""
    if len(token) <= CODE_BREAK_MIN:
        return [token]
    return join_short_pieces([p for p in re.split(r"(?<=[_./])(?!/)", token) if p])


def command_pieces(token: str) -> list[str]:
    """Cut one word of a shell command into pieces that may wrap between them, as the
    examples gallery does: after each "/" (never inside "//"), and in a piece still longer
    than ``CMD_PIECE_MAX`` also after "_", "." or "=". Flags have none of these, so a flag
    such as ``--no-sensitivity`` never wraps."""
    if len(token) <= CODE_BREAK_MIN:
        return [token]
    pieces: list[str] = []
    for part in (p for p in re.split(r"(?<=/)(?!/)", token) if p):
        if len(part) > CMD_PIECE_MAX:
            pieces += [p for p in re.split(r"(?<=[_.=])", part) if p]
        else:
            pieces.append(part)
    return join_short_pieces(pieces)


def is_command_block(text: str) -> bool:
    """True if every line of a code block is a shell command (console output, the usage
    synopsis and file trees are not: they keep their layout and scroll sideways)."""
    lines = [line for line in text.splitlines() if line.strip()]
    return bool(lines) and all(line.startswith(CMD_PREFIXES) for line in lines)


def mark_command_blocks(body: str) -> str:
    """Give command code blocks ``class="cmd"`` (they wrap at spaces, see site.css) and wrap
    their words in ``<span class="nw">`` pieces joined by ``<wbr>`` (see
    :func:`command_pieces`). The text is unchanged, so the copy button copies the command."""

    def replace(match: re.Match[str]) -> str:
        text = html.unescape(match.group("body"))
        if not is_command_block(text):
            return match.group(0)
        out: list[str] = []
        for token in re.split(r"(\s+)", text):
            if not token or token.isspace():
                out.append(token)
                continue
            pieces = [
                f'<span class="nw">{html.escape(p, quote=False)}</span>'
                for p in command_pieces(token)
            ]
            out.append("<wbr>".join(pieces))
        lang = match.group("lang")
        attr = f' class="language-{lang}"' if lang else ""
        return f'<pre class="cmd"><code{attr}>{"".join(out)}</code></pre>'

    return CODE_BLOCK_RE.sub(replace, body)


def add_code_breaks(code: etree.Element) -> None:
    """Control where inline code (anything but a code block) may wrap.

    The text is cut into ``<span class="nw">`` pieces that never wrap inside (so a flag
    such as ``--results-root`` is not split at its hyphens), joined by its spaces and, in
    names longer than ``CODE_BREAK_MIN``, by a ``<wbr>`` after each "_", "." or "/" (see
    :func:`inline_code_pieces`). Without this, a long file or key name keeps a table column
    wide and squeezes the prose column of the same table to a few characters on a phone, and
    a long path in a paragraph breaks at an arbitrary letter. Above 600 px, site.css keeps
    the code in a table's first column on one line.
    """
    text = code.text or ""
    if len(code) or not text.strip():
        return
    code.text = None
    last: etree.Element | None = None
    for token in re.split(r"(\s+)", text):
        if not token:
            continue
        if token.isspace():
            if last is None:
                code.text = (code.text or "") + token
            else:
                last.tail = (last.tail or "") + token
            continue
        pieces = inline_code_pieces(token)
        for index, piece in enumerate(pieces):
            if index:
                etree.SubElement(code, "wbr")
            last = etree.SubElement(code, "span", {"class": "nw"})
            last.text = piece


def nb_spans(parts: list[str]) -> list[etree.Element]:
    """Turn ``NB_TERM_RE.split`` output after its first item into nowrap spans with tails."""
    spans: list[etree.Element] = []
    for index in range(1, len(parts), 2):
        span = etree.Element("span", {"class": "nb"})
        span.text, span.tail = parts[index], parts[index + 1]
        spans.append(span)
    return spans


def wrap_hyphenated_terms(root: etree.Element) -> None:
    """Wrap every ``NB_TERM_RE`` term in running text (not in code) in ``<span class="nb">``."""
    inside = {d for e in root.iter() if e.tag in NB_SKIP_TAGS for d in e.iter()}
    for parent in [e for e in root.iter() if e not in inside]:
        children: list[etree.Element] = []
        changed = False
        if parent.text and NB_TERM_RE.search(parent.text):
            parts = NB_TERM_RE.split(parent.text)
            parent.text = parts[0]
            children += nb_spans(parts)
            changed = True
        for child in list(parent):
            children.append(child)
            if child.tail and NB_TERM_RE.search(child.tail):
                parts = NB_TERM_RE.split(child.tail)
                child.tail = parts[0]
                children += nb_spans(parts)
                changed = True
        if changed:
            parent[:] = children


class ManualTreeprocessor(Treeprocessor):
    """Give headings GitHub's ids, rewrite links and images, drop the chapter's nav line."""

    def __init__(self, md: markdown.Markdown, chapter: Chapter, ctx: ManualContext) -> None:
        super().__init__(md)
        self.chapter = chapter
        self.ctx = ctx
        self._unescape = UnescapeTreeprocessor(md).unescape

    def text_of(self, element: etree.Element) -> str:
        """Return an element's visible text with Markdown's placeholders resolved."""
        raw = HTML_STASH_RE.sub("", "".join(element.itertext()))
        return html.unescape(self._unescape(raw))

    def run(self, root: etree.Element) -> None:
        """Process one chapter's element tree in place."""
        used: set[str] = set()
        for element in root.iter():
            if isinstance(element.tag, str) and re.fullmatch(r"h[1-6]", element.tag):
                text = re.sub(r"\s+", " ", self.text_of(element)).strip()
                if "id" not in element.attrib:
                    element.set("id", unique_slug(github_slug(text), used))
                if element.tag == "h1" and not self.chapter.title:
                    self.chapter.title = text
                elif element.tag == "h2":
                    self.chapter.sections.append((element.get("id", ""), text))
        nav_line = self.find_nav_line(root)
        for element in root.iter("a"):
            self.rewrite_attribute(element, "href", is_image=False)
        for element in root.iter("img"):
            self.rewrite_attribute(element, "src", is_image=True)
        if nav_line is not None:
            root.remove(nav_line)
        inline_code = [
            child
            for parent in root.iter()
            if parent.tag != "pre"
            for child in parent
            if child.tag == "code"
        ]
        for code in inline_code:
            add_code_breaks(code)
        wrap_hyphenated_terms(root)
        for element in root:
            if element.tag == "p":
                text = re.sub(r"\s+", " ", self.text_of(element)).strip()
                if len(text) > DESCRIPTION_CHARS:
                    text = text[:DESCRIPTION_CHARS].rsplit(" ", 1)[0] + "…"
                self.chapter.description = text
                break

    def find_nav_line(self, root: etree.Element) -> etree.Element | None:
        """Return the chapter's own "Manual contents · Previous · Next" paragraph, if any.

        The template draws the same navigation, so the paragraph is dropped from the page
        after its links have been checked.
        """
        for element in list(root)[:3]:
            first = element.find("a") if element.tag == "p" else None
            if (
                first is not None
                and not (element.text or "").strip()
                and first.get("href") == MANUAL_INDEX_SOURCE
                and self.text_of(first).strip() == NAV_LINE_TEXT
            ):
                return element
        return None

    def rewrite_attribute(self, element: etree.Element, attribute: str, is_image: bool) -> None:
        """Rewrite one href or src through the manual context."""
        value = element.get(attribute)
        if value is not None:
            url = self._unescape(value).strip()
            element.set(attribute, self.ctx.rewrite(url, self.chapter, is_image))


class ManualExtension(Extension):
    """Register :class:`ManualTreeprocessor` for one chapter."""

    def __init__(self, chapter: Chapter, ctx: ManualContext) -> None:
        super().__init__()
        self.chapter = chapter
        self.ctx = ctx

    def extendMarkdown(self, md: markdown.Markdown) -> None:  # Python-Markdown's API name
        """Add the treeprocessor to ``md``."""
        md.treeprocessors.register(
            ManualTreeprocessor(md, self.chapter, self.ctx),
            "launchsim_manual",
            TREEPROCESSOR_PRIORITY,
        )


def render_chapter(chapter: Chapter, ctx: ManualContext) -> None:
    """Convert one chapter's Markdown to HTML, filling in its title, sections and body."""
    text = gfm_compat(chapter.source.read_text(encoding="utf-8"), chapter.label, ctx.log)
    md = markdown.Markdown(
        extensions=[
            "tables",
            "fenced_code",
            TocExtension(permalink="#", permalink_title="Link to this section"),
            ManualExtension(chapter, ctx),
        ],
        output_format="html",
    )
    chapter.body = mark_command_blocks(md.convert(text))
    for match in EM_COMMA_RE.finditer(chapter.body):
        snippet = re.sub(r"\s+", " ", match.group(1)).strip()[:60]
        ctx.log.warnings.append(
            f"{chapter.label}: italic text with a comma ({snippet!r}); often an unescaped * "
            "that GitHub shows literally (write \\* there)"
        )
    if not chapter.title:
        ctx.log.errors.append(f"{chapter.label}: no level-1 heading to use as the page title")
        chapter.title = chapter.source.stem


def fill_template(template: str, values: dict[str, str], name: str) -> str:
    """Replace every ``{{key}}`` in ``template`` in one pass; unknown keys are an error."""

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise BuildError(f"{name}: no value for placeholder {{{{{key}}}}}")
        return values[key]

    return PLACEHOLDER_RE.sub(replace, template)


def nav_html(chapters: list[Chapter], current: Chapter) -> str:
    """Return the sidebar: every chapter, with the current one's sections under it."""
    items: list[str] = []
    for chapter in chapters:
        here = chapter is current
        attr = ' aria-current="page"' if here else ""
        item = f'<li><a href="{chapter.out_name}"{attr}>{html.escape(chapter.nav_label)}</a>'
        if here and chapter.sections:
            subs = "".join(
                f'<li><a href="#{html.escape(anchor)}">{html.escape(text)}</a></li>'
                for anchor, text in chapter.sections
            )
            item += f"<ol>{subs}</ol>"
        items.append(item + "</li>")
    return "<ol>" + "".join(items) + "</ol>"


def pager_html(chapters: list[Chapter], index: int) -> str:
    """Return the previous and next links for chapter ``index``."""
    links: list[str] = []
    if index > 0:
        prev = chapters[index - 1]
        links.append(
            f'<a class="prev" href="{prev.out_name}"><small>Previous</small>'
            f"{html.escape(prev.nav_label)}</a>"
        )
    if index < len(chapters) - 1:
        nxt = chapters[index + 1]
        links.append(
            f'<a class="next" href="{nxt.out_name}"><small>Next</small>'
            f"{html.escape(nxt.nav_label)}</a>"
        )
    return "\n".join(links)


def discover_chapters() -> list[Chapter]:
    """Return the manual's chapters: README.md first, then the other files by name."""
    if not (MANUAL_SRC / MANUAL_INDEX_SOURCE).is_file():
        raise BuildError(f"docs/manual/{MANUAL_INDEX_SOURCE} is missing (it becomes index.html)")
    sources = sorted(p for p in MANUAL_SRC.glob("*.md") if p.name != MANUAL_INDEX_SOURCE)
    chapters = [Chapter(MANUAL_SRC / MANUAL_INDEX_SOURCE, "index.html")]
    chapters += [Chapter(p, f"{p.stem}.html") for p in sources]
    return chapters


def build_manual(out: Path, stamp: Stamp, log: BuildLog) -> dict[Path, str]:
    """Render the manual into ``out/manual``; return each page's source label."""
    chapters = discover_chapters()
    ctx = ManualContext(chapters, log)
    for chapter in chapters:
        render_chapter(chapter, ctx)
    template = MANUAL_TEMPLATE.read_text(encoding="utf-8")
    manual_out = out / "manual"
    manual_out.mkdir(parents=True, exist_ok=True)
    labels: dict[Path, str] = {}
    for index, chapter in enumerate(chapters):
        page = fill_template(
            template,
            {
                "title": html.escape(chapter.page_title),
                "description": html.escape(chapter.description, quote=True),
                "nav": nav_html(chapters, chapter),
                "content": chapter.body,
                "pager": pager_html(chapters, index),
                "source_url": GITHUB_BLOB + quote(chapter.label),
                "source_path": html.escape(chapter.label),
                "stamp": stamp.as_html(),
            },
            MANUAL_TEMPLATE.name,
        )
        target = manual_out / chapter.out_name
        target.write_text(page, encoding="utf-8", newline="\n")
        labels[target.resolve()] = chapter.label
    for source, dest in log.images.items():
        copy_to = manual_out / dest
        copy_to.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, copy_to)
    return labels


# ---------------------------------------------------------------------------------------------
# copying and stamping


def prepare_out(out: Path) -> None:
    """Empty the output folder, refusing to delete anything this script did not make."""
    if out == REPO_ROOT or REPO_ROOT.is_relative_to(out) or out.is_relative_to(SITE_SRC):
        raise BuildError(f"refusing to build into {out}")
    if out.exists():
        if any(out.iterdir()) and not (out / BUILD_MARKER).exists():
            raise BuildError(f"{out} is not empty and was not made by site/build.py; not deleting")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / BUILD_MARKER).write_text("made by site/build.py\n", encoding="utf-8")


def site_ignore(directory: str, names: list[str]) -> set[str]:
    """``shutil.copytree`` filter: leave out the build script, templates and caches."""
    skip = {n for n in names if n in SITE_SKIP_ANY or n.endswith(".pyc")}
    if Path(directory).resolve() == SITE_SRC:
        skip |= SITE_SKIP_TOP & set(names)
    return skip


def copy_sources(out: Path) -> dict[Path, str]:
    """Copy ``site/`` and the brand files into ``out``; return each page's source label."""
    if (SITE_SRC / "manual").exists():
        raise BuildError("site/manual/ must not exist: the manual is generated from docs/manual/")
    shutil.copytree(SITE_SRC, out, ignore=site_ignore, dirs_exist_ok=True)
    brand_out = out / "assets" / "brand"
    brand_out.mkdir(parents=True, exist_ok=True)
    for path in sorted(BRAND_SRC.iterdir()):
        if path.suffix.lower() in BRAND_SUFFIXES:
            shutil.copy2(path, brand_out / path.name)
    return {
        page.resolve(): f"site/{page.relative_to(out).as_posix()}" for page in out.rglob("*.html")
    }


def read_replay_frame() -> dict[str, str]:
    """Return the head, top and bottom parts of ``site/templates/replay-frame.html``."""
    parts = dict(FRAME_PART_RE.findall(REPLAY_FRAME.read_text(encoding="utf-8")))
    missing = {"head", "top", "bottom"} - parts.keys()
    if missing:
        raise BuildError(f"{REPLAY_FRAME.name}: no {', '.join(sorted(missing))} part")
    return parts


def frame_replay(text: str, parts: dict[str, str], root: str) -> str | None:
    """Return a replay page with the site's frame inserted, or None if it has no body."""
    body = BODY_OPEN_RE.search(text)
    head_end, body_end = text.find("</head>"), text.rfind("</body>")
    if body is None or head_end < 0 or body_end < body.end() or head_end > body.start():
        return None
    fill = {key: value.replace("{{root}}", root) for key, value in parts.items()}
    return (
        text[:head_end]
        + fill["head"]
        + text[head_end : body.end()]
        + "\n"
        + fill["top"]
        + text[body.end() : body_end]
        + fill["bottom"]
        + text[body_end:]
    )


def fix_replay_text(text: str, label: str, log: BuildLog) -> str:
    """Apply ``REPLAY_TEXT_FIXES``, then the page's ``REPLAY_PAGE_FIXES``, to one replay page.
    A page that still carries the stale sentence afterwards (written by a replay from before
    SP2 step A1a) is an error, not a silent pass; a page addition that no longer matches its
    page is a warning."""
    for old, new in REPLAY_TEXT_FIXES:
        text = text.replace(old, new)
    for old, new in REPLAY_PAGE_FIXES.get(Path(label).name, ()):
        if old in text:
            text = text.replace(old, new)
        elif new not in text:
            log.warnings.append(
                f"{label}: a REPLAY_PAGE_FIXES entry no longer matches ({old[:60]!r}...); "
                "drop it if src/launchsim/replay.py now words this itself"
            )
    if REPLAY_STALE_TEXT in text:
        log.errors.append(
            f"{label}: the drive caveat still says {REPLAY_STALE_TEXT!r}, which the gallery "
            "contradicts; add its sentence to REPLAY_TEXT_FIXES in site/build.py, or "
            "regenerate the page once src/launchsim/replay.py is fixed"
        )
    return text


def check_gallery_index(out: Path, log: BuildLog) -> None:
    """Fail the build when the gallery index still claims a correction the site build no
    longer makes (``GALLERY_STALE_TEXT``)."""
    page = out / GALLERY_INDEX
    if page.is_file() and GALLERY_STALE_TEXT in page.read_text(encoding="utf-8"):
        log.errors.append(
            f"site/{GALLERY_INDEX.as_posix()}: still says {GALLERY_STALE_TEXT!r}; since SP2 step "
            "A1a the replay pages word their caveats themselves and the build adds editorial "
            "sentences only (REPLAY_PAGE_FIXES), so reword that entry"
        )


def scene_data(text: str) -> dict | None:
    """A scene page's data block as a dict, or None when the page has no readable one."""
    match = SCENE_DATA_RE.search(text)
    if match is None:
        return None
    try:
        data = json.loads(match.group(1))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def scene_source(text: str) -> str | None:
    """The results directory a scene page was written from (its data block's ``source``, as
    results/<experiment>/<timestamp>), or None when the page has no readable data block."""
    data = scene_data(text)
    source = data.get("source") if data else None
    return source if isinstance(source, str) else None


def check_scene_source(text: str, label: str, log: BuildLog) -> None:
    """Fail the build for a scene page without a readable source, one written from an app
    launch (``APP_RESULTS_PREFIX``, with either slash) or one whose data block is flagged
    exploratory (``exploratory`` true or ``label`` "exploratory": an app launch keeps the flag
    when its directory is copied or moved elsewhere): gallery material comes only from recorded
    experiment directories (D-SP2-37)."""
    data = scene_data(text) or {}
    source = data.get("source")
    if not isinstance(source, str):
        log.errors.append(f"{label}: scene page without a readable data block (no source path)")
        return
    posix = source.replace("\\", "/")
    if posix.startswith(APP_RESULTS_PREFIX) or f"/{APP_RESULTS_PREFIX}" in f"/{posix}":
        log.errors.append(
            f"{label}: written from {source}, an app launch (exploratory, never gallery "
            "material); export the scene from a recorded experiment directory instead"
        )
    if data.get("exploratory") is True or data.get("label") == EXPLORATORY_LABEL:
        log.errors.append(
            f"{label}: written from an exploratory app run (data block exploratory/label); "
            "gallery material comes only from recorded experiment directories (D-SP2-37)"
        )


def scene_frame_parts(parts: dict[str, str]) -> dict[str, str]:
    """The frame parts for a scene page (``read_replay_frame``'s, with two changes): no icon
    link (the page keeps its own data: icon) and the bar's logo as a data: image, which the
    page's policy (img-src data:) allows; nothing else changes. A frame template whose icon link
    or logo image has moved is an error, so a same-origin URL never reaches a scene page."""
    head = SCENE_FRAME_ICON_RE.sub("", parts["head"], count=1)
    logo = base64.b64encode((BRAND_SRC / "logo-mark.svg").read_bytes()).decode("ascii")
    top = parts["top"].replace(FRAME_LOGO_SRC, f'src="data:image/svg+xml;base64,{logo}"', 1)
    if head == parts["head"] or top == parts["top"]:
        raise BuildError(
            f"{REPLAY_FRAME.name}: no icon link in its head part or no {FRAME_LOGO_SRC} in its "
            "top part; scene_frame_parts must replace both for a scene page"
        )
    return {**parts, "head": head, "top": top}


def check_scene_frame(text: str, label: str, log: BuildLog) -> None:
    """Fail the build when a framed scene page carries a same-origin image or icon URL
    (``SCENE_FRAME_FORBIDDEN``), which its policy would block (a broken logo, console errors)."""
    for needle in SCENE_FRAME_FORBIDDEN:
        if needle in text:
            log.errors.append(
                f"{label}: a framed scene page carries {needle!r}, which its "
                "Content-Security-Policy blocks; the frame must use data: images only"
            )


def frame_replays(out: Path, log: BuildLog) -> tuple[int, int]:
    """Add the site's frame to every replay page and every scene page copied into
    ``out/examples``; a replay page also gets the template patches of ``REPLAY_TEXT_FIXES``
    and the editorial additions of ``REPLAY_PAGE_FIXES``; a scene page gets the frame in the
    form its policy allows (``scene_frame_parts``), no text fix, a check of its source directory
    and flags (``check_scene_source``) and of the framed page's URLs (``check_scene_frame``);
    then check the gallery index beside them (``check_gallery_index``). Returns the counts
    (replay pages, scene pages)."""
    parts = read_replay_frame()
    scene_parts = scene_frame_parts(parts)
    replays = scenes = 0
    for page in sorted((out / REPLAY_DIR).glob("*.html")):
        text = page.read_text(encoding="utf-8")
        is_replay, is_scene = REPLAY_MARKER in text, SCENE_MARKER in text
        if not (is_replay or is_scene):
            continue
        label = f"site/{REPLAY_DIR}/{page.name}"
        kind = "replay" if is_replay else "scene"
        root = "../" * len(Path(REPLAY_DIR).parts)
        framed = frame_replay(text, parts if is_replay else scene_parts, root)
        if framed is None:
            log.errors.append(f"{label}: {kind} page without head and body")
            continue
        if is_replay:
            framed = fix_replay_text(framed, label, log)
            replays += 1
        else:
            check_scene_source(framed, label, log)
            check_scene_frame(framed, label, log)
            scenes += 1
        page.write_text(framed, encoding="utf-8", newline="\n")
    check_gallery_index(out, log)
    return replays, scenes


def write_stamps(out: Path, stamp: Stamp, log: BuildLog) -> int:
    """Fill the stamp markers of every copied page; the landing page must have them."""
    count = 0
    for page in sorted(out.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        new, n = STAMP_RE.subn(lambda m: m.group(1) + stamp.as_html() + m.group(3), text)
        if n:
            page.write_text(new, encoding="utf-8", newline="\n")
            count += n
    if not STAMP_RE.search((out / "index.html").read_text(encoding="utf-8")):
        log.errors.append("site/index.html has no <!-- stamp --> ... <!-- /stamp --> marker")
    return count


# ---------------------------------------------------------------------------------------------
# link check


class PageScan(HTMLParser):
    """Collect the ids and the link targets of one HTML page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record ids, anchors and every href, src, poster and srcset URL."""
        for name, value in attrs:
            if value is None:
                continue
            if name == "id" or (name == "name" and tag == "a"):
                self.ids.add(value)
            elif name in ("href", "src", "poster", "xlink:href"):
                self.refs.append(value)
            elif name == "srcset":
                self.refs += [part.split()[0] for part in value.split(",") if part.strip()]


@dataclass
class LinkChecker:
    """Check every link of every page in the output folder."""

    out: Path
    labels: dict[Path, str]
    log: BuildLog
    scans: dict[Path, PageScan] = field(default_factory=dict)
    repo_refs: list[tuple[str, str, str, str]] = field(default_factory=list)  # label, ref, path, #
    broken: dict[tuple[str, str], list[str]] = field(default_factory=dict)  # (ref, why): pages
    checked: int = 0

    def scan(self, page: Path) -> PageScan:
        """Parse a page once and cache the result."""
        if page not in self.scans:
            parser = PageScan()
            parser.feed(page.read_text(encoding="utf-8"))
            parser.close()
            self.scans[page] = parser
        return self.scans[page]

    def run(self) -> None:
        """Check every page, then the GitHub links they contain."""
        pages = sorted(p.resolve() for p in self.out.rglob("*.html"))
        for page in pages:
            label = self.labels.get(page, page.relative_to(self.out).as_posix())
            for ref in self.scan(page).refs:
                self.checked += 1
                self.check(page, label, ref.strip())
        self.check_repo_refs()
        for (ref, why), where in self.broken.items():
            counts = {label: where.count(label) for label in dict.fromkeys(where)}
            shown = [f"{label} (x{n})" if n > 1 else label for label, n in counts.items()]
            if len(shown) > 4:
                shown = [*shown[:4], f"and {len(shown) - 4} more pages"]
            self.log.errors.append(f"{ref!r}: {why}\n      in {', '.join(shown)}")

    def fail(self, label: str, ref: str, why: str) -> None:
        """Record one broken link; repeats of the same link are grouped in the report."""
        self.broken.setdefault((ref, why), []).append(label)

    def check(self, page: Path, label: str, ref: str) -> None:
        """Check one link found on ``page``."""
        parts = urlsplit(ref)
        if parts.scheme in ("http", "https"):
            match = GITHUB_PATH_RE.match(ref)
            if match:
                path = unquote(match.group("path"))
                self.repo_refs.append((label, ref, path, unquote(parts.fragment)))
            return
        if parts.scheme or parts.netloc:
            return  # mailto:, data:, javascript:, protocol-relative URLs
        fragment = unquote(parts.fragment)
        if not parts.path:
            if fragment and fragment not in self.scan(page).ids:
                self.fail(label, ref, "no element on this page has that id")
            return
        target = (page.parent / unquote(parts.path)).resolve()
        if not target.is_relative_to(self.out):
            self.fail(label, ref, "points outside the site")
            return
        if parts.path.endswith("/") or target.is_dir():
            target = target / "index.html"
        where = target.relative_to(self.out).as_posix()
        if not target.is_file():
            self.fail(label, ref, f"{where} is not on the site")
        elif fragment and target.suffix == ".html" and fragment not in self.scan(target).ids:
            self.fail(label, ref, f"no id {fragment!r} in {where}")

    def check_repo_refs(self) -> None:
        """Check the github.com blob and tree links against the checked-out repository."""
        ignored = git_ignored(path.rstrip("/") for _, _, path, _ in self.repo_refs)
        anchors: dict[Path, set[str]] = {}
        for label, ref, path, fragment in self.repo_refs:
            target = (REPO_ROOT / path).resolve()
            if not target.is_relative_to(REPO_ROOT):
                self.fail(label, ref, "points outside the repository")
            elif not target.exists():
                self.fail(label, ref, f"{path} does not exist in the repository")
            elif path.rstrip("/") in ignored:
                self.fail(label, ref, f"{path} is git-ignored, so it is not on GitHub")
            elif fragment and target.is_file() and target.suffix.lower() == ".md":
                if target not in anchors:
                    anchors[target] = markdown_anchors(target)
                if fragment not in anchors[target]:
                    self.fail(label, ref, f"no heading with anchor {fragment!r} in {path}")


# ---------------------------------------------------------------------------------------------
# entry point


def build(out: Path, log: BuildLog) -> tuple[Stamp, int, tuple[int, int], int]:
    """Build the whole site into ``out``; return the stamp and the manual page, framed
    (replay, scene) page and link counts."""
    stamp = read_stamp()
    prepare_out(out)
    labels = copy_sources(out)
    framed = frame_replays(out, log)
    write_stamps(out, stamp, log)
    manual_labels = build_manual(out, stamp, log)
    labels.update(manual_labels)
    checker = LinkChecker(out, labels, log)
    checker.run()
    return stamp, len(manual_labels), framed, checker.checked


def report(lines: list[str], heading: str, emit: Callable[[str], None]) -> None:
    """Print a heading and an indented list, if the list is not empty."""
    if lines:
        emit(heading)
        for line in lines:
            emit(f"  {line}")


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point; returns the process exit status."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Build the launch-assist-sim site into _site/.")
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT, help="output folder (default: _site/)"
    )
    parser.add_argument(
        "--allow-broken-links",
        action="store_true",
        help="local previews only: report broken links but still exit 0 (CI never uses this)",
    )
    args = parser.parse_args(argv)
    out = args.out.resolve()
    log = BuildLog()
    if markdown.__version__ != MARKDOWN_PIN:
        log.warnings.append(
            f"Python-Markdown {markdown.__version__} is installed; CI pins {MARKDOWN_PIN}"
        )
    try:
        stamp, manual_pages, framed, links = build(out, log)
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    def err(line: str) -> None:
        print(line, file=sys.stderr)

    report(log.warnings, f"warnings ({len(log.warnings)}):", err)
    print(f"built {out}")
    print(f"  manual: {manual_pages} pages from docs/manual, {len(log.images)} images copied")
    print(f"  replay: {framed[0]} pages in {REPLAY_DIR}/ framed with the site bar and notice")
    print(
        f"  scene:  {framed[1]} pages in {REPLAY_DIR}/ framed the same way, in the form their "
        "policy allows (no text fix)"
    )
    print(f"  stamp:  {stamp.as_text()}")
    print(f"  links:  {links} checked")
    if log.errors:
        if args.allow_broken_links:
            report(log.errors, f"{len(log.errors)} errors, allowed for a preview:", err)
            return 0
        report(log.errors, f"error: {len(log.errors)} errors (the site is not usable):", err)
        return 1
    print("  no broken links")
    return 0


if __name__ == "__main__":
    sys.exit(main())
