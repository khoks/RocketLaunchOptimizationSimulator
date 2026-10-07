"""site/build.py's handling of scene pages (SP2 step A7, review round 1): the frame a scene page
gets must load under the page's own Content-Security-Policy, and a page from an app launch or
flagged exploratory never reaches the gallery (D-SP2-37). The build script is loaded from its
file (it is not a package); its optional markdown import is not needed here."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

from launchsim import scene

REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / "site" / "build.py"
CSP_RE = re.compile(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)">')


def _markdown_stub() -> dict[str, ModuleType]:
    """Stand-ins for the Python-Markdown modules site/build.py imports at load time (it is
    deliberately not a project dependency and exits without it): the manual build is not run
    here, only the frame and the scene checks, which need none of them."""
    pkg, ext, toc, tree = (
        ModuleType(name)
        for name in (
            "markdown",
            "markdown.extensions",
            "markdown.extensions.toc",
            "markdown.treeprocessors",
        )
    )
    ext.Extension = type("Extension", (), {})
    toc.TocExtension = type("TocExtension", (), {})
    tree.Treeprocessor = type("Treeprocessor", (), {})
    tree.UnescapeTreeprocessor = type("UnescapeTreeprocessor", (), {})
    pkg.Markdown, pkg.__version__ = type("Markdown", (), {}), "stub"
    pkg.extensions, ext.toc, pkg.treeprocessors = ext, toc, tree
    return {m.__name__: m for m in (pkg, ext, toc, tree)}


@pytest.fixture(scope="module")
def build() -> ModuleType:
    stubs = {} if importlib.util.find_spec("markdown") else _markdown_stub()
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location("site_build", BUILD)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name in stubs:
            sys.modules.pop(name, None)
    return module


def _scene_page(data: dict) -> str:
    """The scene template with ``data`` as its data block (what `launchsim scene` writes)."""
    return scene.load_template().replace(scene.SCENE_DATA_TOKEN, json.dumps(data))


RECORDED = {
    "source": "results/silo_offload_2d/20261003T112934Z",
    "exploratory": False,
    "label": None,
}


def test_scene_frame_adds_no_same_origin_url_and_leaves_policy_and_script_alone(
    build: ModuleType,
) -> None:
    """A framed scene page carries the site bar and footer, the logo as a data: image and no
    second icon link; nothing with a same-origin URL that the page's policy (img-src data:)
    would block (the review saw a broken logo and CSP reports); the policy meta and the inline
    script are byte-identical to the page's (the sha256 pin still matches); the replay pages'
    frame keeps its file URLs."""
    page = _scene_page(RECORDED)
    parts = build.read_replay_frame()
    scene_parts = build.scene_frame_parts(parts)
    framed = build.frame_replay(page, scene_parts, "../")
    assert framed is not None
    assert 'class="las-bar"' in framed and 'class="las-foot"' in framed
    assert 'src="data:image/svg+xml;base64,' in framed
    for needle in build.SCENE_FRAME_FORBIDDEN:
        assert needle not in framed, needle
    assert framed.count('<link rel="icon"') == 1  # the page's own data: icon
    assert CSP_RE.findall(framed) == CSP_RE.findall(page)
    assert re.findall(r"<script>(.*?)</script>", framed, re.S) == re.findall(
        r"<script>(.*?)</script>", page, re.S
    )
    log = build.BuildLog()
    build.check_scene_frame(framed, "site/examples/x.html", log)
    assert log.errors == []
    # the replay frame itself still names its files; the scene check would refuse it
    plain = build.frame_replay(page, parts, "../")
    assert plain is not None and 'src="../assets/brand/logo-mark.svg"' in plain
    build.check_scene_frame(plain, "site/examples/x.html", log)
    assert len(log.errors) == 2 and all("Content-Security-Policy blocks" in e for e in log.errors)
    # a frame template whose icon link or logo moved is a build error, not a silent pass
    with pytest.raises(build.BuildError):
        build.scene_frame_parts({**parts, "top": parts["top"].replace("logo-mark", "x")})
    with pytest.raises(build.BuildError):
        build.scene_frame_parts({**parts, "head": "<style></style>"})


@pytest.mark.parametrize(
    ("data", "errors"),
    [
        (RECORDED, 0),
        ({**RECORDED, "source": "results/app/20261007T050105Z"}, 1),
        ({**RECORDED, "source": "D:/DEV/x/results/app/20261007T050105Z"}, 1),
        ({**RECORDED, "source": "results\\app\\20261007T050105Z"}, 1),
        ({**RECORDED, "source": "results/demo_copy/20261007T050105Z", "exploratory": True}, 1),
        ({**RECORDED, "source": "results/demo_copy/20261007T050105Z", "label": "exploratory"}, 1),
        ({**RECORDED, "source": "results/app/20261007T050105Z", "exploratory": True}, 2),
        ({"experiment": "x"}, 1),
    ],
)
def test_check_scene_source_refuses_app_launches_and_exploratory_flags(
    build: ModuleType, data: dict, errors: int
) -> None:
    """The gallery refuses a scene page written from results/app/ (either slash, any prefix),
    one whose data block is flagged exploratory although its directory was copied elsewhere,
    and one without a readable source; a recorded directory passes."""
    log = build.BuildLog()
    build.check_scene_source(_scene_page(data), "site/examples/x.html", log)
    assert len(log.errors) == errors, log.errors
    for error in log.errors:
        assert "D-SP2-37" in error or "app launch" in error or "no source path" in error


def test_check_scene_source_without_a_data_block(build: ModuleType) -> None:
    log = build.BuildLog()
    build.check_scene_source("<html><head></head><body></body></html>", "x", log)
    assert log.errors == ["x: scene page without a readable data block (no source path)"]
    assert build.scene_source("<html></html>") is None
    assert build.scene_data(_scene_page(RECORDED)) == RECORDED
