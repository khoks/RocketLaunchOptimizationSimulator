"""The local app server (SP2 step A4b; src/launchsim/app.py and cli.py's ``app`` command;
design docs/phases/inputs/2026-10-05-SP2-design.md section 4.6, decisions D-SP2-09, 11,
22, 29, 32, 36, 37; survey 07 sections 3 to 6; reviews 04, 05 findings 6 and 7, 06
findings 3, 5, 8 and 11). Every server binds 127.0.0.1 on port 0 and lists or launches
into a folder under tmp_path, never results/; every connection is closed in a finally;
a test that starts a job waits for its end.

Fast:

- the raw-socket guard table: survey 07's 38 prototype cases adapted (a decoded '\\\\' is
  now 400) plus Sec-Fetch-Site same-site and cross-site on GET /scene, /api/results and
  /api/job (403) and on GET / (200), path decoding ('+' stays '+', %2B gives '+'; %2F,
  %5C, %00, non-ASCII and %252e%252e refused), query strings, absolute-form and asterisk
  targets, Transfer-Encoding, Content-Length rules, 64 KiB + 1 refused without reading
  and 64 KiB accepted, nested, repeated-key and non-finite JSON refused, a malformed and a
  two-word request line answered with a status line; a kept connection (HTTP/1.1 since
  fix round 3 of A6v) carries two requests, is closed by a refusal, by an HTTP/1.0
  request line and after HANDLER_TIMEOUT_S idle;
- a header table per route (the frame and CSP headers of /, /scene/... and the API, the
  standard library's own errors included; no CORS header; the Server header);
- only 127.0.0.1 is bound, with no option to change it; a second server on the port
  fails;
- the launch route: a dry run never starts a job; a refusal writes nothing; a second
  launch while one runs is 409 busy; a launch after a code change is 409; two
  simultaneous launch POSTs give exactly one 202; the job snapshot through a launch; a
  worker exception marks the job failed and writes FAILED.txt, printing nothing; the
  stop routine writes FAILED.txt for a running job and none for a finished one or one
  that finishes writing; a server block that raises marks the running launch; a real
  launch stopped in its comparison writes no summary.md and prints nothing; an edited
  preset is not reported as that preset;
- the run browser states on synthetic directories (complete, running, failed with its
  line, incomplete, unreadable: a truncated, a too-deep and an oversized metrics.json,
  a 1-D directory, a sweep, a link, names that fail the rules) with the listing at 200;
  a FAILED.txt or summary.md that is a link is unreadable and never followed; a scene of
  a directory cut short after its row was cached is 422, its row built again; classify
  reads the calibration cases, bounds and sensitivity arms; a resolved_config.yaml with
  a YAML alias tree or over its cap is unreadable, never walked or parsed; run_folders
  is linear in the run list;
- the results panel per launch kind on directories derived from one fixed-guidance
  launch (a solved stage-1 case, a stage-2 solve with a failed verification, an imposed
  offload above and below P_ref, a run that did not fly), and the reproduction lines;
  SP1's comparison bounded, and SP1's headline only with SP1's figure (and, in SP1's
  directory, SP1's clean commit) and on SP1's basis files at the directory's own basis
  commit; a run or a comparison that is bug_suspect flagged beside its figure, never
  'not in orbit'; an imposed offload names its penalty; a git record without a hash
  never clean; a yardstick headline;
- the injection test: a directory whose label, caveats, flags and FAILED.txt line carry
  HTML and script text, served as strict JSON with '<' escaped and as a scene page whose
  data block escapes '<';
- the scene route (a selection of 1 to 4 distinct runs of the directory; 409 for the
  running launch's directory and an unplayable one; the LRU);
- the app page (ASCII, the brand copies, its script by sha256, no HTML sink, no input
  another site controls, a launch or scene route only inside a click or keydown
  handler) and GET /api/form (presets, fields, SP1's headline, which matches the
  findings note);
- no ResourceWarning after a server, a stub job and gc;
- the CLI: a busy port is one error line and exit 1; Ctrl+C (KeyboardInterrupt) marks a
  running launch FAILED and exits 0; another exception while serving marks it too and
  is one error line; an interrupt during the start is one line and exit 0; --open opens
  the URL once (faked); missing display files are one error line.

Slow (Windows only): ``python -m launchsim app --port 0`` in a new process group, a
launch of the shipped silo_cold preset, Ctrl+Break: exit 0, exactly eight stdout lines
ending with the stopped line, nothing on stderr, FAILED.txt.
"""

from __future__ import annotations

import base64
import contextlib
import copy
import dataclasses
import gc
import hashlib
import http.client
import importlib.util
import inspect
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import warnings
from collections.abc import Callable, Iterator
from email.message import Message
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from launchsim import app, appform, cli, replay, results_io, run_data, scene


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
FINDINGS_NOTE = REPO / "docs" / "findings" / "RQ1-fuel-offload-2d.md"
LOGO = REPO / "assets" / "brand" / "logo-mark.svg"
FAVICON = REPO / "assets" / "brand" / "favicon.svg"
CLEAN = {"hash": "0123456789ab", "dirty": False, "error": None}
START = app.ServerStart(git=dict(CLEAN), head=None)
_DRIVE_NOTE_RE = re.compile(r'const DRIVE_NOTE = "([^"]*)" \+\s*"([^"]*)";')
_DRIVE_NOTE_FOUND = _DRIVE_NOTE_RE.search(app.load_app_template())
assert _DRIVE_NOTE_FOUND is not None
DRIVE_NOTE = _DRIVE_NOTE_FOUND.group(1) + _DRIVE_NOTE_FOUND.group(2)
"""The app page's line beside a push of the prescribed drive, read from the template (a
change of its wording is caught by the served-panel test)."""
"""A server start without a HEAD hash: code_changed makes no git call (None)."""
POLL_S = 0.02
TIMEOUT_S = 30.0
QUICK_S = 5.0
"""A response that must come at once (the server did not wait for a body) arrives within
this [s]; the handler timeout is 30 s."""
INJECT_IMG = "<img src=x onerror=window.__x=1>"
INJECT_SCRIPT = "</script><script>window.__x=1</script>"
OFFLOAD_CAVEATS = ("first offload caveat, word for word", f"caveat with {INJECT_IMG} in it")
S1_LOAD_KG = 410_900.0
S2_LOAD_KG = 107_500.0
REMOVED_KG = 20_000.0
VERIFY_TOL_KG = 2.6
FAILED_TEXT = (
    "This run raised before its results were complete; the files here are partial.\n\n"
    "Traceback (most recent call last):\n"
    '  File "x.py", line 1, in <module>\n'
    "ValueError: boom\n"
    "    For further information visit https://errors.pydantic.dev/2/v/value_error\n"
)
STOPPED = "launchsim.app.LaunchInterrupted: the app server was stopped"
"""How FAILED.txt's reason starts for a launch the server stopped (the traceback names
the exception with its module)."""
HTML_SINKS = ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "DOMParser")


# ------------------------------------------------------------------ helpers


class StubRunner:
    """A stand-in for run_launch: reports the preflight stage, waits on ``pre`` (set by
    default), makes <results_root>/app/<timestamp> as run_launch does, reports the pad
    stage (the directory with the pad's), waits on ``gate``, reports the writing stage,
    waits on ``writing`` and writes summary.md, and returns a complete outcome. ``fail``:
    raise it after the directory is made. ``abandon``: return without writing once
    released (a stopped launch)."""

    def __init__(self, *, block: bool = False, fail: BaseException | None = None) -> None:
        self.pre = threading.Event()
        self.pre.set()
        self.gate = threading.Event()
        self.writing = threading.Event()
        self.writing.set()
        if not block:
            self.gate.set()
        self.started = threading.Event()
        self.made = threading.Event()
        self.fail = fail
        self.abandon = False
        self.calls = 0
        self.out_dir: Path | None = None

    def __call__(
        self,
        basis: Any,
        form: Any,
        *,
        results_root: Path,
        repo_root: Path,
        cache: Any,
        server_start: Any,
        progress: Callable[[str, dict[str, Any]], None] | None = None,
        plots: bool = False,
    ) -> app.LaunchOutcome:
        assert progress is not None
        self.calls += 1
        progress(app.STAGE_PREFLIGHT, {"elapsed_s": 0.0, "expected_s": None})
        self.started.set()
        self.pre.wait(TIMEOUT_S)
        out = results_io.make_run_dir(Path(results_root), appform.APP_EXPERIMENT_NAME)
        self.out_dir = out
        progress(
            app.STAGE_PAD,
            {"elapsed_s": 0.0, "expected_s": [1.0, 2.0], "cached": False, "out_dir": out},
        )
        self.made.set()
        if self.fail is not None:
            raise self.fail
        self.gate.wait(TIMEOUT_S)
        if self.abandon:
            return app.LaunchOutcome(app.OUTCOME_CRASHED, out, None, "abandoned")
        progress(app.STAGE_WRITING, {"elapsed_s": 0.1, "expected_s": [1.0, 2.0]})
        self.writing.wait(TIMEOUT_S)
        if self.abandon:
            return app.LaunchOutcome(app.OUTCOME_CRASHED, out, None, "abandoned")
        (out / app.SUMMARY_FILE).write_text("# stub\n", encoding="utf-8", newline="\n")
        return app.LaunchOutcome(
            app.OUTCOME_COMPLETE,
            out,
            None,
            "complete: stub",
            ("a note",),
            0.1,
            (1.0, 2.0),
            None,
            ("a reproduction",),
        )


@contextlib.contextmanager
def serving(
    root: Path,
    basis: appform.Basis,
    *,
    runner: Any = None,
    server_start: app.ServerStart = START,
) -> Iterator[app.AppServer]:
    """An AppServer on 127.0.0.1:0 over ``root``, serving in a daemon thread (poll
    POLL_S), closed (and the thread joined) on exit."""
    server = app.AppServer(
        port=0,
        basis=basis,
        server_start=server_start,
        results_root=root,
        repo_root=root.parent,
        display_dir=DISPLAY_DIR,
        runner=runner,
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


def read_response(sock: socket.socket) -> bytes:
    """One HTTP response from ``sock``: read until the server closes, or (a kept
    connection, since fix round 3 of A6v) until the head and its Content-Length of body
    bytes have arrived."""
    chunks: list[bytes] = []
    need: int | None = None
    while True:
        try:
            data = sock.recv(65536)
        except ConnectionResetError:
            break
        if not data:
            break
        chunks.append(data)
        response = b"".join(chunks)
        head, sep, body = response.partition(b"\r\n\r\n")
        if sep and need is None:
            found = re.search(rb"(?im)^content-length:[ \t]*([0-9]+)[ \t]*\r?$", head)
            need = int(found.group(1)) if found else None
        if need is not None and len(body) >= need:
            break
    return b"".join(chunks)


def raw(
    port: int, payload: bytes, timeout: float = TIMEOUT_S
) -> tuple[int, dict[str, list[str]], bytes]:
    """Send ``payload`` to 127.0.0.1:port over a raw socket and read one response
    (``read_response``): (status, headers lower-cased with every value, body). Status 0:
    no status line."""
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as sock:
        sock.sendall(payload)
        response = read_response(sock)
    head, _, body = response.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    match = re.match(r"HTTP/1\.[01] (\d{3})", lines[0]) if lines else None
    headers: dict[str, list[str]] = {}
    for line in lines[1:]:
        name, _, value = line.partition(":")
        headers.setdefault(name.strip().lower(), []).append(value.strip())
    return (int(match.group(1)) if match else 0), headers, body


def call(
    port: int,
    method: str,
    path: str,
    body: Any = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    """One request through http.client (Host 127.0.0.1:port), the connection closed in a
    finally: (status, headers lower-cased, body)."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT_S)
    try:
        sent = dict(headers or {})
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            sent.setdefault("Content-Type", "application/json")
        conn.request(method, path, body=data, headers=sent)
        response = conn.getresponse()
        return response.status, {k.lower(): v for k, v in response.getheaders()}, response.read()
    finally:
        conn.close()


def strict(text: bytes | str) -> Any:
    """JSON that must be strict: NaN and Infinity refused."""

    def refuse(name: str) -> Any:
        raise ValueError(f"non-strict JSON constant {name}")

    return json.loads(text, parse_constant=refuse)


def wait_job(server: app.AppServer, timeout: float = TIMEOUT_S) -> dict[str, Any]:
    """The job snapshot once the job is no longer running."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snap = server.job_snapshot()
        if snap["state"] != app.JOB_RUNNING:
            return snap
        time.sleep(POLL_S)
    raise AssertionError("the job did not end")


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data), encoding="utf-8", newline="\n")


def make_sweep(root: Path, experiment: str, stamp: str) -> Path:
    """A sweep directory: summary.md over baseline/ and sweep_1/run_0000/."""
    out = root / experiment / stamp
    (out / "baseline").mkdir(parents=True)
    (out / "sweep_1" / "run_0000").mkdir(parents=True)
    (out / "summary.md").write_text("# sweep\n", encoding="utf-8")
    return out


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def basis() -> appform.Basis:
    return sup.fixed_basis()


@pytest.fixture(scope="module")
def request_body(basis: appform.Basis) -> dict[str, Any]:
    """The silo_cold preset's form as a request (the fixed basis: neutral names)."""
    return appform.form_to_request(appform.preset_form(basis, "silo_cold"))


@pytest.fixture(scope="module")
def launched(basis: appform.Basis, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One real fixed-guidance launch of the silo_cold preset (run_launch, no plots,
    about a second): an exploratory app directory with the runs pad and silo."""
    root = tmp_path_factory.mktemp("launched")
    with pytest.MonkeyPatch.context() as mp:
        sup.git_states(mp, CLEAN)
        outcome = app.run_launch(
            basis,
            appform.preset_form(basis, "silo_cold"),
            results_root=root,
            repo_root=REPO,
            cache=app.BaselineCache(),
            server_start=START,
        )
    assert outcome.out_dir is not None and (outcome.out_dir / app.SUMMARY_FILE).is_file()
    return outcome.out_dir


def _case(name: str, p_ref: float, **fields: Any) -> dict[str, Any]:
    """An offload case record (the SP1 writer's keys) of a solved stage-1 case removing
    REMOVED_KG, ``fields`` replacing or adding keys."""
    total = S1_LOAD_KG + S2_LOAD_KG
    record = {
        "name": name,
        "of": "silo",
        "kind": "solve",
        "mode": "stage1",
        "fixed_key": None,
        "fixed_fraction": None,
        "run": name,
        "status": "ok",
        "run_status": "inserted",
        "reference_payload_kg": p_ref,
        "quoted_offload_kg": REMOVED_KG,
        "quoted_basis": "x* at P_ref, gross: stage 1, the headline",
        "offload_kg": REMOVED_KG,
        "stage2_preoffload_kg": 0.0,
        "stage1_dry_mass_added_kg": 0.0,
        "assumed_penalty": False,
        "stage1_offload_kg": REMOVED_KG,
        "stage2_offload_kg": 0.0,
        "total_offload_kg": REMOVED_KG,
        "stage1_load_kg": S1_LOAD_KG,
        "stage2_load_kg": S2_LOAD_KG,
        "total_load_kg": total,
        "stage1_fraction": REMOVED_KG / S1_LOAD_KG,
        "stage2_fraction": 0.0,
        "total_fraction": REMOVED_KG / total,
        "payload_kg": p_ref,
        "payload_delta_kg": 0.0,
        "verification": {
            "status": "ok",
            "payload_kg": p_ref + 0.01,
            "delta_kg": 0.01,
            "tolerance_kg": VERIFY_TOL_KG,
            "passed": True,
            "run": name,
        },
        "pad_control_offload_kg": None,
        "net_offload_kg": None,
        "vs_pad": {"max_q_above_pad": True, "max_q_pa": 39_000.0, "pad_max_q_pa": 38_000.0},
        "flags": [],
    }
    record.update(fields)
    return record


def derive(
    src: Path,
    root: Path,
    stamp: str,
    edit: Callable[[dict[str, Any], dict[str, Any], Path], None],
    *,
    experiment: str = appform.APP_EXPERIMENT_NAME,
) -> Path:
    """A copy of the launched directory at <root>/<experiment>/<stamp>, its runs made
    inserted with a payload (fixed guidance searches none), then ``edit``ed (metrics,
    config, the new directory) and written back (the config as results_io writes it:
    YAML, so 1e-10 stays a number)."""
    out = root / experiment / stamp
    shutil.copytree(src, out)
    metrics = run_data.read_json(out / run_data.METRICS_FILE)
    config = run_data.read_yaml(out / run_data.CONFIG_FILE)
    for name, m in metrics["runs"].items():
        m["status"] = "inserted"
        m["payload_kg"] = 26_000.0 if name == "pad" else 27_000.0
    metrics["comparison"]["silo"]["payload_delta_kg"] = 1_000.0
    edit(metrics, config, out)
    write_json(out / run_data.METRICS_FILE, metrics)
    results_io.write_yaml(out / run_data.CONFIG_FILE, config)
    return out


def with_case(
    record: dict[str, Any],
    *,
    flags: list[str] | None = None,
    control_flags: list[str] | None = None,
) -> Callable[..., None]:
    """An ``edit`` adding an offload block with ``record`` as its one case, its run a
    copy of the silo run folder, metrics and config entry, and a stage-2 pad control
    (carrying ``control_flags``)."""

    def edit(metrics: dict[str, Any], config: dict[str, Any], out: Path) -> None:
        name = record["name"]
        shutil.copytree(out / "silo", out / name)
        flown = json.loads(json.dumps(metrics["runs"]["silo"]))
        flown["payload_kg"] = record["payload_kg"]
        flown["flags"] = list(flags or [])
        metrics["offload"] = {
            "basis": "test basis",
            "reference": "pad",
            "reference_payload_kg": record["reference_payload_kg"],
            "caveats": list(OFFLOAD_CAVEATS),
            "pad_control": True,
            "pad_controls": [
                {
                    "mode": "stage2",
                    "run": "pad__offload_stage2",
                    "status": "ok",
                    "offload_kg": 500.0,
                    "flags": list(control_flags or []),
                }
            ],
            "cases": [record],
            "runs": {name: flown},
        }
        config["offload_runs"] = {name: json.loads(json.dumps(config["runs"]["silo"]))}

    return edit


# ------------------------------------------------------------------ the guard (pure)


def _headers(*pairs: tuple[str, str]) -> Message:
    msg = Message()
    for name, value in pairs:
        msg[name] = value
    return msg


def test_split_target_decodes_each_segment_once_after_splitting() -> None:
    """'+' stays '+', %2B gives '+', each segment decoded once (%252e%252e stays
    refused as %2e%2e), and a decoded '/', '\\\\', '%', control or non-ASCII is 400."""
    assert app.split_target("/") == [""]
    assert app.split_target("/api/results/a+b/x") == ["api", "results", "a+b", "x"]
    assert app.split_target("/api/results/a%2Bb/x") == ["api", "results", "a+b", "x"]
    assert app.split_target("/scene/e/t/pad,silo_cold_s1_dry+8.1t") == [
        "scene",
        "e",
        "t",
        "pad,silo_cold_s1_dry+8.1t",
    ]
    assert app.split_target("/a/%2e%2e/b") == ["a", "..", "b"]
    for bad in ("/a%2Fb", "/a%5Cb", "/a%00b", "/%252e%252e", "/caf%C3%A9", "/%FF", "/a%7Fb"):
        with pytest.raises(app.Refused) as caught:
            app.split_target(bad)
        assert caught.value.status == 400, bad


def test_guard_rules_without_a_socket() -> None:
    """Host, Origin, Sec-Fetch-Site (GET / exempt), the target's form and the query."""
    port = 8765
    host = ("Host", f"127.0.0.1:{port}")
    assert app.guard("GET", "/api/job", _headers(host), port) == ["api", "job"]
    assert app.guard("GET", "/", _headers(host, ("Sec-Fetch-Site", "cross-site")), port) == [""]
    cases = [
        ("GET", "/api/job", _headers(("Host", "127.0.0.1:1")), 403),
        ("GET", "/api/job", _headers(host, ("Origin", "null")), 403),
        (
            "GET",
            "/api/job",
            _headers(
                host, ("Origin", f"http://127.0.0.1:{port}"), ("Origin", f"http://127.0.0.1:{port}")
            ),
            403,
        ),
        ("POST", "/", _headers(host, ("Sec-Fetch-Site", "cross-site")), 403),
        ("GET", "/api/job", _headers(host, ("Sec-Fetch-Site", "same-site")), 403),
        ("GET", "http://127.0.0.1/api/job", _headers(host), 400),
        ("GET", "*", _headers(host), 400),
        ("GET", "/api/job?", _headers(host), 400),
        ("GET", "/?x=1", _headers(host), 400),
    ]
    for method, target, headers, status in cases:
        with pytest.raises(app.Refused) as caught:
            app.guard(method, target, headers, port)
        assert caught.value.status == status, (method, target)
    for site in ("same-origin", "none", "Same-Origin"):
        assert app.guard("GET", "/api/job", _headers(host, ("Sec-Fetch-Site", site)), port)


# ------------------------------------------------------------------ the guard over sockets


def test_raw_socket_guard_table(
    tmp_path: Path, basis: appform.Basis, request_body: dict[str, Any]
) -> None:
    """Survey 07's 38 raw-socket cases, adapted (a decoded backslash is now 400), and the
    new ones (review 04 findings 3, 7, 11 and 12): each request gets the expected
    status; the server never starts a job (dry runs only) and writes nothing."""
    root = tmp_path / "root"
    make_sweep(root, "silo_x", "20260101T000000Z")
    make_sweep(root, "exp+1", "20260101T000000Z")
    runner = StubRunner()
    with serving(root, basis, runner=runner) as server:
        port = server.port
        own = f"127.0.0.1:{port}".encode()
        pb = str(port).encode()

        def g(
            path: bytes, extra: bytes = b"", host: bytes | None = own, ver: bytes = b"1.1"
        ) -> bytes:
            line = b"" if host is None else b"Host: " + host + b"\r\n"
            return b"GET " + path + b" HTTP/" + ver + b"\r\n" + line + extra + b"\r\n"

        def p(
            body: bytes, headers: bytes, host: bytes = own, path: bytes = b"/api/launches"
        ) -> bytes:
            start = b"POST " + path + b" HTTP/1.1\r\nHost: " + host + b"\r\n"
            return start + headers + b"\r\n" + body

        def m(method: bytes, extra: bytes = b"") -> bytes:
            return method + b" /api/launches HTTP/1.1\r\nHost: " + own + b"\r\n" + extra + b"\r\n"

        good = json.dumps({**request_body, "dry_run": True}).encode()
        ctj = b"Content-Type: application/json\r\n"

        def n(body: bytes) -> bytes:
            return b"Content-Length: %d\r\n" % len(body)

        def ok(body: bytes = good) -> bytes:
            return ctj + n(body)

        sfs = b"Sec-Fetch-Site: "
        stamp = b"20260101T000000Z"
        sweep = b"/api/results/silo_x/" + stamp
        scene_path = b"/scene/silo_x/" + stamp + b"/pad"
        panel_path = b"/api/panel/silo_x/" + stamp + b"/pad,silo"
        nested = b"[" * 30_000 + b"]" * 30_000
        full = good + b" " * (app.MAX_JSON_BODY_BYTES - len(good))
        huge = json.dumps({**request_body, "stroke_m": 7}).replace(": 7", ": 1e400").encode()
        evil = b"Origin: http://evil.example\r\n"
        preflight = evil + b"Access-Control-Request-Method: POST\r\n"
        cases: list[tuple[str, bytes, int]] = [
            # survey 07 section 3.2, the 38 prototype cases (adapted)
            ("Host 127.0.0.1:port", g(b"/api/job"), 200),
            ("Host localhost:port", g(b"/api/job", host=b"localhost:" + pb), 200),
            ("Host LOCALHOST:port", g(b"/api/job", host=b"LOCALHOST:" + pb), 200),
            ("Host evil.example:port", g(b"/api/job", host=b"evil.example:" + pb), 403),
            ("Host without port", g(b"/api/job", host=b"127.0.0.1"), 403),
            ("Host port.evil", g(b"/api/job", host=own + b".evil.example"), 403),
            ("no Host (HTTP/1.0)", g(b"/api/job", host=None, ver=b"1.0"), 403),
            ("two Host headers", g(b"/api/job", b"Host: evil.example\r\n"), 403),
            ("Origin of another site", g(b"/api/job", evil), 403),
            ("Origin null", g(b"/api/job", b"Origin: null\r\n"), 403),
            ("absolute-form target", g(b"http://evil.example/api/job"), 400),
            ("existing results directory", g(sweep), 200),
            ("traversal ../", g(b"/api/results/../" + stamp), 404),
            ("traversal %2e%2e", g(b"/api/results/%2e%2e/" + stamp), 404),
            ("traversal ..%5c (a backslash)", g(b"/api/results/..%5c..%5cW/" + stamp), 400),
            ("device name CON", g(b"/api/results/CON/" + stamp), 404),
            ("upper-cased experiment", g(b"/api/results/SILO_X/" + stamp), 404),
            ("trailing dot", g(b"/api/results/silo_x./" + stamp), 404),
            ("extra path segment", g(sweep + b"/metrics.json"), 404),
            ("POST, own Origin", p(good, ok() + b"Origin: http://" + own + b"\r\n"), 200),
            ("POST, no Origin", p(good, ok()), 200),
            ("POST, charset=utf-8", p(good, ctj[:-2] + b"; charset=utf-8\r\n" + n(good)), 200),
            ("POST, Origin of another site", p(good, ok() + evil), 403),
            ("POST, Origin other port", p(good, ok() + b"Origin: http://127.0.0.1:1\r\n"), 403),
            ("POST, Sec-Fetch-Site cross-site", p(good, ok() + sfs + b"cross-site\r\n"), 403),
            ("POST, text/plain", p(good, b"Content-Type: text/plain\r\n" + n(good)), 415),
            ("POST, form", p(b"a=1", b"Content-Type: application/x-www-form-urlencoded\r\n"), 415),
            ("POST, no Content-Type", p(good, n(good)), 415),
            ("POST, no Content-Length", p(b"", ctj), 411),
            ("POST, 10 MB announced", p(b"", ctj + b"Content-Length: 10485760\r\n"), 413),
            ("POST, chunked", p(b"0\r\n\r\n", ctj + b"Transfer-Encoding: chunked\r\n"), 400),
            ("POST, invalid JSON", p(b"{not json}", ok(b"{not json}")), 400),
            ("POST, JSON array", p(b"[1, 2, 3]", ok(b"[1, 2, 3]")), 400),
            ("POST, NaN", p(b'{"a": NaN}', ok(b'{"a": NaN}')), 400),
            ("POST to a GET route", p(good, ok(), path=b"/api/job"), 404),
            ("POST, evil Host", p(good, ok(), host=b"evil.example"), 403),
            ("OPTIONS preflight", m(b"OPTIONS", preflight), 501),
            ("PUT", m(b"PUT"), 501),
            # Sec-Fetch-Site on every request but GET / (review 04 finding 3)
            ("GET /scene, same-site", g(scene_path, sfs + b"same-site\r\n"), 403),
            ("GET /scene, cross-site", g(scene_path, sfs + b"cross-site\r\n"), 403),
            ("GET /api/results, same-site", g(b"/api/results", sfs + b"same-site\r\n"), 403),
            ("GET /api/results, cross-site", g(b"/api/results", sfs + b"cross-site\r\n"), 403),
            ("GET /api/job, same-site", g(b"/api/job", sfs + b"same-site\r\n"), 403),
            ("GET /api/job, cross-site", g(b"/api/job", sfs + b"cross-site\r\n"), 403),
            ("GET /api/panel, same-site", g(panel_path, sfs + b"same-site\r\n"), 403),
            ("GET /api/panel, cross-site", g(panel_path, sfs + b"cross-site\r\n"), 403),
            ("GET /api/panel, Origin of another site", g(panel_path, evil), 403),
            ("GET /, cross-site (a link opens the app)", g(b"/", sfs + b"cross-site\r\n"), 200),
            ("GET /api/job, same-origin", g(b"/api/job", sfs + b"same-origin\r\n"), 200),
            ("GET /api/job, none", g(b"/api/job", sfs + b"none\r\n"), 200),
            ("POST, same-site", p(good, ok() + sfs + b"same-site\r\n"), 403),
            ("POST, same-origin", p(good, ok() + sfs + b"same-origin\r\n"), 200),
            # path decoding (review 04 finding 12)
            ("'+' stays '+'", g(b"/api/results/exp+1/" + stamp), 200),
            ("%2B gives '+'", g(b"/api/results/exp%2B1/" + stamp), 200),
            ("%20 is a space, not '+'", g(b"/api/results/exp%201/" + stamp), 404),
            ("%2F", g(b"/api/results/silo_x%2F" + stamp), 400),
            ("%5C", g(b"/api/results/silo_x%5C" + stamp), 400),
            ("%00", g(b"/api/results/silo_x%00/" + stamp), 400),
            ("%252e%252e", g(b"/api/results/%252e%252e/" + stamp), 400),
            ("non-ASCII", g(b"/api/results/caf%C3%A9/" + stamp), 400),
            ("raw non-ASCII byte", g(b"/api/results/caf\xe9/" + stamp), 400),
            # query, target form, routes
            ("query string", g(b"/api/job?x=1"), 400),
            ("empty query", g(b"/api/job?"), 400),
            ("query on /", g(b"/?a"), 400),
            ("asterisk target", g(b"*"), 400),
            ("unknown route", g(b"/api/nothing"), 404),
            ("favicon.ico", g(b"/favicon.ico"), 404),
            ("trailing slash", g(b"/api/job/"), 404),
            ("HEAD", m(b"HEAD"), 501),
            # body rules (review 04 findings 7 and 11)
            ("chunked with a length", p(good, ok() + b"Transfer-Encoding: chunked\r\n"), 400),
            ("two Content-Length", p(good, ok() + n(good)), 400),
            ("Content-Length not digits", p(good, ctj + b"Content-Length: 1e3\r\n"), 400),
            ("two Content-Type", p(good, ctj + ok()), 415),
            ("charset latin-1", p(good, ctj[:-2] + b"; charset=latin-1\r\n" + n(good)), 415),
            ("64 KiB exactly", p(full, ok(full)), 200),
            ("nested JSON", p(nested, ok(nested)), 400),
            ("repeated key", p(b'{"a": 1, "a": 2}', ok(b'{"a": 1, "a": 2}')), 400),
            ("Infinity", p(b'{"a": Infinity}', ok(b'{"a": Infinity}')), 400),
            ("-Infinity", p(b'{"a": -Infinity}', ok(b'{"a": -Infinity}')), 400),
            ("not UTF-8", p(b'{"a": "\xff"}', ok(b'{"a": "\xff"}')), 400),
            ("1e400 in a number field (the form refuses it)", p(huge, ok(huge)), 422),
            # request lines the standard library parses
            ("malformed request line", b"NONSENSE\r\n\r\n", 400),
            ("two-word request line (no Host)", b"GET /api/job\r\n\r\n", 403),
        ]
        wrong = []
        for label, request, want in cases:
            got = raw(port, request)[0]
            if got != want:
                wrong.append(f"{label}: {got} (expected {want})")
        assert not wrong, wrong
        assert len(cases) >= 38 + 20
        assert runner.calls == 0
        assert server.job_snapshot()["state"] == app.JOB_IDLE
    assert sorted(p.name for p in root.iterdir()) == ["exp+1", "silo_x"]


def test_oversized_body_is_refused_without_reading(tmp_path: Path, basis: appform.Basis) -> None:
    """64 KiB + 1 announced and nothing sent: 413 at once (the server waits for no
    byte of the body; its handler timeout is 30 s); a body shorter than its
    Content-Length is 400 once the client stops sending."""
    with serving(tmp_path / "root", basis) as server:
        own = f"127.0.0.1:{server.port}".encode()
        t0 = time.monotonic()
        status, _, body = raw(
            server.port,
            b"POST /api/launches HTTP/1.1\r\nHost: " + own + b"\r\nContent-Type: application/json"
            b"\r\nContent-Length: " + str(app.MAX_JSON_BODY_BYTES + 1).encode() + b"\r\n\r\n",
            timeout=QUICK_S,
        )
        assert status == 413 and time.monotonic() - t0 < QUICK_S
        assert strict(body)["error"] == "body_too_large"
        with socket.create_connection(("127.0.0.1", server.port), timeout=TIMEOUT_S) as sock:
            sock.sendall(
                b"POST /api/launches HTTP/1.1\r\nHost: " + own + b"\r\nContent-Type: "
                b'application/json\r\nContent-Length: 100\r\n\r\n{"a": 1}'
            )
            sock.shutdown(socket.SHUT_WR)
            reply = b""
            while chunk := sock.recv(65536):
                reply += chunk
        assert reply.startswith(b"HTTP/1.1 400 ")  # a refusal closes the connection


# ------------------------------------------------------------------ headers per route


def _single(headers: dict[str, list[str]], name: str) -> str:
    values = headers.get(name.lower(), [])
    assert len(values) == 1, (name, values)
    return values[0]


def test_header_table_per_route(tmp_path: Path, basis: appform.Basis, launched: Path) -> None:
    """Every response carries nosniff, no-store, no-referrer and same-origin resource and
    opener policy, a Server header without the Python version and no CORS header; the
    app page is DENY with its own policy (its script by sha256, connect-src and
    frame-src 'self', frame-ancestors 'none'); a scene page is SAMEORIGIN with the page's
    meta policy plus frame-ancestors 'self' (the meta tag stays); the API, a 404, the
    standard library's 501 and 400 are DENY with default-src 'none' and frame-ancestors
    'none', as JSON with charset."""
    root = tmp_path / "root"
    shutil.copytree(launched, root / "app" / launched.name)
    with serving(root, basis) as server:
        own = f"127.0.0.1:{server.port}".encode()

        def get(path: bytes) -> tuple[int, dict[str, list[str]], bytes]:
            return raw(server.port, b"GET " + path + b" HTTP/1.1\r\nHost: " + own + b"\r\n\r\n")

        page = get(b"/")
        scene_page = get(b"/scene/app/" + launched.name.encode() + b"/pad,silo")
        api = [
            get(b"/api/job"),
            get(b"/api/form"),
            get(b"/api/results"),
            get(b"/api/results/app/" + launched.name.encode()),
            get(b"/api/panel/app/" + launched.name.encode() + b"/pad"),
            get(b"/nothing"),
            raw(server.port, b"PUT / HTTP/1.1\r\nHost: " + own + b"\r\n\r\n"),
            raw(server.port, b"NONSENSE\r\n\r\n"),
        ]
    responses = [page, scene_page, *api]
    assert [r[0] for r in responses] == [200, 200, 200, 200, 200, 200, 200, 404, 501, 400]
    for status, headers, body in responses:
        for name, value in app.FIXED_HEADERS:
            assert _single(headers, name) == value, (status, name)
        assert _single(headers, "Server") == app.SERVER_VERSION
        assert not [h for h in headers if h.startswith("access-control-")]
        assert int(_single(headers, "Content-Length")) == len(body)
        assert "charset=utf-8" in _single(headers, "Content-Type")
    _, headers, body = page
    assert _single(headers, "Content-Type") == app.HTML_CONTENT_TYPE
    assert _single(headers, "X-Frame-Options") == "DENY"
    script = re.findall(r"<script>(.*?)</script>", body.decode("ascii"), re.S)
    assert len(script) == 1
    digest = base64.b64encode(hashlib.sha256(script[0].encode("utf-8")).digest()).decode()
    csp = _single(headers, "Content-Security-Policy")
    assert csp == app.APP_CSP_TEMPLATE.format(script=f"sha256-{digest}")
    for directive in (
        "default-src 'none'",
        "connect-src 'self'",
        "frame-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
        "form-action 'none'",
        "img-src 'self' data:",
        "style-src 'unsafe-inline'",
    ):
        assert directive in csp
    _, headers, body = scene_page
    assert _single(headers, "X-Frame-Options") == "SAMEORIGIN"
    meta = re.findall(
        r'<meta http-equiv="Content-Security-Policy" content="([^"]*)">', body.decode("ascii")
    )
    assert len(meta) == 1
    assert _single(headers, "Content-Security-Policy") == f"{meta[0]}; frame-ancestors 'self'"
    assert "connect-src" not in meta[0]
    for _, headers, body in api:
        assert _single(headers, "Content-Type") == app.JSON_CONTENT_TYPE
        assert _single(headers, "X-Frame-Options") == "DENY"
        assert _single(headers, "Content-Security-Policy") == app.API_CSP
        strict(body)
    for *_, body in api[-3:]:
        assert set(strict(body)) == {"error", "message"}
        assert b"Traceback" not in body and b"PUT" not in body and b"NONSENSE" not in body


# ------------------------------------------------------------------ binding


def test_binds_127_0_0_1_only_and_a_second_server_fails(
    tmp_path: Path, basis: appform.Basis
) -> None:
    """The socket is IPv4 on 127.0.0.1 (no host option in the server or the command);
    a second server on the bound port fails with OSError (exclusive binding)."""
    with serving(tmp_path / "root", basis) as server:
        assert server.socket.family == socket.AF_INET
        assert server.socket.getsockname()[0] == "127.0.0.1"
        assert server.url == f"http://127.0.0.1:{server.port}/"
        params = inspect.signature(app.AppServer).parameters
        assert not {"host", "address", "bind"} & set(params)
        options = {
            opt
            for action in cli.build_parser()._subparsers._group_actions[0].choices["app"]._actions
            for opt in action.option_strings
        }
        assert options == {"-h", "--help", "--port", "--results-root", "--open"}
        with pytest.raises(OSError):
            app.AppServer(
                port=server.port,
                basis=basis,
                server_start=START,
                results_root=tmp_path / "root",
                repo_root=tmp_path,
                display_dir=DISPLAY_DIR,
            )


# ------------------------------------------------------------------ launches


def test_dry_run_never_starts_a_job_and_a_refusal_writes_nothing(
    tmp_path: Path, basis: appform.Basis, request_body: dict[str, Any]
) -> None:
    """A dry run answers 200 with the derived values (or the refusal) and starts
    nothing; a refused form is 422 with its field and one line and writes nothing; a
    number field holding true or a string is refused."""
    root = tmp_path / "root"
    runner = StubRunner()
    with serving(root, basis, runner=runner) as server:
        status, _, body = call(
            server.port, "POST", "/api/launches", {**request_body, "dry_run": True}
        )
        data = strict(body)
        assert status == 200 and data["dry_run"] is True and data["refused"] is None
        assert data["derived"]["push"]["exit_speed_mps"] > 0
        bad = {**request_body, "stroke_m": 1.0e6, "dry_run": True}
        status, _, body = call(server.port, "POST", "/api/launches", bad)
        assert status == 200 and strict(body)["refused"]["field"] == "stroke_m"
        for value in (1.0e6, True, "3"):
            status, _, body = call(
                server.port, "POST", "/api/launches", {**request_body, "stroke_m": value}
            )
            data = strict(body)
            assert status == 422 and data["error"] == "refused" and data["field"] == "stroke_m"
            assert "\n" not in data["message"] and len(data["message"]) <= appform.MAX_REFUSAL_CHARS
        status, _, body = call(server.port, "POST", "/api/launches", {"nope": 1})
        assert status == 422 and "nope" not in strict(body)["message"]
        assert runner.calls == 0
        assert server.job_snapshot()["state"] == app.JOB_IDLE
    assert not root.exists()


def test_launch_job_snapshot_busy_and_code_changed(
    tmp_path: Path,
    basis: appform.Basis,
    request_body: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """202 with the job; while it runs the snapshot says running with its stage, the
    directory and the running row, and a second launch is 409 busy with the running
    job; at the end done with the outcome; after a code change a launch is 409
    code_changed and nothing starts."""
    root = tmp_path / "root"
    runner = StubRunner(block=True)
    with serving(root, basis, runner=runner) as server:
        try:
            status, _, body = call(server.port, "POST", "/api/launches", request_body)
            job = strict(body)["job"]
            assert status == 202 and job["id"] == 1 and job["state"] == app.JOB_RUNNING
            assert job["boot_id"] == server.boot_id and job["expected_s"] is not None
            assert runner.made.wait(TIMEOUT_S)
            snap = strict(call(server.port, "GET", "/api/job")[2])
            assert snap["stage"] == app.STAGE_PAD and snap["pad_cached"] is False
            assert snap["directory"] == {"experiment": "app", "timestamp": runner.out_dir.name}
            status, _, body = call(server.port, "POST", "/api/launches", request_body)
            assert status == 409 and strict(body)["error"] == "busy"
            assert strict(body)["job"]["id"] == 1
            listing = strict(call(server.port, "GET", "/api/results")[2])
            (row,) = listing["groups"][0]["rows"]
            assert row["state"] == app.DIR_RUNNING and row["playable"] is False
            assert listing["running"] == snap["directory"]
            status, _, body = call(server.port, "GET", f"/scene/app/{runner.out_dir.name}/pad")
            assert status == 409 and strict(body)["error"] == "running"
        finally:
            runner.gate.set()
        done = wait_job(server)
        assert done["state"] == app.JOB_DONE and done["stage"] == app.STAGE_WRITING
        assert done["outcome"] == {
            "kind": app.OUTCOME_COMPLETE,
            "message": "complete: stub",
            "notes": ["a note"],
            "reproduces": ["a reproduction"],
            "field": None,
        }
        assert strict(call(server.port, "GET", "/api/job")[2]) == done | {
            "elapsed_s": done["elapsed_s"]
        }
        monkeypatch.setattr(app, "code_changed", lambda *args: True)
        status, _, body = call(server.port, "POST", "/api/launches", request_body)
        assert status == 409 and strict(body)["error"] == "code_changed"
        assert runner.calls == 1


def test_two_simultaneous_launches_give_exactly_one_202(
    tmp_path: Path, basis: appform.Basis, request_body: dict[str, Any]
) -> None:
    """Two launch POSTs released together: one 202, one 409 busy (check-and-start under
    one lock); one directory."""
    root = tmp_path / "root"
    runner = StubRunner(block=True)
    with serving(root, basis, runner=runner) as server:
        barrier = threading.Barrier(2)
        statuses: list[int] = []

        def post() -> None:
            barrier.wait(TIMEOUT_S)
            statuses.append(call(server.port, "POST", "/api/launches", request_body)[0])

        threads = [threading.Thread(target=post) for _ in range(2)]
        try:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(TIMEOUT_S)
        finally:
            runner.gate.set()
        wait_job(server)
    assert sorted(statuses) == [202, 409]
    assert runner.calls == 1
    assert len(list((root / "app").iterdir())) == 1


def test_a_worker_exception_marks_the_job_failed_and_writes_failed_txt(
    tmp_path: Path,
    basis: appform.Basis,
    request_body: dict[str, Any],
    capfd: pytest.CaptureFixture[str],
) -> None:
    """An exception escaping the launch function: the job is failed (crashed, with the
    reason FAILED.txt gives), FAILED.txt is in its directory and the browser shows it
    failed with the same line; nothing is printed (file descriptors 1 and 2 captured: no
    traceback, no warning)."""
    root = tmp_path / "root"
    runner = StubRunner(fail=RuntimeError("worker broke"))
    with serving(root, basis, runner=runner) as server:
        assert call(server.port, "POST", "/api/launches", request_body)[0] == 202
        snap = wait_job(server)
        listing = strict(call(server.port, "GET", "/api/results")[2])
    assert capfd.readouterr() == ("", "")
    assert snap["state"] == app.JOB_FAILED
    assert snap["outcome"]["kind"] == app.OUTCOME_CRASHED
    assert snap["outcome"]["message"] == "RuntimeError: worker broke"
    assert runner.out_dir is not None
    assert app.failed_line(runner.out_dir / results_io.FAILED_MARKER) == (
        "RuntimeError: worker broke"
    )
    (row,) = listing["groups"][0]["rows"]
    assert row["state"] == app.DIR_FAILED and row["line"] == "RuntimeError: worker broke"


def test_stop_marks_a_running_launch_and_leaves_a_finished_one(
    tmp_path: Path, basis: appform.Basis, request_body: dict[str, Any]
) -> None:
    """stop_active_job: a launch still running gets FAILED.txt (LaunchInterrupted with
    its stage) and a failed job, and every later launch is 503 stopping; one that
    finishes writing during the grace wait gets no marker; with no running launch nothing
    is written."""
    form = appform.parse_request(request_body)
    assert isinstance(form, appform.Form)
    root = tmp_path / "root"
    runner = StubRunner(block=True)
    with serving(root, basis, runner=runner) as server:
        assert server.start_launch(form)[0] == 202
        assert runner.made.wait(TIMEOUT_S)
        marked = server.stop_active_job()
        assert marked == runner.out_dir == server.stopped_dir
        line = app.failed_line(marked / results_io.FAILED_MARKER)
        assert line.startswith(f"{STOPPED} while launch 1")
        assert "stage pad" in line
        snap = server.job_snapshot()
        assert snap["state"] == app.JOB_FAILED and snap["outcome"]["kind"] == app.OUTCOME_CRASHED
        assert snap["outcome"]["message"] == line
        status, body = server.start_launch(form)
        assert status == 503 and body["error"] == "stopping" and runner.calls == 1
        runner.abandon = True
        runner.gate.set()
        server._worker.join(TIMEOUT_S)  # the test waits for its job
        assert server.job_snapshot()["state"] == app.JOB_FAILED
        assert server.stop_active_job() is None

    runner = StubRunner()
    runner.writing.clear()
    with serving(tmp_path / "root2", basis, runner=runner) as server:
        assert server.start_launch(form)[0] == 202
        deadline = time.monotonic() + TIMEOUT_S
        while server.job_snapshot()["stage"] != app.STAGE_WRITING:
            assert time.monotonic() < deadline
            time.sleep(POLL_S)
        threading.Timer(0.2, runner.writing.set).start()
        assert server.stop_active_job() is None
        assert server.job_snapshot()["state"] == app.JOB_DONE
    assert runner.out_dir is not None
    assert not (runner.out_dir / results_io.FAILED_MARKER).exists()
    assert (runner.out_dir / app.SUMMARY_FILE).is_file()


def test_a_launch_post_arriving_during_the_stop_starts_nothing(
    tmp_path: Path, basis: appform.Basis, request_body: dict[str, Any]
) -> None:
    """A launch POST whose body is still arriving when the server stops (Ctrl+C:
    stop_active_job, then close): 503 stopping, the runner never called, no directory."""
    root = tmp_path / "root"
    runner = StubRunner()
    body = json.dumps(request_body).encode()
    with serving(root, basis, runner=runner) as server:
        own = f"127.0.0.1:{server.port}".encode()
        head = (
            b"POST /api/launches HTTP/1.1\r\nHost: " + own + b"\r\nContent-Type: "
            b"application/json\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n"
        )
        with socket.create_connection(("127.0.0.1", server.port), timeout=TIMEOUT_S) as sock:
            sock.sendall(head + body[:10])
            time.sleep(0.2)  # the handler is now waiting for the rest of the body
            assert server.stop_active_job() is None
            server.close()
            sock.sendall(body[10:])
            reply = b""
            while chunk := sock.recv(65536):
                reply += chunk
    status_line, _, rest = reply.partition(b"\r\n")
    assert status_line.startswith(b"HTTP/1.1 503 ")  # a stopping server closes the connection
    assert strict(rest.partition(b"\r\n\r\n")[2])["error"] == "stopping"
    assert runner.calls == 0
    assert not (root / appform.APP_EXPERIMENT_NAME).exists()


def test_a_stop_before_the_directory_exists_marks_it_once_made(
    tmp_path: Path, basis: appform.Basis, request_body: dict[str, Any]
) -> None:
    """Ctrl+C in a launch's first moments (still in its preflight, no directory yet):
    stop_active_job marks nothing, and the worker marks the directory it makes after the
    stop with the stop's reason (the job's message agrees)."""
    form = appform.parse_request(request_body)
    assert isinstance(form, appform.Form)
    runner = StubRunner(block=True)
    runner.pre.clear()
    with serving(tmp_path / "root", basis, runner=runner) as server:
        try:
            assert server.start_launch(form)[0] == 202
            assert runner.started.wait(TIMEOUT_S)
            assert server.stop_active_job() is None
            runner.pre.set()
            assert runner.made.wait(TIMEOUT_S)
        finally:
            runner.abandon = True
            runner.pre.set()
            runner.gate.set()
        server._worker.join(TIMEOUT_S)  # the test waits for its job
        snap = server.job_snapshot()
    assert runner.out_dir is not None and server.stopped_dir == runner.out_dir
    line = app.failed_line(runner.out_dir / results_io.FAILED_MARKER)
    assert line.startswith(f"{STOPPED} while launch 1 was running: stage preflight")
    assert snap["state"] == app.JOB_FAILED and snap["outcome"]["message"] == line
    assert not (runner.out_dir / app.SUMMARY_FILE).exists()


def test_a_server_block_that_raises_marks_the_running_launch(
    tmp_path: Path,
    basis: appform.Basis,
    request_body: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ``with server:`` block left by an exception other than Ctrl+C (serve_forever's
    select failing, say) stops the running launch before closing: FAILED.txt with the
    stop's reason, never a directory that reads incomplete."""
    form = appform.parse_request(request_body)
    assert isinstance(form, appform.Form)
    monkeypatch.setattr(app, "WORKER_JOIN_TIMEOUT_S", 0.1)  # the stub job stays blocked
    runner = StubRunner(block=True)
    try:
        with pytest.raises(OSError, match="select failed"):
            with serving(tmp_path / "root", basis, runner=runner) as server:
                assert server.start_launch(form)[0] == 202
                assert runner.made.wait(TIMEOUT_S)
                raise OSError(10038, "select failed")
    finally:
        runner.abandon = True
        runner.gate.set()
    server._worker.join(TIMEOUT_S)  # the test waits for its job
    assert runner.out_dir is not None and server.stopped_dir == runner.out_dir
    line = app.failed_line(runner.out_dir / results_io.FAILED_MARKER)
    assert line.startswith(f"{STOPPED} while launch 1 was running: stage pad")
    assert app.classify(runner.out_dir)[0] == app.OUTCOME_CRASHED


def test_a_stop_in_the_comparison_stage_writes_no_summary(
    tmp_path: Path,
    basis: appform.Basis,
    request_body: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """A real launch (run_launch on the fixed basis) stopped while its comparison runs:
    stop_active_job marks the directory at once (stage comparison); at its next stage
    report (writing) the worker is interrupted (LaunchInterrupted, a BaseException the
    progress wrapper passes), and run_launch writes FAILED.txt with the same reason and
    returns before write_run: no summary.md and no metrics.json beside FAILED.txt, the
    job failed with the marker's line, the worker ended, and nothing was printed (file
    descriptors 1 and 2 captured)."""
    sup.git_states(monkeypatch, CLEAN)
    entered = threading.Event()
    release = threading.Event()
    real = results_io.planar_experiment_result

    def held(*args: Any, **kwargs: Any) -> Any:
        entered.set()
        release.wait(TIMEOUT_S)
        return real(*args, **kwargs)

    monkeypatch.setattr(results_io, "planar_experiment_result", held)
    form = appform.parse_request(request_body)
    assert isinstance(form, appform.Form)
    with serving(tmp_path / "root", basis) as server:
        try:
            assert server.start_launch(form)[0] == 202
            assert entered.wait(TIMEOUT_S)
            assert server.job_snapshot()["stage"] == app.STAGE_COMPARISON
            marked = server.stop_active_job()
        finally:
            release.set()
        server._worker.join(TIMEOUT_S)  # the test waits for its job
        assert not server._worker.is_alive()
        snap = server.job_snapshot()
    assert capfd.readouterr() == ("", "")
    assert marked is not None and server.stopped_dir == marked
    line = app.failed_line(marked / results_io.FAILED_MARKER)
    assert line.startswith(f"{STOPPED} while launch 1 was running: stage comparison")
    assert not (marked / app.SUMMARY_FILE).exists()
    assert not (marked / run_data.METRICS_FILE).exists()
    assert snap["state"] == app.JOB_FAILED and snap["outcome"]["message"] == line


def test_an_edited_preset_is_not_reported_as_the_preset(
    tmp_path: Path, basis: appform.Basis, request_body: dict[str, Any]
) -> None:
    """GET /api/job names the preset a launch is only when its form equals that preset's
    (``same_preset``): the silo_cold request as sent reports preset silo_cold; the same
    request with its net acceleration changed reports preset None, started_from_preset
    silo_cold and preset_edited True; a request naming no preset reports neither. The
    silo_cold_s1 form edited the same way is not that preset either."""
    runner = StubRunner()
    edited = {**request_body, "net_accel_g": 2.5}
    unnamed = {k: v for k, v in request_body.items() if k != "preset"}
    snaps: list[dict[str, Any]] = []
    with serving(tmp_path / "root", basis, runner=runner) as server:
        idle = server.job_snapshot()
        for body in (request_body, edited, unnamed):
            status, _, reply = call(server.port, "POST", "/api/launches", body)
            assert status == 202, reply
            snaps.append(wait_job(server))
    assert (idle["preset"], idle["started_from_preset"], idle["preset_edited"]) == (
        None,
        None,
        False,
    )
    assert [(s["preset"], s["started_from_preset"], s["preset_edited"]) for s in snaps] == [
        ("silo_cold", "silo_cold", False),
        (None, "silo_cold", True),
        (None, None, False),
    ]
    s1 = appform.preset_form(basis, "silo_cold_s1")
    assert app.same_preset(basis, s1)
    assert app.same_preset(basis, dataclasses.replace(s1, dry_run=True))
    assert not app.same_preset(basis, dataclasses.replace(s1, net_accel_g=2.5))
    assert not app.same_preset(basis, dataclasses.replace(s1, preset="no_such_preset"))


def test_a_failure_while_marking_a_crash_still_ends_the_job(
    tmp_path: Path,
    basis: appform.Basis,
    request_body: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A launch that raises, and reading its FAILED.txt raises too (a locked file): the
    job still ends failed with the exception's line, a second launch is 202, and no
    exception reaches threading.excepthook (pytest's filterwarnings=error would fail)."""

    def locked(marker: Path) -> str:
        raise PermissionError("locked")

    monkeypatch.setattr(app, "failed_line", locked)
    runner = StubRunner(fail=RuntimeError("worker broke"))
    with serving(tmp_path / "root", basis, runner=runner) as server:
        assert call(server.port, "POST", "/api/launches", request_body)[0] == 202
        snap = wait_job(server)
        assert snap["state"] == app.JOB_FAILED
        assert snap["outcome"]["message"] == "RuntimeError: worker broke"
        runner.fail = None
        assert call(server.port, "POST", "/api/launches", request_body)[0] == 202
        assert wait_job(server)["state"] == app.JOB_DONE
    assert runner.calls == 2


def test_a_client_that_drips_its_request_is_cut_off_at_the_deadline(
    tmp_path: Path, basis: appform.Basis, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HANDLER_TIMEOUT_S bounds the whole request, not each byte: a client sending one
    byte every 0.5 s sees its connection closed within about the deadline (2 s here) and
    never a 200."""
    monkeypatch.setattr(app, "HANDLER_TIMEOUT_S", 2.0)
    with serving(tmp_path / "root", basis) as server:
        request = b"GET /api/job HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n\r\n" % server.port
        t0 = time.monotonic()
        reply = b""
        closed = False
        with socket.create_connection(("127.0.0.1", server.port), timeout=TIMEOUT_S) as sock:
            sock.settimeout(0.5)
            for byte in request:
                try:
                    sock.sendall(bytes([byte]))
                    chunk = sock.recv(65536)
                except TimeoutError:
                    continue  # nothing yet: drip the next byte
                except OSError:
                    closed = True
                    break
                if not chunk:
                    closed = True
                    break
                reply += chunk
        elapsed = time.monotonic() - t0
    assert closed and elapsed < 3.5, elapsed
    assert not reply.startswith((b"HTTP/1.0 200", b"HTTP/1.1 200"))


def test_a_kept_connection_carries_requests_and_idles_out_at_the_deadline(
    tmp_path: Path, basis: appform.Basis, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fix round 3 of A6v (HTTP/1.1): two GETs on one connection are both answered 200
    without a close between them; a refusal (403) closes the connection with its response;
    an HTTP/1.0 request line closes it; an idle kept connection is closed after
    HANDLER_TIMEOUT_S (2 s here), armed anew for each request."""
    monkeypatch.setattr(app, "HANDLER_TIMEOUT_S", 2.0)
    with serving(tmp_path / "root", basis) as server:
        own = b"127.0.0.1:%d" % server.port
        get = b"GET /api/job HTTP/1.1\r\nHost: " + own + b"\r\n\r\n"
        with socket.create_connection(("127.0.0.1", server.port), timeout=TIMEOUT_S) as sock:
            sock.sendall(get)
            first = read_response(sock)
            time.sleep(1.2)  # within the deadline: the connection is still kept
            sock.sendall(get)
            second = read_response(sock)
            t0 = time.monotonic()
            closed = sock.recv(65536) == b""  # idle: closed at the deadline, nothing sent
            idle = time.monotonic() - t0
        assert first.startswith(b"HTTP/1.1 200 ") and second.startswith(b"HTTP/1.1 200 ")
        assert closed and 1.0 < idle < 3.5, idle
        with socket.create_connection(("127.0.0.1", server.port), timeout=TIMEOUT_S) as sock:
            sock.sendall(b"GET /api/job HTTP/1.1\r\nHost: evil.example:1\r\n\r\n")
            reply = read_response(sock)
            assert reply.startswith(b"HTTP/1.1 403 ")
            assert sock.recv(65536) == b""  # a refusal closes the connection
        with socket.create_connection(("127.0.0.1", server.port), timeout=TIMEOUT_S) as sock:
            sock.sendall(b"GET /api/job HTTP/1.0\r\nHost: " + own + b"\r\n\r\n")
            reply = read_response(sock)
            assert reply.startswith(b"HTTP/1.1 200 ")
            assert sock.recv(65536) == b""  # an HTTP/1.0 request line: one request


# ------------------------------------------------------------------ the run browser


def _junction(target: Path, link: Path) -> bool:
    """A junction (Windows) or a symbolic link elsewhere; False when neither can be made."""
    try:
        if sys.platform == "win32":
            import _winapi

            _winapi.CreateJunction(str(target), str(link))
        else:
            os.symlink(target, link, target_is_directory=True)
    except OSError:
        return False
    return True


def test_run_browser_states_on_synthetic_directories(
    tmp_path: Path, basis: appform.Basis, launched: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Complete (playable), failed with its line (not the pydantic URL line), incomplete,
    unreadable (truncated, a 5000-digit number, too deep, over its cap: fixed text naming
    the file only, never the local path), a 1-D directory, a model that is neither (its
    reason from the fixed set, never its text), a sweep (its git state from its
    baseline), no planar runs; names that fail the rules (fullwidth digits included) and
    a link are not listed but counted; the listing stays 200, newest first in two groups;
    nothing is written."""
    root = tmp_path / "root"
    app_dir = root / "app" / "20260102T000000Z"
    shutil.copytree(launched, app_dir)
    rec = root / "recorded"
    failed = rec / "20260101T000001Z"
    failed.mkdir(parents=True)
    (failed / results_io.FAILED_MARKER).write_text(FAILED_TEXT, encoding="utf-8")
    (rec / "20260101T000002Z").mkdir()
    for stamp, text in (
        ("20260101T000003Z", '{"runs": {"pad": '),
        ("20260101T000004Z", "[" * 30_000 + "]" * 30_000),
        ("20260101T000009Z", "{}"),
        ("20260101T000011Z", '{"runs": {}, "x": ' + "9" * 5_000 + "}"),
    ):
        (rec / stamp).mkdir()
        (rec / stamp / "summary.md").write_text("# x\n", encoding="utf-8")
        (rec / stamp / "metrics.json").write_text(text, encoding="utf-8")
    one_d = root / "one_d" / "20260101T000005Z"
    (one_d / "pad").mkdir(parents=True)
    (one_d / "pad" / "timeseries.csv").write_text("t_s\n0\n", encoding="utf-8")
    (one_d / "summary.md").write_text("# 1-D\n", encoding="utf-8")
    write_json(
        one_d / "metrics.json", {"experiment": "one_d", "baseline": "pad", "runs": {"pad": {}}}
    )
    odd = root / "odd" / "20260101T000012Z"
    odd.mkdir(parents=True)
    (odd / "summary.md").write_text("# x\n", encoding="utf-8")
    write_json(odd / "metrics.json", {"model": "<x>", "baseline": "pad", "runs": {"pad": {}}})
    sweep = make_sweep(root, "sweeps", "20260101T000006Z")
    write_json(
        sweep / "baseline" / "metrics.json",
        {"git": {"hash": "b3150c1754ee", "dirty": False, "error": None}},
    )
    fullwidth = "".join(chr(0xFF10 + int(d)) for d in "20260101")  # U+FF12 U+FF10 ...
    (rec / f"{fullwidth}T000000Z").mkdir()
    empty = root / "flat" / "20260101T000010Z"
    (empty / "pad").mkdir(parents=True)
    (empty / "pad" / "timeseries.csv").write_text("t_s,alt_m\n", encoding="utf-8")
    (empty / "summary.md").write_text("# x\n", encoding="utf-8")
    write_json(
        empty / "metrics.json",
        {"experiment": "flat", "model": "planar_2d", "baseline": "pad", "runs": {"pad": {}}},
    )
    hostile = "x' onmouseover='1"
    (root / hostile / "20260101T000007Z").mkdir(parents=True)
    (rec / hostile).mkdir()
    (rec / "notes.txt").write_text("x", encoding="utf-8")
    linked = _junction(app_dir, root / "linked")
    cap = max(p.stat().st_size for p in root.rglob("metrics.json")) + 1
    big = rec / "20260101T000009Z" / "metrics.json"
    write_json(big, {"runs": {}, "pad": "x" * cap})
    monkeypatch.setattr(app, "MAX_METRICS_BYTES", cap)  # only 20260101T000009Z is over it
    before = sorted(p.as_posix() for p in root.rglob("*"))
    with serving(root, basis) as server:
        status, _, body = call(server.port, "GET", "/api/results")
        listing = strict(body)
        status_hostile = call(
            server.port, "GET", "/api/results/x%27%20onmouseover%3D%271/20260101T000007Z"
        )[0]
        details = [
            call(server.port, "GET", f"/api/results/recorded/{stamp}")[2]
            for stamp in ("20260101T000003Z", "20260101T000011Z")
        ]
        odd_status, _, odd_body = call(server.port, "GET", "/scene/odd/20260101T000012Z/pad")
    assert status == 200 and status_hostile == 404
    groups = {g["name"]: g for g in listing["groups"]}
    assert [g["name"] for g in listing["groups"]] == [app.GROUP_APP, app.GROUP_RECORDED]
    rows = {(r["experiment"], r["timestamp"]): r for g in listing["groups"] for r in g["rows"]}
    (app_row,) = groups[app.GROUP_APP]["rows"]
    assert app_row["state"] == app.DIR_COMPLETE and app_row["playable"] is True
    assert app_row["label"] == replay.EXPLORATORY_LABEL and app_row["run_count"] == 2
    assert app_row["git"] == {"hash": "0123456789ab", "state": "clean"}
    assert app_row["server_start"] == {"hash": "0123456789ab", "state": "clean"}
    assert app_row["description"].startswith("silo: vertical silo 100 m deep")
    assert app_row["size_bytes"] > 0
    kind, message, _ = app.classify(app_dir)
    assert app_row["outcome"] == {"kind": kind, "message": message}
    expect = {
        ("recorded", "20260101T000001Z"): (app.DIR_FAILED, app.REASON_FAILED),
        ("recorded", "20260101T000002Z"): (app.DIR_INCOMPLETE, app.REASON_INCOMPLETE),
        ("recorded", "20260101T000003Z"): (app.DIR_UNREADABLE, app.REASON_UNREADABLE),
        ("recorded", "20260101T000004Z"): (app.DIR_UNREADABLE, app.REASON_UNREADABLE),
        ("recorded", "20260101T000009Z"): (app.DIR_UNREADABLE, app.REASON_UNREADABLE),
        ("recorded", "20260101T000011Z"): (app.DIR_UNREADABLE, app.REASON_UNREADABLE),
        ("one_d", "20260101T000005Z"): (app.DIR_COMPLETE, app.REASON_1D),
        ("odd", "20260101T000012Z"): (app.DIR_COMPLETE, app.REASON_NOT_PLANAR),
        ("sweeps", "20260101T000006Z"): (app.DIR_COMPLETE, app.REASON_SWEEP),
        ("flat", "20260101T000010Z"): (app.DIR_COMPLETE, app.REASON_NO_PLANAR_RUNS),
    }
    for key, (state, reason) in expect.items():
        assert (rows[key]["state"], rows[key]["reason"], rows[key]["playable"]) == (
            state,
            reason,
            False,
        ), key
    assert {r["reason"] for r in rows.values()} <= {None, *app.REASONS}
    assert rows[("recorded", "20260101T000001Z")]["line"] == "ValueError: boom"
    assert rows[("sweeps", "20260101T000006Z")]["run_count"] == 1
    assert rows[("sweeps", "20260101T000006Z")]["git"] == {"hash": "b3150c1754ee", "state": "clean"}
    assert rows[("recorded", "20260101T000009Z")]["line"] == (
        f"metrics.json is over its size cap ({cap:,} bytes)"
    )
    unparsed = "metrics.json cannot be parsed (cut short, not JSON or a number too large)"
    assert rows[("recorded", "20260101T000003Z")]["line"] == unparsed
    assert rows[("recorded", "20260101T000011Z")]["line"] == unparsed
    assert rows[("recorded", "20260101T000004Z")]["line"] == "metrics.json is nested too deeply"
    for text in (body, *details):
        assert str(tmp_path).encode() not in text
        assert str(tmp_path).replace("\\", "\\\\").encode() not in text
    assert odd_status == 409 and strict(odd_body)["reason"] == app.REASON_NOT_PLANAR
    assert "<x" not in json.dumps(strict(odd_body)) and rows[("odd", "20260101T000012Z")]["model"]
    recorded = [r["timestamp"] for r in groups[app.GROUP_RECORDED]["rows"]]
    assert recorded == sorted(recorded, reverse=True)
    assert not any(hostile in r["experiment"] or hostile in r["timestamp"] for r in rows.values())
    assert not any(not r["timestamp"].isascii() for r in rows.values())
    # the hostile experiment, the hostile timestamp, the fullwidth one, notes.txt, the link
    assert listing["not_listed"] == 4 + int(linked)
    assert sorted(p.as_posix() for p in root.rglob("*")) == before


def test_a_linked_failed_txt_or_summary_is_unreadable(
    tmp_path: Path, basis: appform.Basis, launched: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A FAILED.txt or a summary.md that is a link is never followed (design 4.6): the
    row is unreadable with fixed text, and the last line of the file it points to is in
    no response (classify and failed_line would read through the link). A real symbolic
    link when this machine can make one; else (Windows without Developer Mode cannot link
    a file) a copy of the file that ``is_link`` reports as a link."""
    outside = tmp_path / "outside.txt"
    outside.write_text("first\nOUTSIDE-LINE-123\n", encoding="utf-8")
    root = tmp_path / "root"
    failed = root / "rec" / "20260101T000010Z"
    summary = root / "rec" / "20260101T000011Z"
    for run_dir in (failed, summary):
        shutil.copytree(launched, run_dir)
    (summary / app.SUMMARY_FILE).unlink()
    links = (failed / results_io.FAILED_MARKER, summary / app.SUMMARY_FILE)
    try:
        for link in links:
            os.symlink(outside, link)
    except OSError:
        for link in links:
            if link.is_symlink():
                link.unlink()
            shutil.copyfile(outside, link)
        real = app.is_link
        monkeypatch.setattr(app, "is_link", lambda path: Path(path) in links or real(path))
    with serving(root, basis) as server:
        bodies = [call(server.port, "GET", "/api/results")[2]]
        bodies += [
            call(server.port, "GET", f"/api/results/rec/{d.name}")[2] for d in (failed, summary)
        ]
        scene_status = call(server.port, "GET", f"/scene/rec/{failed.name}/pad")[0]
    for body in bodies:
        assert b"OUTSIDE-LINE-123" not in body
    rows = {r["timestamp"]: r for g in strict(bodies[0])["groups"] for r in g["rows"]}
    assert rows[failed.name]["state"] == app.DIR_UNREADABLE
    assert rows[failed.name]["line"] == "FAILED.txt is a link"
    assert rows[summary.name]["state"] == app.DIR_UNREADABLE
    assert rows[summary.name]["line"] == "summary.md is a link"
    assert rows[failed.name]["outcome"] is None and scene_status == 409


def test_a_scene_of_a_directory_cut_short_after_its_row_was_cached(
    tmp_path: Path, basis: appform.Basis, launched: Path
) -> None:
    """A directory listed (and cached) complete whose metrics.json is cut short later:
    its scene is 422 no_scene with the fixed text naming the file, never a 500 (no
    handler error recorded), and the next listing builds its row again: unreadable."""
    root = tmp_path / "root"
    run_dir = root / "rec" / "20260101T000010Z"
    shutil.copytree(launched, run_dir)
    unparsed = "metrics.json cannot be parsed (cut short, not JSON or a number too large)"
    with serving(root, basis) as server:
        (before,) = strict(call(server.port, "GET", "/api/results")[2])["groups"][1]["rows"]
        (run_dir / run_data.METRICS_FILE).write_text('{"runs": {"pad": ', encoding="utf-8")
        status, _, body = call(server.port, "GET", f"/scene/rec/{run_dir.name}/silo")
        (after,) = strict(call(server.port, "GET", "/api/results")[2])["groups"][1]["rows"]
        last_error = server.last_error
    assert before["state"] == app.DIR_COMPLETE and before["playable"] is True
    refusal = strict(body)
    assert status == 422 and refusal == {"error": "no_scene", "message": unparsed}
    assert last_error is None
    assert after["state"] == app.DIR_UNREADABLE and after["line"] == unparsed


def _classified(tmp_path: Path, name: str, **extra: Any) -> tuple[str, str, tuple[str, ...]]:
    """classify of a complete directory whose metrics.json holds an inserted pad and
    ``extra`` beside it."""
    out = tmp_path / name
    out.mkdir()
    (out / app.SUMMARY_FILE).write_text("# x\n", encoding="utf-8")
    pad = {"status": app.INSERTED_STATUS, "flags": []}
    write_json(out / run_data.METRICS_FILE, {"baseline": "pad", "runs": {"pad": pad}, **extra})
    return app.classify(out)


def test_classify_reads_cases_bounds_and_sensitivity_arms(tmp_path: Path) -> None:
    """The complete message's 'no flag, failed verification or bug_suspect check' covers
    every run metrics.json records: a calibration case that is bug_suspect or flagged, a
    bound or its paired baseline short of orbit, a bound's comparison that is bug_suspect,
    a sensitivity arm that did not fly or is flagged, each name the run with its kind;
    with none of them the directory is complete."""
    inserted = {"status": app.INSERTED_STATUS, "flags": []}
    plain = _classified(tmp_path, "plain", cases={"alt_185": inserted}, bounds=[], sensitivity=[])
    assert plain[0] == app.OUTCOME_COMPLETE
    kind, message, notes = _classified(
        tmp_path,
        "case",
        cases={"readme_loads": {"status": app.BUG_SUSPECT, "flags": ["bug_suspect: budget"]}},
    )
    assert (kind, message) == (app.OUTCOME_FLAGGED, "readme_loads (case): status bug_suspect")
    assert notes == ("readme_loads (case): status bug_suspect", "readme_loads (case): 1 flag")
    bound = {
        "run": "silo__aero_bound",
        "paired_baseline": "pad__aero_bound",
        "metrics": {"status": "impact", "flags": []},
        "paired_baseline_metrics": inserted,
        "comparison_vs_paired_baseline": {"screening_status": app.BUG_SUSPECT},
        "comparison_vs_baseline": {"screening_status": "not_checked"},
    }
    kind, message, notes = _classified(tmp_path, "bound", bounds=[bound])
    assert kind == app.OUTCOME_NOT_IN_ORBIT
    assert message == "silo__aero_bound (bound) did not reach the target orbit: impact"
    assert "silo__aero_bound (bound) against pad__aero_bound: bug_suspect" in notes
    arm = {
        "run": "silo__isp__+0.1",
        "status": "search_failed",
        "flags": ["a flag"],
        "metrics": {"status": "search_failed", "search_failure_kind": "edge", "flags": ["a"]},
        "comparison": {"screening_status": "not_checked"},
        "comparison_vs_perturbed_baseline": {"screening_status": app.BUG_SUSPECT},
    }
    kind, message, notes = _classified(tmp_path, "arm", sensitivity=[arm])
    assert (kind, message) == (
        app.OUTCOME_DID_NOT_FLY,
        "silo__isp__+0.1 (sensitivity arm) did not fly: search_failed (edge)",
    )
    assert notes[1:] == (
        "silo__isp__+0.1 (sensitivity arm): 1 flag",
        "silo__isp__+0.1 (sensitivity arm) against its same-perturbation baseline: bug_suspect",
    )


def test_listing_is_kept_per_folder(
    tmp_path: Path, basis: appform.Basis, launched: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second listing of an unchanged tree stats the root and each experiment folder
    once, lists no folder again and reads no complete or failed directory (survey 07: each
    file-system call waits for the GIL during a launch); a directory added to a folder is
    listed at once; the two listings are equal."""
    root = tmp_path / "root"
    shutil.copytree(launched, root / "app" / "20260102T000000Z")
    failed = root / "recorded" / "20260101T000001Z"
    failed.mkdir(parents=True)
    (failed / results_io.FAILED_MARKER).write_text(FAILED_TEXT, encoding="utf-8")
    make_sweep(root, "sweeps", "20260101T000006Z")
    monkeypatch.setattr(app, "LISTING_SETTLE_NS", 0)
    stats: list[Path] = []
    listed: list[Path] = []
    for name, log in (("_stat", stats), ("_dir_stamp", stats), ("folder_entries", listed)):
        real_fn = getattr(app, name)

        def counted(path: Path, *args: Any, _real: Any = real_fn, _log: Any = log) -> Any:
            _log.append(path)
            return _real(path, *args)

        monkeypatch.setattr(app, name, counted)
    with serving(root, basis) as server:
        # twice: NTFS may set a new folder's mtime only when it is first read, and a
        # folder whose mtime is not yet in the past is listed again (LISTING_SETTLE_NS)
        call(server.port, "GET", "/api/results")
        time.sleep(0.05)
        first = call(server.port, "GET", "/api/results")[2]
        stats.clear()
        listed.clear()
        second = call(server.port, "GET", "/api/results")[2]
        assert len(stats) <= 1 + 3, stats  # the root and the three experiment folders
        assert listed == []
        assert second == first
        (root / "recorded" / "20260101T000002Z").mkdir()
        third = strict(call(server.port, "GET", "/api/results")[2])
    rows = {(r["experiment"], r["timestamp"]): r for g in third["groups"] for r in g["rows"]}
    assert rows[("recorded", "20260101T000002Z")]["state"] == app.DIR_INCOMPLETE
    assert len(rows) == 4


def test_listing_survives_a_row_that_raises(
    tmp_path: Path, basis: appform.Basis, launched: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory whose row raises any error is unreadable (the error's type only) and
    the others are listed."""
    root = tmp_path / "root"
    shutil.copytree(launched, root / "app" / "20260102T000000Z")
    make_sweep(root, "sweeps", "20260101T000006Z")
    real = app.directory_row

    def flaky(run_dir: Path, experiment: str, timestamp: str, *, running: bool) -> dict[str, Any]:
        if experiment == "sweeps":
            raise KeyError("secret detail")
        return real(run_dir, experiment, timestamp, running=running)

    monkeypatch.setattr(app, "directory_row", flaky)
    with serving(root, basis) as server:
        status, _, body = call(server.port, "GET", "/api/results")
    assert status == 200
    rows = [r for g in strict(body)["groups"] for r in g["rows"]]
    states = {r["experiment"]: (r["state"], r["line"]) for r in rows}
    assert states["sweeps"] == (app.DIR_UNREADABLE, "the directory could not be read: KeyError")
    assert states["app"][0] == app.DIR_COMPLETE
    assert b"secret detail" not in body


def _alias_tree(width: int, depth: int) -> dict[str, Any]:
    """A mapping ``depth`` levels deep whose ``width`` values at each level are one shared
    mapping: yaml.safe_dump writes it with anchors and aliases in about 1.5 kB a level,
    and a walk of it meets width**depth leaves."""
    node: dict[str, Any] = {"leaf": 1}
    for _ in range(depth):
        node = {f"k{i}": node for i in range(width)}
    return node


def test_a_yaml_alias_config_is_unreadable(
    tmp_path: Path, basis: appform.Basis, launched: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An app directory whose resolved_config.yaml holds a width-10, depth-9 alias tree
    under runs.silo.run (about 14 kB; 10**9 leaves when walked): its detail answers at once
    with a small body, the row unreadable with a line naming resolved_config.yaml and no
    panel; the listing stays 200; its scene is refused and never built. The same file in a
    recorded directory (whose row reads no config): no panel, panel_error with the same
    line, scene 422 with it."""
    root = tmp_path / "root"

    def bomb(metrics: dict[str, Any], config: dict[str, Any], out: Path) -> None:
        config["runs"]["silo"]["run"]["bomb"] = _alias_tree(10, 9)

    derive(launched, root, "20260105T000001Z", bomb)
    derive(launched, root, "20260105T000002Z", bomb, experiment="recorded")
    written = root / "app" / "20260105T000001Z" / run_data.CONFIG_FILE
    text = written.read_text(encoding="utf-8")
    assert "&id" in text and "*id" in text and len(text) < 100_000
    builds: list[Any] = []
    monkeypatch.setattr(scene, "scene_payload", lambda *a, **k: builds.append(a))
    line = f"{run_data.CONFIG_FILE} {app.YAML_ALIAS_REFUSED}"
    with serving(root, basis) as server:
        t0 = time.monotonic()
        status, _, body = call(server.port, "GET", "/api/results/app/20260105T000001Z")
        elapsed = time.monotonic() - t0
        listing_status = call(server.port, "GET", "/api/results")[0]
        scene_status = call(server.port, "GET", "/scene/app/20260105T000001Z/pad")[0]
        rec_status, _, rec_body = call(server.port, "GET", "/api/results/recorded/20260105T000002Z")
        rec_scene_status, _, rec_scene = call(
            server.port, "GET", "/scene/recorded/20260105T000002Z/pad"
        )
    assert status == 200 and elapsed < QUICK_S and len(body) < 100_000
    detail = strict(body)
    assert detail["row"]["state"] == app.DIR_UNREADABLE and detail["row"]["line"] == line
    assert detail["row"]["playable"] is False and detail["panel"] is None
    assert listing_status == 200 and scene_status in (409, 422)
    record = strict(rec_body)
    assert rec_status == 200 and record["row"]["state"] == app.DIR_COMPLETE
    assert record["panel"] is None
    assert record["panel_error"] == f"the results panel could not be built: {line}"
    assert rec_scene_status == 422 and strict(rec_scene)["message"] == line
    assert builds == []


def test_an_oversized_config_is_unreadable_without_parsing(
    tmp_path: Path, basis: appform.Basis, launched: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An app directory whose resolved_config.yaml is MAX_CONFIG_BYTES + 1 bytes (valid
    YAML): its row is unreadable ('over its size cap'), the listing answers within 2 s,
    the scene is refused, and the file is never parsed nor the scene built."""
    out = derive(launched, tmp_path / "root", "20260105T000003Z", lambda m, c, o: None)
    path = out / run_data.CONFIG_FILE
    pad = app.MAX_CONFIG_BYTES + 1 - path.stat().st_size - len("#\n")
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write("#" + "x" * pad + "\n")
    assert path.stat().st_size == app.MAX_CONFIG_BYTES + 1
    parsed: list[Path] = []
    real = app.read_yaml_no_alias
    monkeypatch.setattr(app, "read_yaml_no_alias", lambda p: parsed.append(p) or real(p))
    builds: list[Any] = []
    monkeypatch.setattr(scene, "scene_payload", lambda *a, **k: builds.append(a))
    with serving(tmp_path / "root", basis) as server:
        t0 = time.monotonic()
        status, _, body = call(server.port, "GET", "/api/results")
        elapsed = time.monotonic() - t0
        scene_status = call(server.port, "GET", "/scene/app/20260105T000003Z/pad")[0]
    assert status == 200 and elapsed < 2.0, elapsed
    (row,) = strict(body)["groups"][0]["rows"]
    assert row["state"] == app.DIR_UNREADABLE
    assert row["line"] == (
        f"{run_data.CONFIG_FILE} is over its size cap ({app.MAX_CONFIG_BYTES:,} bytes)"
    )
    assert scene_status in (409, 422)
    assert parsed == [] and builds == []


def test_run_folders_cost_does_not_grow_with_the_run_list(tmp_path: Path) -> None:
    """run_folders over 1,000 run folders with a metrics.json listing 600,000 runs (half
    of the folders among them, in reverse): the listed folders first in the run list's
    order, the others sorted after them; the long run list adds well under a second to
    the walk of the same folders (a membership test in a list made it about 3 s here)."""
    for i in range(1000):
        folder = tmp_path / f"run_{i:04d}"
        folder.mkdir()
        (folder / run_data.SERIES_FILE).write_text("t_s\n0\n", encoding="utf-8")
    listed = [f"run_{i:04d}" for i in range(998, -1, -2)]
    runs: dict[str, Any] = {f"x{i}": {} for i in range(600_000)}
    runs.update({name: {} for name in listed})
    app.run_folders(tmp_path, {"runs": {}})  # the file-system cache warmed
    t0 = time.perf_counter()
    walk = app.run_folders(tmp_path, {"runs": {}})
    t1 = time.perf_counter()
    out = app.run_folders(tmp_path, {"runs": runs})
    t2 = time.perf_counter()
    rest = sorted(n for n in walk if n not in set(listed))
    assert list(out) == listed + rest and all(out.values()) and len(out) == 1000
    assert (t2 - t1) - (t1 - t0) < 1.0, (t1 - t0, t2 - t1)


# ------------------------------------------------------------------ the results panel


@pytest.fixture(scope="module")
def panel_root(launched: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A results root of directories derived from the launch, one per launch kind."""
    root = tmp_path_factory.mktemp("panels")
    p_ref = 26_000.0
    derive(launched, root, "20260103T000001Z", with_case(_case("silo_s1", p_ref)))
    stage2 = _case(
        "silo_s2",
        p_ref,
        mode="stage2",
        quoted_offload_kg=REMOVED_KG - 500.0,
        quoted_basis="x* net of the pad control's x_pad: a property of the vehicle model",
        stage1_offload_kg=0.0,
        stage2_offload_kg=REMOVED_KG,
        stage1_fraction=0.0,
        stage2_fraction=REMOVED_KG / S2_LOAD_KG,
        pad_control_offload_kg=500.0,
        net_offload_kg=REMOVED_KG - 500.0,
        verification={
            "status": "ok",
            "payload_kg": p_ref + 15.36,
            "delta_kg": 15.36,
            "tolerance_kg": VERIFY_TOL_KG,
            "passed": False,
            "run": "silo_s2",
        },
        flags=["offload: offload_verify_mismatch: the payload search ended ok above P_ref"],
    )
    derive(launched, root, "20260103T000002Z", with_case(stage2))
    for stamp, delta in (("20260103T000003Z", 783.2), ("20260103T000004Z", -500.0)):
        fixed = _case(
            "silo_fix5pct",
            p_ref,
            kind="fixed",
            fixed_key="stage1_fraction",
            fixed_fraction=0.05,
            quoted_basis="imposed",
            payload_kg=p_ref + delta,
            payload_delta_kg=delta,
            verification=None,
            vs_pad={"max_q_above_pad": False, "max_q_pa": 37_000.0, "pad_max_q_pa": 38_000.0},
        )
        derive(launched, root, stamp, with_case(fixed))

    def did_not_fly(metrics: dict[str, Any], config: dict[str, Any], out: Path) -> None:
        silo = metrics["runs"]["silo"]
        silo.update(status="search_failed", search_failure_kind="edge", payload_kg=None)
        series = out / "silo" / run_data.SERIES_FILE
        header = series.read_text(encoding="utf-8").splitlines()[0]
        series.write_text(header + "\n", encoding="utf-8", newline="\n")

    derive(launched, root, "20260103T000005Z", did_not_fly)
    # a stage-2 solve whose verification failed and whose pad control carries a flag
    derive(
        launched,
        root,
        "20260103T000006Z",
        with_case(stage2, control_flags=["offload: a pad-control flag"]),
    )
    # a launch that kept SP1's committed case name (a reproduction on a committed basis)
    paired = {"run": "silo_cold_s1__pad", "status": "inserted", "payload_kg": 25_000.0}
    kept = _case("silo_cold_s1", p_ref, paired_pad=paired, **SP1_FIGURES)

    def reproduction(metrics: dict[str, Any], config: dict[str, Any], out: Path) -> None:
        with_case(kept)(metrics, config, out)
        metrics["git"]["basis_commit"] = "f" * 40

    derive(launched, root, "20260103T000007Z", reproduction)

    def deeper(metrics: dict[str, Any], config: dict[str, Any], out: Path) -> None:
        config["runs"]["silo"]["run"]["assist"]["stroke_m"] = 150

    derive(launched, root, "20260103T000008Z", deeper)

    def recorded(metrics: dict[str, Any], config: dict[str, Any], out: Path) -> None:
        with_case(_case("silo_cold_s1", p_ref, paired_pad=paired, **SP1_FIGURES))(
            metrics, config, out
        )
        metrics["label"] = None
        metrics["git"] = dict(SP1_GIT)

    derive(launched, root, SP1_STAMP, recorded, experiment=SP1_EXPERIMENT)
    return root


SP1_EXPERIMENT, SP1_STAMP = app.SP1_HEADLINE.directory.split("/")[-2:]
"""SP1's results directory as <experiment>/<timestamp> (a synthetic copy under that name
in the tests: never results/)."""
SP1_X_KG = 41_262.90803733282
"""x* of silo_cold_s1 as results/silo_offload_2d/20261003T112934Z/metrics.json records it
(the note's 41,262.908 kg)."""
SP1_FIGURES = {
    "quoted_offload_kg": SP1_X_KG,
    "offload_kg": SP1_X_KG,
    "stage1_offload_kg": SP1_X_KG,
    "total_offload_kg": SP1_X_KG,
}
"""The x* fields of a case record carrying SP1's figure."""
SP1_GIT = {"hash": app.SP1_HEADLINE.commit, "dirty": False, "error": None}
"""The git record of SP1's results directory."""


@pytest.fixture(scope="module")
def panels(panel_root: Path, basis: appform.Basis) -> dict[str, dict[str, Any]]:
    """GET /api/results/app/<stamp> of every derived app directory, by stamp, and of the
    directory named as SP1's (key SP1_STAMP); the listing under key 'listing'. The basis
    files count as SP1's at every commit (``sp1_files_same`` faked True: the fixed basis is
    read from no commit)."""
    out: dict[str, dict[str, Any]] = {}
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(app, "sp1_files_same", lambda repo_root, basis, commit=None: True)
        with serving(panel_root, basis) as server:
            assert server.sp1_same is True
            targets = [("app", p.name) for p in sorted((panel_root / "app").iterdir())]
            for experiment, stamp in [*targets, (SP1_EXPERIMENT, SP1_STAMP)]:
                status, _, body = call(server.port, "GET", f"/api/results/{experiment}/{stamp}")
                assert status == 200, body
                out[stamp] = strict(body)
            out["listing"] = strict(call(server.port, "GET", "/api/results")[2])
    return out


def test_panel_of_a_solved_stage1_case(panels: dict[str, dict[str, Any]]) -> None:
    """The tag (exploratory, both git states), the case run shown with its pad, the
    headline in t and % of stage 1, the push and the flight (max-Q above the pad's from
    the case's own comparison), the verification passed, the offload caveats word for
    word and the structure caveat with the run's own load."""
    detail = panels["20260103T000001Z"]
    panel = detail["panel"]
    assert detail["row"]["state"] == app.DIR_COMPLETE and detail["baseline"] == "pad"
    assert (
        panel["tag"]["kind"] == "exploratory" and panel["tag"]["text"] == app.TAG_EXPLORATORY_TEXT
    )
    assert panel["tag"]["server_start"] == {"hash": "0123456789ab", "state": "clean"}
    assert panel["shown"] == "silo_s1" and panel["pair"] == ["pad", "silo_s1"]
    head = panel["headline"]
    assert head["kind"] == app.HEADLINE_SOLVED and head["net_of_pad_control"] is False
    assert head["text"].startswith(
        "Propellant removed at the pad's payload (P_ref = 26,000.0 kg): 20.00 t"
    )
    assert "4.87% of the stage-1 load" in head["text"] and "saved" not in head["text"]
    assert head["flagged"] is False and head["quoted_kg"] == REMOVED_KG
    assert panel["push"]["exit_speed_mps"] > 0 and panel["push"]["facility_length_m"] > 0
    assert panel["push"]["text"].startswith("vertical silo 100 m deep")
    assert panel["flight"]["max_q_vs_pad"] == "above"
    assert panel["flight"]["max_q_text"].endswith("above the pad's (38.0 kPa)")
    assert panel["flight"]["max_q_against"] == "pad"
    assert panel["sp1_headline"] is None  # a neutral name
    comparison = panel["sp1_comparison"]
    assert comparison["case"] == "silo_cold_s1" and comparison["reproduces"] is False
    assert comparison["differs"] == ["paired pad: no (SP1's silo_cold_s1: yes)"]
    assert comparison["text"].startswith("not SP1's silo_cold_s1: 1 setting differs from it")
    assert panel["verification"]["passed"] is True and panel["verification"]["lower_bound"] is False
    assert panel["offload_caveats"] == list(OFFLOAD_CAVEATS)
    assert panel["caveats"][0] == replay.EXPLORATORY_CAVEAT and panel["error"] is None
    structure = [c for c in panel["caveats"] if "structural mass" in c]
    assert structure and "silo_s1 (" in structure[0] and "20.00 t less propellant" in structure[0]
    assert panel["reproduces"] == []
    assert panel["outcome"]["kind"] in (app.OUTCOME_COMPLETE, app.OUTCOME_FLAGGED)
    names = [r["name"] for r in detail["runs"]]
    assert names == ["pad", "silo", "silo_s1"]
    roles = {r["name"]: (r["role"], r["offload_kind"]) for r in detail["runs"]}
    assert roles["silo_s1"] == (run_data.ROLE_OFFLOAD, run_data.OFFLOAD_CASE)
    assert roles["pad"] == (run_data.ROLE_RUN, None)
    assert detail["default_pair"] == ["pad", "silo_s1"]


def test_panel_of_a_stage2_solve_with_a_failed_verification(
    panels: dict[str, dict[str, Any]],
) -> None:
    """Net of the pad control, a property of the vehicle model; the verification failed
    above P_ref reads as a flagged lower bound; the case's flag is listed."""
    panel = panels["20260103T000002Z"]["panel"]
    head = panel["headline"]
    lower = (
        "verification failed (+15.36 kg against 2.6 kg): the gross removal is a flagged lower bound"
    )
    assert head["kind"] == app.HEADLINE_SOLVED and head["net_of_pad_control"] is True
    assert appform.ADVANCED_SOLVE_READING in head["text"]
    assert "19.50 t (gross 20.00 t)" in head["text"]
    assert head["flagged"] is True and head["text"].endswith(f"; {lower}")
    ver = panel["verification"]
    assert ver["passed"] is False and ver["lower_bound"] is True
    assert ver["text"] == lower
    assert ver["verdict"].startswith("offload case silo_s2: verification failed")
    assert any("offload_verify_mismatch" in f for f in panel["flags"])


def test_a_flagged_net_figure_is_never_shown_bare(panels: dict[str, dict[str, Any]]) -> None:
    """A stage-2 solve (silo_cold_s2's record: verification failed above P_ref) quoted net
    of a flagged pad control: the headline and the verification text both say the net
    figure is uncertain both ways; the browser row carries the outcome (flagged) and its
    description says so after the figure."""
    panel = panels["20260103T000006Z"]["panel"]
    both_ways = "the net figure, which also subtracts a flagged pad control, is uncertain both ways"
    assert panel["headline"]["flagged"] is True and both_ways in panel["headline"]["text"]
    assert panel["verification"]["text"].startswith("verification failed (+15.36 kg")
    assert both_ways in panel["verification"]["text"]
    rows = {r["timestamp"]: r for g in panels["listing"]["groups"] for r in g["rows"]}
    row = rows["20260103T000006Z"]
    assert row["outcome"]["kind"] == app.OUTCOME_FLAGGED
    assert panels["20260103T000006Z"]["panel"]["outcome"]["message"] == row["outcome"]["message"]
    assert any(
        n.startswith("offload case silo_s2: verification failed")
        for n in panels["20260103T000006Z"]["panel"]["outcome"]["notes"]
    )
    figure, _, outcome = row["description"].partition("; flagged: ")
    assert "19.50 t (gross 20.00 t)" in figure and both_ways in figure
    assert outcome == row["outcome"]["message"]
    assert rows["20260103T000008Z"]["outcome"]["kind"] in (
        app.OUTCOME_COMPLETE,
        app.OUTCOME_FLAGGED,
    )


def test_sp1_headline_and_comparison_in_the_panel(panels: dict[str, dict[str, Any]]) -> None:
    """SP1's headline with its six caveat groups beside silo_cold_s1 in a directory named
    as SP1's and in an app run that kept SP1's committed case name (a reproduction: no
    difference, the reproduction line); a recorded directory has no comparison; a 150 m
    launch differs in the stroke."""
    own = panels[SP1_STAMP]["panel"]
    assert own["shown"] == "silo_cold_s1" and own["tag"]["kind"] == "recorded"
    assert own["sp1_headline"]["text"] == app.SP1_HEADLINE.text
    assert len(own["sp1_headline"]["caveats"]) == 6
    assert own["sp1_comparison"] is None
    kept = panels["20260103T000007Z"]["panel"]
    assert kept["shown"] == "silo_cold_s1"
    assert len(kept["sp1_headline"]["caveats"]) == 6
    comparison = kept["sp1_comparison"]
    assert comparison["reproduces"] is True and comparison["differs"] == []
    assert comparison["text"].startswith("silo_cold_s1: same configuration as the committed")
    assert comparison["text"].endswith(app.REPRODUCTION_TAIL)
    deeper = panels["20260103T000008Z"]["panel"]
    assert deeper["sp1_headline"] is None
    differs = deeper["sp1_comparison"]["differs"]
    assert "assist.stroke_m: 150 (SP1's silo_cold_s1: 100)" in differs
    assert "offload: none, a full load (SP1's silo_cold_s1: solve stage1)" in differs


def test_sp1_differences_of_a_pad_launch(basis: appform.Basis) -> None:
    """The pad alone and a pad-site variant say there is no push in one line; a basis
    without SP1's case gives None."""
    pad_only = {"label": "exploratory", "baseline": "pad", "runs": {"pad": {}}}
    (line,) = app.sp1_differences(basis, pad_only, {})
    assert line.startswith("launch: the pad alone, no push and no offload")
    variant = {**pad_only, "runs": {"pad": {}, "pad_variant": {}}}
    run = json.loads(json.dumps(basis.committed_runs["pad"].run_dict))
    run["ignition"]["stage1"]["t_ign_s"] = -1.0
    config = {"runs": {"pad_variant": {"run": run}}}
    lines = app.sp1_differences(basis, variant, config)
    assert lines[0].startswith("site: the pad, no push")
    assert "ignition.stage1.t_ign_s: -1.0 (SP1's silo_cold_s1: 0.5)" in lines
    assert not any(ln.startswith("assist.") for ln in lines)
    bare = dataclasses.replace(basis, case_fragments={})
    assert app.sp1_differences(bare, variant, config) is None
    assert app.sp1_comparison(bare, variant, config, []) is None


def test_sp1_differences_is_bounded(basis: appform.Basis) -> None:
    """A run dict holding one shared mapping reached 10**9 times (as a YAML alias tree
    makes it) is not walked past LEAF_BUDGET: one line says the run was not compared, at
    once. A run differing in more than SP1_DIFF_MAX_LINES settings lists that many and
    one 'and N more' line, and the comparison says 'more than' that many differ."""
    metrics = {
        "label": replay.EXPLORATORY_LABEL,
        "baseline": "pad",
        "runs": {"pad": {}, "silo": {}},
    }
    run = copy.deepcopy(basis.committed_runs["silo_cold"].run_dict)
    run["bomb"] = _alias_tree(10, 9)
    t0 = time.monotonic()
    lines = app.sp1_differences(basis, metrics, {"runs": {"silo": {"run": run}}})
    assert time.monotonic() - t0 < QUICK_S
    committed = [k for k in app._leaves(basis.committed_runs["silo_cold"].run_dict) if k != "name"]
    assert lines is not None and lines[0] == (
        f"run: more than {app.LEAF_BUDGET:,} settings, not compared one by one "
        f"(SP1's silo_cold_s1: {len(committed)} settings)"
    )
    assert len(lines) == 2 and lines[1].startswith("offload: none, a full load")
    wide = copy.deepcopy(basis.committed_runs["silo_cold"].run_dict)
    wide["extra"] = {f"s{i}": i for i in range(120)}
    config = {"runs": {"silo": {"run": wide}}}
    lines = app.sp1_differences(basis, metrics, config)
    assert lines is not None and len(lines) == app.SP1_DIFF_MAX_LINES + 1
    assert lines[0] == "extra.s0: 0 (SP1's silo_cold_s1: not set)"
    assert lines[-1] == f"and {121 - app.SP1_DIFF_MAX_LINES} more"  # 120 extras + offload
    comparison = app.sp1_comparison(basis, metrics, config, [])
    assert comparison is not None and comparison["reproduces"] is False
    assert comparison["text"].startswith(
        f"not SP1's silo_cold_s1: more than {app.SP1_DIFF_MAX_LINES} settings differ from it"
    )


def test_sp1_headline_needs_the_basis_files_to_be_sp1s(
    panel_root: Path, basis: appform.Basis
) -> None:
    """The app run that kept silo_cold_s1 with no setting different and SP1's x*
    reproduces SP1's case and carries SP1's headline only when the basis files at its
    recorded basis commit are SP1's (``sp1_same`` True); when they differ, or could not be
    checked, the comparison says so, naming that commit, and the headline is left out,
    while the directory's reproduction line stays. A directory whose settings differ never
    reproduces, whatever its reproduction lines say."""
    stamp = "20260103T000007Z"
    run_dir = panel_root / "app" / stamp
    metrics = app.read_capped_json(run_dir / run_data.METRICS_FILE, app.MAX_METRICS_BYTES)
    config = app.read_capped_yaml(run_dir / run_data.CONFIG_FILE, app.MAX_CONFIG_BYTES)
    for same, why in ((False, "differ from"), (None, "could not be checked against")):
        panel = app.results_panel(run_dir, "app", stamp, basis, metrics, config, same)["panel"]
        comparison = panel["sp1_comparison"]
        assert comparison["reproduces"] is False and comparison["differs"] == []
        assert comparison["text"] == (
            "same configuration as the committed silo_cold_s1 of the app's basis at commit "
            f"{'f' * 12}, whose files {why} SP1's at {app.SP1_HEADLINE.commit}: not called "
            "SP1's headline"
        )
        assert panel["sp1_headline"] is None
        assert any(ln.startswith("silo_cold_s1:") for ln in panel["reproduces"])
    panel = app.results_panel(run_dir, "app", stamp, basis, metrics, config, True)["panel"]
    assert panel["sp1_comparison"]["reproduces"] is True
    assert panel["sp1_headline"]["text"] == app.SP1_HEADLINE.text
    deeper = panel_root / "app" / "20260103T000008Z"
    d_metrics = app.read_capped_json(deeper / run_data.METRICS_FILE, app.MAX_METRICS_BYTES)
    d_config = app.read_capped_yaml(deeper / run_data.CONFIG_FILE, app.MAX_CONFIG_BYTES)
    claimed = [f"silo_cold_s1: same configuration as the committed silo_cold_s1 ({stamp})"]
    comparison = app.sp1_comparison(basis, d_metrics, d_config, claimed, True)
    assert comparison is not None and comparison["differs"]
    assert comparison["reproduces"] is False and comparison["text"].startswith("not SP1's")
    assert app.sp1_headline_for("app", stamp, "silo_cold_s1", d_metrics, comparison) is None


def test_sp1_files_same_by_git(basis: appform.Basis) -> None:
    """sp1_files_same (read-only git): None for a basis read from no commit (no git call),
    for a recorded commit that is not a hex hash (never passed to git, where '--output=...'
    would be an option) and for a commit git does not know; True for SP1's own commit;
    False for the repository's first commit (no experiment file yet)."""
    assert app.sp1_files_same(REPO, basis) is None
    calls: list[Any] = []
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(app.subprocess, "run", lambda *a, **k: calls.append(a))
        for odd in ("--output=x", "HEAD", "", None, 7, "F" * 40):
            assert app.sp1_files_same(REPO, basis, odd) is None, odd
    assert calls == []
    known = subprocess.run(
        ["git", "cat-file", "-e", f"{app.SP1_HEADLINE.commit}^{{commit}}"],
        cwd=REPO,
        capture_output=True,
        check=False,
    )
    if known.returncode != 0:
        pytest.skip("SP1's commit is not in this checkout's history")
    assert app.sp1_files_same(REPO, dataclasses.replace(basis, commit=app.SP1_HEADLINE.commit))
    unknown = dataclasses.replace(basis, commit="f" * 40)
    assert app.sp1_files_same(REPO, unknown) is None
    roots = subprocess.run(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    ).stdout.split()
    first = dataclasses.replace(basis, commit=roots[-1])
    assert app.sp1_files_same(REPO, first) is False


def _sp1_like(figure: float | None, git: dict[str, Any]) -> dict[str, Any]:
    """metrics.json of a directory named as SP1's whose silo_cold_s1 quotes ``figure``."""
    return {
        "git": git,
        "offload": {"cases": [{"name": "silo_cold_s1", "quoted_offload_kg": figure}]},
    }


def test_sp1_headline_needs_sp1s_figure_and_git(
    tmp_path: Path, basis: appform.Basis, launched: Path
) -> None:
    """SP1's headline is attached in a directory named as SP1's only when its git record
    is SP1's commit, clean, and its x* of silo_cold_s1 is SP1's within
    REPRODUCTION_TOL_KG (exit criterion 3), never on the name alone. An app run that kept
    SP1's case name with every setting equal, on basis files that are SP1's, but another
    x* is not SP1's headline: the code differs."""
    assert app.SP1_HEADLINE.offload_kg == 41_262.908 and app.REPRODUCTION_TOL_KG == 0.002
    tol = app.REPRODUCTION_TOL_KG
    for figure, git, attached in (
        (SP1_X_KG, SP1_GIT, True),
        (app.SP1_HEADLINE.offload_kg + 0.75 * tol, SP1_GIT, True),
        (app.SP1_HEADLINE.offload_kg - 1.25 * tol, SP1_GIT, False),
        (39_000.0, SP1_GIT, False),
        (None, SP1_GIT, False),
        (SP1_X_KG, {**SP1_GIT, "dirty": True}, False),
        (SP1_X_KG, {**SP1_GIT, "hash": "0123456789ab"}, False),
        (SP1_X_KG, {"dirty": False}, False),
    ):
        head = app.sp1_headline_for(
            SP1_EXPERIMENT, SP1_STAMP, "silo_cold_s1", _sp1_like(figure, git), None
        )
        assert (head is not None) is attached, (figure, git)
    elsewhere = app.sp1_headline_for(
        "other", SP1_STAMP, "silo_cold_s1", _sp1_like(SP1_X_KG, SP1_GIT), None
    )
    assert elsewhere is None
    paired = {"run": "silo_cold_s1__pad", "status": "inserted", "payload_kg": 25_000.0}
    other = {**SP1_FIGURES, "quoted_offload_kg": 39_000.0}

    def edit(metrics: dict[str, Any], config: dict[str, Any], out: Path) -> None:
        with_case(_case("silo_cold_s1", 26_000.0, paired_pad=paired, **other))(metrics, config, out)
        metrics["git"]["basis_commit"] = "f" * 40

    run_dir = derive(launched, tmp_path / "root", "20260105T000001Z", edit)
    metrics = app.read_capped_json(run_dir / run_data.METRICS_FILE, app.MAX_METRICS_BYTES)
    config = app.read_capped_yaml(run_dir / run_data.CONFIG_FILE, app.MAX_CONFIG_BYTES)
    panel = app.results_panel(run_dir, "app", run_dir.name, basis, metrics, config, True)["panel"]
    comparison = panel["sp1_comparison"]
    assert comparison["differs"] == [] and comparison["reproduces"] is False
    assert comparison["offload_kg"] == 39_000.0
    assert comparison["text"] == (
        "same configuration as SP1's silo_cold_s1, but x* = 39,000.0 kg against SP1's "
        "recorded 41,262.9 kg (b3150c1754ee): the code differs, so this is not SP1's headline"
    )
    assert panel["sp1_headline"] is None


def test_sp1_files_are_checked_at_each_directorys_basis_commit(
    tmp_path: Path, basis: appform.Basis, launched: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The panel's check that the basis files are SP1's runs at the directory's own
    recorded basis commit (once per commit), not the server's: two directories recorded at
    a commit whose files are SP1's reproduce SP1's case with its headline; one recorded at
    a commit whose files differ does not, and its text names that commit."""
    calls: list[Any] = []

    def fake(repo_root: Path, basis: Any, commit: Any = dataclasses.MISSING) -> bool:
        if commit is dataclasses.MISSING:
            return False  # the server's own basis: not what decides a directory's panel
        calls.append(commit)
        return commit == "f" * 40

    monkeypatch.setattr(app, "sp1_files_same", fake)
    paired = {"run": "silo_cold_s1__pad", "status": "inserted", "payload_kg": 25_000.0}

    def at(commit: str) -> Callable[..., None]:
        def edit(metrics: dict[str, Any], config: dict[str, Any], out: Path) -> None:
            record = _case("silo_cold_s1", 26_000.0, paired_pad=paired, **SP1_FIGURES)
            with_case(record)(metrics, config, out)
            metrics["git"]["basis_commit"] = commit

        return edit

    root = tmp_path / "root"
    stamps = {"20260105T000001Z": "f" * 40, "20260105T000002Z": "f" * 40}
    stamps["20260105T000003Z"] = "e" * 40
    for stamp, commit in stamps.items():
        derive(launched, root, stamp, at(commit))
    with serving(root, basis) as server:
        assert server.sp1_same is False
        panels = {
            stamp: strict(call(server.port, "GET", f"/api/results/app/{stamp}")[2])["panel"]
            for stamp in stamps
        }
    assert calls == ["f" * 40, "e" * 40]
    for stamp in ("20260105T000001Z", "20260105T000002Z"):
        assert panels[stamp]["sp1_comparison"]["reproduces"] is True
        assert panels[stamp]["sp1_headline"]["text"] == app.SP1_HEADLINE.text
    other = panels["20260105T000003Z"]
    assert other["sp1_comparison"]["reproduces"] is False and other["sp1_headline"] is None
    assert other["sp1_comparison"]["text"] == (
        f"same configuration as the committed silo_cold_s1 of the app's basis at commit "
        f"{'e' * 12}, whose files differ from SP1's at {app.SP1_HEADLINE.commit}: not called "
        "SP1's headline"
    )


def test_a_bug_suspect_run_is_flagged_never_out_of_orbit(
    tmp_path: Path, basis: appform.Basis, launched: Path
) -> None:
    """A run whose own checks failed (status bug_suspect, trace_status inserted): its
    headline says findings are blocked, how its trajectory ended and its payload as not
    to be quoted, never that it did not reach the target orbit; the browser row's
    description says the same, then the flagged outcome."""
    source = {
        "metrics": {
            "status": app.BUG_SUSPECT,
            "trace_status": app.INSERTED_STATUS,
            "run_checks_failed": "loss budget does not close",
            "payload_kg": 27_553.2,
        },
        "config": {},
        "role": run_data.ROLE_RUN,
        "compared_to": "pad",
        "comparison": {},
    }
    head = app.run_headline("silo_cold", source, {"baseline": "pad"})
    assert head["kind"] == app.HEADLINE_FLAGGED and head["flagged"] is True
    assert head["trace_status"] == app.INSERTED_STATUS
    assert head["text"] == (
        "silo_cold: bug_suspect (loss budget does not close): findings blocked until "
        "investigated (summary.md, Checks); its trajectory ended inserted; payload capacity "
        "27,553.2 kg, not to be quoted"
    )

    def suspect(metrics: dict[str, Any], config: dict[str, Any], out: Path) -> None:
        metrics["runs"]["silo"].update(
            status=app.BUG_SUSPECT, trace_status=app.INSERTED_STATUS, run_checks_failed="x"
        )

    run_dir = derive(launched, tmp_path / "root", "20260105T000001Z", suspect)
    row = app.directory_row(run_dir, "app", run_dir.name, running=False)
    assert row["outcome"] == {"kind": app.OUTCOME_FLAGGED, "message": "silo: status bug_suspect"}
    assert "did not reach" not in row["description"]
    assert "silo: bug_suspect (x): findings blocked until investigated" in row["description"]
    assert row["description"].endswith("; flagged: silo: status bug_suspect")


def test_a_bug_suspect_comparison_is_flagged_beside_the_figure(
    tmp_path: Path, basis: appform.Basis, launched: Path
) -> None:
    """A variant whose comparison with the pad is bug_suspect: its payload headline says
    so after the figure (``flagged`` True) and the panel's flags list it, beside the
    numbers, not only in the directory's outcome."""

    def suspect(metrics: dict[str, Any], config: dict[str, Any], out: Path) -> None:
        metrics["comparison"]["silo"]["screening_status"] = app.BUG_SUSPECT

    run_dir = derive(launched, tmp_path / "root", "20260105T000001Z", suspect)
    metrics = app.read_capped_json(run_dir / run_data.METRICS_FILE, app.MAX_METRICS_BYTES)
    config = app.read_capped_yaml(run_dir / run_data.CONFIG_FILE, app.MAX_CONFIG_BYTES)
    panel = app.results_panel(run_dir, "app", run_dir.name, basis, metrics, config)["panel"]
    head = panel["headline"]
    assert panel["shown"] == "silo" and head["kind"] == app.HEADLINE_PAYLOAD
    assert head["flagged"] is True
    assert head["text"].startswith("Payload capacity 27,000.0 kg, +1,000.0 kg against pad")
    assert (
        "; flagged: its comparison with pad is bug_suspect: findings blocked until "
        "investigated (summary.md, Checks)"
    ) in head["text"]
    assert panel["flags"][-1] == (
        "comparison with pad is bug_suspect: findings blocked until investigated (summary.md, "
        "Checks)"
    )
    assert panel["outcome"]["kind"] == app.OUTCOME_FLAGGED
    clean = app.run_headline(
        "silo",
        {"metrics": {"status": "inserted"}, "compared_to": "pad", "comparison": {}},
        {"baseline": "pad"},
    )
    assert clean["flagged"] is False and "flagged" not in clean["text"]


def test_an_imposed_offload_headline_names_its_penalty() -> None:
    """An imposed offload flown with an assumed stage-1 dry mass names it after the
    amount, as a solved figure does; one without a penalty does not."""
    offload = {"reference_payload_kg": 26_000.0}
    fields = {
        "kind": "fixed",
        "fixed_key": "stage1_fraction",
        "fixed_fraction": 0.05,
        "total_offload_kg": 20_550.0,
        "payload_kg": 26_429.4,
        "payload_delta_kg": 429.4,
        "verification": None,
    }
    penalised = _case(
        "silo_fix5pct", 26_000.0, **fields, stage1_dry_mass_added_kg=2_000.0, assumed_penalty=True
    )
    head = app.case_headline(penalised, offload)
    assert head["kind"] == app.HEADLINE_IMPOSED
    assert head["text"].startswith(
        "Imposed offload of 20.55 t with an assumed +2 t of stage-1 dry mass: P* - P_ref +429.4 kg"
    )
    plain = app.case_headline(_case("silo_fix5pct", 26_000.0, **fields), offload)
    assert plain["text"].startswith("Imposed offload of 20.55 t: P* - P_ref +429.4 kg")


def test_an_imposed_offload_with_a_pre_offload_states_them_apart() -> None:
    """Review of A5, round 3 (usability): an imposed stage-1 offload flown with a stage-2
    pre-offload states the two apart, as the form sets them (the pre-offload a property of
    the vehicle model, not netted), never one summed figure the push would replace; the
    penalty and P* - P_ref follow as before. The panel text is the headline as served."""
    offload = {"reference_payload_kg": 26_000.0}
    fields = {
        "kind": "fixed",
        "fixed_key": "stage1_t",
        "fixed_fraction": None,
        "stage2_preoffload_kg": 2_000.0,
        "stage1_offload_kg": 30_000.0,
        "stage2_offload_kg": 2_000.0,
        "total_offload_kg": 32_000.0,
        "payload_kg": 26_065.7,
        "payload_delta_kg": 65.7,
        "verification": None,
        "stage1_dry_mass_added_kg": 2_000.0,
        "assumed_penalty": True,
    }
    head = app.case_headline(_case("silo_fix30t", 26_000.0, **fields), offload)
    assert head["kind"] == app.HEADLINE_IMPOSED
    assert head["text"].startswith(
        "Imposed offload: 30.00 t from stage 1, plus a 2.00 t stage-2 pre-offload (a property "
        "of the vehicle model, not netted) with an assumed +2 t of stage-1 dry mass: P* - P_ref "
        "+65.7 kg"
    )
    assert "32.00 t" not in head["text"]
    # without a pre-offload the one figure stays
    alone = {**fields, "stage2_preoffload_kg": 0.0, "stage2_offload_kg": 0.0}
    alone["total_offload_kg"] = 30_000.0
    assert app.case_headline(_case("silo_fix30t", 26_000.0, **alone), offload)["text"].startswith(
        "Imposed offload of 30.00 t with an assumed +2 t"
    )


def test_a_launch_that_did_not_fly_is_described_from_its_config() -> None:
    """Review of A5, round 3 (honesty): the run browser's line (and the panel's 'Launched:'
    line) of a launched run whose search failed says no flight was recorded, never 'stage
    1 never lit' (its metrics hold no ignition time because nothing was flown: here a hot
    start lit on the carriage 2 s before the push); it keeps the silo's configured depth
    and the ramp start it set. A failed ignition that flew (status impact) still says
    stage 1 never lit."""
    assist = {
        "model": "constant_accel",
        "net_accel_g": 0.2,
        "stroke_m": 100,
        "carriage_mass_t": 0,
        "track": {"angle_deg": 90, "exit_altitude_m": 0},
    }

    def directory(ignition: dict[str, Any], silo: dict[str, Any]) -> tuple[dict, dict]:
        metrics = {
            "baseline": "pad",
            "runs": {"pad": {"status": "inserted"}, "silo": silo},
        }
        config = {  # resolved_config.yaml's runs: {name: {run: <run block>}}
            "runs": {
                "pad": {"run": {"name": "pad", "assist": {"model": "none"}}},
                "silo": {
                    "run": {"name": "silo", "assist": assist, "ignition": {"stage1": ignition}}
                },
            }
        }
        return metrics, config

    failed = {
        "status": "search_failed",
        "search_failure_kind": "grid",
        "t_ign_rel_release_s_stage1": None,
        "track_start_altitude_m": None,
        "flags": ["search_failed: grid: (first failure: drive_limit: x)"],
    }
    hot = {"t_ign_s": -2, "reference": "push_start"}
    metrics, config = directory(hot, failed)
    line = app.app_description(metrics, config, ("did_not_fly", "silo did not fly: x"))
    assert "never lit" not in line
    assert line.startswith(
        "silo: vertical silo 100 m deep, 0.2 g net push; ramp start set at T-2 s from push "
        "start; no flight recorded (its search failed), so no ignition time"
    )
    height = {"at_height_m": 300.9, "height_method": "event"}
    metrics, config = directory(height, failed)
    assert "ramp start set at 300.9 m above the mouth (event method); no flight recorded" in (
        app.app_description(metrics, config)
    )
    flown = {
        "status": "impact",
        "t_ign_rel_release_s_stage1": None,
        "track_start_altitude_m": -100.0,
    }
    metrics, config = directory({"fails": True}, flown)
    assert "; stage 1 never lit" in app.app_description(metrics, config)
    assert app.configured_ramp_start({"ignition": {"stage1": {"fails": True}}}) == (
        "stage 1 set never to light (failed ignition)"
    )
    assert app.configured_ramp_start({}) == "ramp start set at T+0 s from release"


def test_a_git_record_without_a_hash_is_never_clean() -> None:
    """A git record whose hash is missing, null, empty, not a string, 'unknown' or
    'no-git', or whose dirty flag is not a boolean, reads unknown, never clean; the shown
    hash is then 'unknown'; a recorded tag says so; an app run's working tree at launch
    too."""
    for record in (
        {"dirty": False},
        {"hash": None, "dirty": False},
        {"hash": "", "dirty": False},
        {"hash": 7, "dirty": False},
        {"hash": "unknown", "dirty": False},
        {"hash": "no-git", "dirty": False},
        {"hash": "abc", "dirty": None},
    ):
        assert app.git_view(record)["state"] == "unknown", record
    assert app.git_view({"hash": None, "dirty": False})["hash"] == app.GIT_HASH_UNKNOWN
    assert app.git_view({"hash": 7, "dirty": False})["hash"] == app.GIT_HASH_UNKNOWN
    assert app.git_view({"hash": "abc", "dirty": False}) == {"hash": "abc", "state": "clean"}
    assert app.git_view({"hash": "abc", "dirty": True})["state"] == "dirty"
    stamp = "20260101T000000Z"
    tag = app.tag_view({"git": {"dirty": False}, "runs": {}}, "x", stamp)
    assert tag["text"] == f"Recorded: x/{stamp}, git unknown (unknown)"
    exploratory = {"label": replay.EXPLORATORY_LABEL, "git": {"dirty": False}, "runs": {}}
    assert app.tag_view(exploratory, "app", stamp)["launch_tree"] == "unknown"


def test_a_yardstick_headline_says_so() -> None:
    """An instant-startup run's payload headline (silo_instant, pad_instant: a step to
    full thrust) says it is a yardstick, not a design, and carries yardstick True; a run
    with a real startup does not."""
    source = {
        "metrics": {
            "status": app.INSERTED_STATUS,
            "payload_kg": 27_880.4,
            "startup_kind_stage1": "step",
        },
        "config": {},
        "role": run_data.ROLE_RUN,
        "compared_to": "pad",
        "comparison": {"payload_delta_kg": 1_826.0, "payload_delta_upper_bound": True},
    }
    head = app.run_headline("silo_instant", source, {"baseline": "pad"})
    assert head["yardstick"] is True
    assert head["text"] == (
        "Payload capacity 27,880.4 kg, +1,826.0 kg against pad (an upper bound: unthrottled "
        f"and unconstrained); {app.YARDSTICK_TEXT}"
    )
    source["metrics"]["startup_kind_stage1"] = "ramp"
    head = app.run_headline("silo_cold", source, {"baseline": "pad"})
    assert head["yardstick"] is False and "yardstick" not in head["text"]


def test_case_headline_net_of_nothing_and_the_frontier_case() -> None:
    """A stage-2 solve whose x* is at or below its pad control's x_pad (or quotes
    nothing) is 'nothing net of the pad control', as classify says, never a negative
    removal; the frontier case leads with its stage-1 x* and says the imposed stage-2
    tonnes are not netted."""
    offload = {
        "reference_payload_kg": 26_000.0,
        "pad_controls": [{"mode": "stage2", "offload_kg": 513.6, "flags": []}],
    }
    fields = {
        "mode": "stage2",
        "offload_kg": 400.0,
        "total_offload_kg": 400.0,
        "pad_control_offload_kg": 513.6,
        "net_offload_kg": -113.6,
    }
    for quoted in (-113.6, None):
        head = app.case_headline(
            _case("silo_s2", 26_000.0, **fields, quoted_offload_kg=quoted), offload
        )
        assert head["kind"] == app.HEADLINE_NOTHING
        assert head["text"].startswith(
            "Offload case silo_s2: nothing net of the pad control (x* 0.400 t, pad control "
            "0.514 t, net -0.114 t)"
        )
        assert "Propellant removed" not in head["text"]
    total = S1_LOAD_KG + S2_LOAD_KG
    frontier = _case(
        "silo_s1_s2pre2t",
        26_000.0,
        stage2_preoffload_kg=2_000.0,
        quoted_offload_kg=18_000.0,
        stage1_offload_kg=18_000.0,
        stage2_offload_kg=2_000.0,
        total_offload_kg=REMOVED_KG,
        stage1_fraction=18_000.0 / S1_LOAD_KG,
        stage2_fraction=2_000.0 / S2_LOAD_KG,
        total_fraction=REMOVED_KG / total,
    )
    head = app.case_headline(frontier, offload)
    assert head["kind"] == app.HEADLINE_SOLVED and head["quoted_kg"] == 18_000.0
    assert head["text"] == (
        "Propellant removed at the pad's payload (P_ref = 26,000.0 kg): 18.00 t of stage 1 "
        "(4.38% of the stage-1 load), solved after 2.00 t imposed on stage 2 first "
        f"({appform.ADVANCED_FIXED_READING}); 20.00 t, 3.86% of all, in total"
    )


def test_max_q_of_a_bound_names_its_paired_baseline() -> None:
    """A bound run is compared with its paired baseline, not the pad: the text names it
    and quotes that run's max-Q."""
    source = {
        "metrics": {"max_q_pa": 30_000.0, "status": "inserted"},
        "config": {},
        "role": run_data.ROLE_BOUND,
        "compared_to": "pad__aero_bound",
        "comparison": {"max_q_above_baseline": False},
    }
    metrics = {
        "baseline": "pad",
        "runs": {"pad": {"max_q_pa": 37_200.0}},
        "bounds": [{"run": "silo__aero_bound", "paired_baseline_metrics": {"max_q_pa": 35_500.0}}],
    }
    flight = app.flight_view("silo__aero_bound", source, metrics)
    assert flight["max_q_text"] == "max-Q 30.0 kPa, below pad__aero_bound's (35.5 kPa)"
    assert flight["max_q_against"] == "pad__aero_bound"


def test_max_q_of_a_run_short_of_orbit_is_not_compared() -> None:
    """Review of A5: a run that did not reach the target orbit (a failed ignition's impact)
    has its max-Q without 'above' or 'below the pad's': its flight is no like-for-like
    comparison; outcome rows count flags in words ('1 flag', '2 flags'); an absent setting
    in the comparison with SP1's case reads 'not set', never 'none' (a push key stated the
    other way is not 'no push')."""
    source = {
        "metrics": {"max_q_pa": 3_600.0, "status": "impact"},
        "config": {},
        "role": "run",
        "compared_to": "pad",
        "comparison": {"max_q_above_baseline": False},
    }
    metrics = {"baseline": "pad", "runs": {"pad": {"max_q_pa": 37_200.0}}}
    flight = app.flight_view("silo_failed", source, metrics)
    assert flight["max_q_text"] == "max-Q 3.6 kPa"
    assert flight["max_q_vs_pad"] is None and flight["max_q_against"] is None
    assert [app.flags_text(n) for n in (1, 2)] == ["1 flag", "2 flags"]
    assert app._setting_text(None) == "not set"


def test_panel_of_an_imposed_offload_above_and_below_p_ref(
    panels: dict[str, dict[str, Any]],
) -> None:
    """P* - P_ref with its reading (D-SP2-27): above, not the largest possible offload;
    below, a payload loss; never 'saved'; max-Q below the pad's; the verification is not
    applicable (only a solved x* is verified), never 'no verification recorded', which a
    solved case without one still says."""
    above = panels["20260103T000003Z"]["panel"]
    below = panels["20260103T000004Z"]["panel"]
    for panel in (above, below):
        assert panel["headline"]["kind"] == app.HEADLINE_IMPOSED
        assert "saved" not in panel["headline"]["text"]
        assert panel["verification"]["text"] == app.IMPOSED_VERIFICATION_TEXT
        assert panel["verification"]["passed"] is None
        assert panel["flight"]["max_q_vs_pad"] == "below"
    unverified = _case("silo_s1", 26_000.0, verification=None)
    assert app.verification_view(unverified, {})["text"] == "no verification recorded"
    assert above["headline"]["text"].startswith("Imposed offload of 20.00 t: P* - P_ref +783.2 kg")
    assert "not the largest possible" in above["headline"]["text"]
    assert below["headline"]["delta_kg"] == -500.0
    assert "a payload loss at this offload, not a propellant saving" in below["headline"]["text"]


def test_panel_of_a_run_that_did_not_fly(panels: dict[str, dict[str, Any]]) -> None:
    """The variant's series is empty: still listed and playable (the pad has rows), the
    panel shows the variant with 'The run did not fly' and its kind, the caveats are
    built for the pad alone, and the outcome says it did not fly."""
    detail = panels["20260103T000005Z"]
    panel = detail["panel"]
    assert detail["row"]["playable"] is True
    assert panel["shown"] == "silo"
    assert panel["headline"] == {
        "kind": app.HEADLINE_DID_NOT_FLY,
        "status": "search_failed",
        "text": "The run did not fly: search_failed (edge)",
    }
    assert {r["name"]: r["has_rows"] for r in detail["runs"]} == {"pad": True, "silo": False}
    assert panel["built_for"] == ["pad"]
    assert panel["outcome"]["kind"] == app.OUTCOME_DID_NOT_FLY
    assert detail["default_pair"] == ["pad"]
    assert detail["panel_error"] is None
    # its run-list line: the launched run's own headline says it did not fly, so the
    # outcome is not repeated after it (step A5)
    row = next(
        r
        for g in panels["listing"]["groups"]
        for r in g["rows"]
        if r["timestamp"] == "20260103T000005Z"
    )
    assert "The run did not fly: search_failed (edge)" in row["description"]
    assert "did_not_fly" not in row["description"] and "silo did not fly" not in row["description"]


def test_panel_for_the_runs_the_scene_shows(
    panel_root: Path, basis: appform.Basis, tmp_path: Path
) -> None:
    """GET /api/panel/<experiment>/<timestamp>/<runs> (step A5: the results panel follows
    the runs the page's scene shows): the panel of the runs named, the right-hand one
    shown and the caveats built for them; one run alone; the selection rule of the scene
    route (1 to PANEL_RUNS distinct runs of the directory's run list, else 422); 409 for a
    directory with no panel; GET /api/results/... keeps the directory's own pair; every
    panel carries what the scene draws that the model does not compute
    (scene.DISPLAY_ONLY, design 4.9)."""
    stamp = "20260103T000001Z"
    sweep = make_sweep(tmp_path / "other", "sweeps", "20260101T000006Z")
    with serving(panel_root, basis) as server:

        def get(path: str) -> tuple[int, Any]:
            status, _, body = call(server.port, "GET", path)
            return status, strict(body)

        own_status, own = get(f"/api/results/app/{stamp}")
        pair_status, pair = get(f"/api/panel/app/{stamp}/pad,silo")
        alone_status, alone = get(f"/api/panel/app/{stamp}/pad")
        refused = {
            sel: get(f"/api/panel/app/{stamp}/{sel}")[0]
            for sel in ("pad,pad", "pad,silo,silo_s1", "nope", "pad,nope", "")
        }
        missing = get("/api/panel/app/20990101T000000Z/pad")[0]
        extra = call(server.port, "GET", f"/api/panel/app/{stamp}/pad/x")[0]
    with serving(sweep.parent.parent, basis) as server:
        swept = call(server.port, "GET", f"/api/panel/sweeps/{sweep.name}/pad")
    assert own_status == pair_status == alone_status == 200
    assert own["panel"]["shown"] == "silo_s1" and own["panel"]["pair"] == ["pad", "silo_s1"]
    assert pair["panel"]["shown"] == "silo" and pair["panel"]["pair"] == ["pad", "silo"]
    assert pair["panel"]["built_for"] == ["pad", "silo"]
    assert pair["panel"]["headline"] != own["panel"]["headline"]
    assert pair["runs"] == own["runs"] and pair["default_pair"] == own["default_pair"]
    assert alone["panel"]["shown"] == "pad" and alone["panel"]["pair"] == ["pad"]
    assert alone["panel"]["push"] is None  # the pad has no push
    assert refused == {sel: 422 for sel in refused}
    assert missing == 404 and extra == 404
    assert swept[0] == 409 and strict(swept[2])["error"] == "no_panel"
    for detail in (own, pair, alone):
        assert detail["panel"]["display_only"] == list(scene.DISPLAY_ONLY)
    assert ("GET", "/api/panel/<experiment>/<timestamp>/<runs>") in app.ROUTES


def test_recorded_rows_name_the_findings_notes_that_cite_them(
    tmp_path: Path, basis: appform.Basis, launched: Path
) -> None:
    """GET /api/results: each row carries the findings notes of the repository
    (docs/findings/*.md) that cite its results/<experiment>/<timestamp>, with the note's
    first heading as its title; a row no note cites carries none; a missing folder gives
    none."""
    root = tmp_path / "root"
    shutil.copytree(launched, root / "recorded" / "20260105T000001Z")
    shutil.copytree(launched, root / "recorded" / "20260105T000002Z")
    notes = tmp_path / "docs" / "findings"
    notes.mkdir(parents=True)
    (notes / "RQ9-test.md").write_text(
        "# RQ9: a test note\n\nSee results/recorded/20260105T000001Z/summary.md and again "
        "results/recorded/20260105T000001Z.\n",
        encoding="utf-8",
    )
    (notes / "RQ8-other.md").write_text(
        "no heading, cites results/recorded/20260105T000001Z\n", encoding="utf-8"
    )
    with serving(root, basis) as server:
        listing = strict(call(server.port, "GET", "/api/results")[2])
    rows = {r["timestamp"]: r for g in listing["groups"] for r in g["rows"]}
    assert rows["20260105T000001Z"]["cited_in"] == [
        {"path": "docs/findings/RQ8-other.md", "title": "RQ8-other"},
        {"path": "docs/findings/RQ9-test.md", "title": "RQ9: a test note"},
    ]
    assert rows["20260105T000002Z"]["cited_in"] == []
    assert app.findings_citations(tmp_path / "nowhere") == {}


@pytest.mark.skipif(sup.NODE is None, reason="node not installed: the page's panel text is not run")
def test_page_panel_text_from_served_records(
    panels: dict[str, dict[str, Any]], tmp_path: Path
) -> None:
    """The app page's results panel (templates/app.html's panelBlocks under node) on the
    records GET /api/results serves for each derived launch kind and for SP1's directory:
    the order of design 4.7 (the tag, the run shown, its headline, the comparison, the
    push, the flight, flags and verification, the caveats); 'Reproduction' only over
    reproduction lines, SP1's comparison under its own heading otherwise; the offload runs
    of an offload launch, each with its note; a run that did not fly has no push or flight
    block; no value is a unit or a 'T+' on a missing number; the caveats box ends with
    every display-only item of design 4.9; no heading or label of the page says 'saved'
    (D-SP2-27; the server's own sentences are tested where they are made)."""
    stamps = [k for k in panels if k != "listing"]
    out = sup.run_page_pure(
        sup.PAGE_BLOCKS_HARNESS, {"details": [panels[k] for k in stamps]}, tmp_path
    )
    for stamp, lines in zip(stamps, out["panels"], strict=True):
        panel = panels[stamp]["panel"]
        tags = [t for t, _ in lines]
        texts = [x for _, x in lines]
        heads = [x for t, x in lines if t == "h3"]
        assert tags[0].startswith("p.tag"), stamp
        shown = texts.index(next(x for x in texts if x.startswith("Run shown: ")))
        assert tags[shown + 1].startswith("p.headline"), stamp
        assert ("Reproduction" in heads) == bool(panel["reproduces"]), stamp
        comparison = panel["sp1_comparison"]
        if comparison and comparison["text"] not in panel["reproduces"]:
            assert f"Against SP1's {comparison['case']}" in heads, stamp
            # SP1's headline is an offload: a launch without one is not compared with it
            if any(r["role"] == "offload" for r in panels[stamp]["runs"]):
                assert comparison["text"] in texts
            else:
                at = texts.index(f"Against SP1's {comparison['case']}")
                assert texts[at + 1].endswith(
                    "this launch has no offload, so it is not compared with it."
                )
        order = [h for h in heads if h in ("Push", "Flight", "Flags and verification")] + [
            heads[-1]
        ]
        if panel["headline"]["kind"] == app.HEADLINE_DID_NOT_FLY:
            assert "Push" not in heads and "Flight" not in heads, stamp
        else:
            assert order[:2] == ["Push", "Flight"], stamp
        assert heads[-1] == "Read before quoting: the caveats of the runs shown", stamp
        assert order[-2:] == ["Flags and verification", heads[-1]], stamp
        box = tags.index("box.caveats")
        # folded, its summary counting what it holds (round 3 of the A5 review)
        display = texts.index(
            "What the scene draws that the model does not compute (display only): "
            f"{len(scene.DISPLAY_ONLY)} items"
        )
        assert tags[display] == "summary"
        assert box < display and texts[display + 1 : display + 1 + len(scene.DISPLAY_ONLY)] == list(
            scene.DISPLAY_ONLY
        )
        # every served push of the prescribed drive carries its model, and the panel says
        # under its text what the carriage mass and the impingement fraction change
        if panel["push"] is not None and panel["headline"]["kind"] != app.HEADLINE_DID_NOT_FLY:
            assert panel["push"]["model"] == "constant_accel", stamp
            at = lines.index(["h3", "Push"])
            assert lines[at + 1] == ["p", panel["push"]["text"]], stamp
            assert lines[at + 2] == ["p.meta", DRIVE_NOTE], stamp
        offload = [r for r in panels[stamp]["runs"] if r["role"] == "offload" and r["note"]]
        if offload:
            assert any(h.startswith("Offload runs of this") for h in heads + texts), stamp
            assert all(r["note"] in texts for r in offload), stamp
        for tag, text in lines:
            label = text
            if tag == "kv":
                label, value = text.split(": ", 1)
                assert "not recorded" == value or "not recorded" not in value, (stamp, text)
                assert not re.match(r"^\S+ not recorded", value), (stamp, text)
            if tag in ("kv", "h3", "h4", "summary"):
                assert not re.search(r"\bsaved\b", label, re.I), (stamp, text)


def test_scene_of_runs_without_rows_and_a_panel_that_fails(
    panel_root: Path, basis: appform.Basis, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A selection whose only run has no row is 422 no_scene naming the directory as
    <experiment>/<timestamp>, never its local path; the pad of the same directory plays.
    A panel that cannot be built leaves the row with panel_error (the type only)."""
    stamp = "20260103T000005Z"
    with serving(panel_root, basis) as server:
        status, _, body = call(server.port, "GET", f"/scene/app/{stamp}/silo")
        refusal = strict(body)
        assert status == 422 and refusal["error"] == "no_scene"
        assert f"app/{stamp}" in refusal["message"]
        assert str(panel_root) not in refusal["message"] and "\\" not in refusal["message"]
        assert call(server.port, "GET", f"/scene/app/{stamp}/pad")[0] == 200

        def broken(*args: Any) -> dict[str, Any]:
            raise KeyError("a detail nobody should see")

        monkeypatch.setattr(app, "results_panel", broken)
        status, _, body = call(server.port, "GET", "/api/results/app/20260103T000004Z")
    detail = strict(body)
    assert status == 200 and detail["row"]["state"] == app.DIR_COMPLETE
    assert detail["panel"] is None
    assert detail["panel_error"] == "the results panel could not be built: KeyError"
    assert b"nobody" not in body


def test_reproduction_lines_from_a_directory(basis: appform.Basis) -> None:
    """Only an exploratory directory with a server-start record and the basis commit
    names reproductions: the pad alone is the committed baseline; a committed variant or
    case name is a reproduction; a neutral one is not."""
    git = {"hash": "h", "dirty": False, "server_start": dict(CLEAN), "basis_commit": "f" * 40}
    pad_only = {"label": "exploratory", "git": git, "baseline": "pad", "runs": {"pad": {}}}
    (line,) = app.directory_reproduction_lines(basis, pad_only)
    assert line.startswith("pad: the committed baseline of experiments/silo_offload_2d.yaml")
    assert "ffffffffffff: a reproduction, not new evidence" in line
    kept = {
        **pad_only,
        "runs": {"pad": {}, "silo_cold": {}},
        "offload": {"cases": [{"name": "silo_cold_s1"}]},
    }
    lines = app.directory_reproduction_lines(basis, kept)
    assert [ln.split(":")[0] for ln in lines] == ["silo_cold", "silo_cold_s1"]
    neutral = {
        **pad_only,
        "runs": {"pad": {}, "silo": {}},
        "offload": {"cases": [{"name": "silo_s1"}]},
    }
    assert app.directory_reproduction_lines(basis, neutral) == []
    assert app.directory_reproduction_lines(basis, {**kept, "label": None}) == []
    no_commit = {**kept, "git": {**git, "basis_commit": None}}
    assert app.directory_reproduction_lines(basis, no_commit) == []


# ------------------------------------------------------------------ the scene route


def test_scene_route_selection_and_cache(
    tmp_path: Path, basis: appform.Basis, launched: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """1 to 4 distinct runs of the directory's run list (else 422), the page rendered by
    scene.render_page and kept in the LRU (a second request builds nothing), 409 for an
    unplayable directory, 404 for an unknown one."""
    root = tmp_path / "root"
    stamp = launched.name
    shutil.copytree(launched, root / "app" / stamp)
    make_sweep(root, "sweeps", "20260101T000006Z")
    builds: list[tuple[str, ...]] = []
    real = scene.scene_payload

    def counting(run_dir: Path, runs: Any, *, display_dir: Path) -> dict[str, Any]:
        builds.append(tuple(runs))
        return real(run_dir, runs, display_dir=display_dir)

    monkeypatch.setattr(scene, "scene_payload", counting)
    reads: list[str] = []
    for name in ("read_capped_json", "read_capped_yaml"):
        real_read = getattr(app, name)

        def read(path: Path, cap: int, *, _real: Any = real_read) -> dict[str, Any]:
            reads.append(path.name)
            return _real(path, cap)

        monkeypatch.setattr(app, name, read)
    with serving(root, basis) as server:
        base = f"/scene/app/{stamp}/"
        status, headers, page = call(server.port, "GET", base + "pad,silo")
        assert status == 200 and headers["content-type"] == app.HTML_CONTENT_TYPE
        assert scene.SCENE_MARKER in page.decode("ascii")
        assert reads  # the first request read metrics.json
        reads.clear()
        assert call(server.port, "GET", base + "pad,silo")[2] == page
        assert reads == []  # a cached page reads no file
        assert call(server.port, "GET", base + "silo")[0] == 200
        assert builds == [("pad", "silo"), ("silo",)]
        for bad in ("pad,pad", "pad,silo,nope", "", "pad,silo,pad,silo,pad", "pad,"):
            status, _, body = call(server.port, "GET", base + bad)
            assert status == 422 and strict(body)["error"] == "bad_selection", bad
        status, _, body = call(server.port, "GET", "/scene/sweeps/20260101T000006Z/pad")
        assert status == 409 and strict(body)["reason"] == app.REASON_SWEEP
        assert call(server.port, "GET", "/scene/app/20990101T000000Z/pad")[0] == 404
    assert len(server._scenes) == 2  # the LRU of rendered pages


def test_lru_keeps_the_most_recent() -> None:
    lru = app.LruCache(2)
    lru.put("a", 1)
    lru.put("b", 2)
    assert lru.get("a") == 1
    lru.put("c", 3)
    assert lru.keys() == ["a", "c"] and lru.get("b") is None


# ------------------------------------------------------------------ injection


def test_injected_text_is_escaped_in_every_response(
    tmp_path: Path, basis: appform.Basis, launched: Path
) -> None:
    """A directory whose label, offload caveats, run and case flags carry HTML and
    script text, and a FAILED.txt whose line does: /api/results and the panel are strict
    JSON with no '<' (each string round-trips exactly), and the scene page's data block
    has no '<' and holds the text exactly."""
    root = tmp_path / "root"
    record = _case("silo_s1", 26_000.0, flags=[f"flag {INJECT_SCRIPT}"])

    def edit(metrics: dict[str, Any], config: dict[str, Any], out: Path) -> None:
        with_case(record, flags=[f"run flag {INJECT_IMG}"])(metrics, config, out)
        metrics["label"] = INJECT_IMG
        metrics["offload"]["caveats"].append(INJECT_SCRIPT)
        metrics["runs"]["silo"]["flags"] = [INJECT_SCRIPT]

    derive(launched, root, "20260104T000001Z", edit)
    failed = root / "app" / "20260104T000002Z"
    failed.mkdir(parents=True)
    (failed / results_io.FAILED_MARKER).write_text(
        f"partial\n\nTraceback:\n  frame\nValueError: {INJECT_SCRIPT} {INJECT_IMG}\n",
        encoding="utf-8",
    )
    with serving(root, basis) as server:
        listing_status, _, listing = call(server.port, "GET", "/api/results")
        detail_status, _, detail = call(server.port, "GET", "/api/results/app/20260104T000001Z")
        scene_status, _, page = call(
            server.port, "GET", "/scene/app/20260104T000001Z/pad,silo,silo_s1"
        )
    assert (listing_status, detail_status, scene_status) == (200, 200, 200)
    for body in (listing, detail):
        assert b"<" not in body and b">" not in body
        strict(body)
    rows = {r["timestamp"]: r for g in strict(listing)["groups"] for r in g["rows"]}
    assert rows["20260104T000001Z"]["label"] == INJECT_IMG
    assert rows["20260104T000002Z"]["line"] == f"ValueError: {INJECT_SCRIPT} {INJECT_IMG}"
    panel = strict(detail)
    assert INJECT_SCRIPT in panel["panel"]["offload_caveats"]
    silo = next(r for r in panel["runs"] if r["name"] == "silo")
    assert silo["flags"] == [INJECT_SCRIPT]
    text = page.decode("ascii")
    block = re.findall(
        r'<script type="application/json" id="scene-data">(.*?)</script>', text, re.S
    )
    assert len(block) == 1 and "<" not in block[0]
    data = strict(block[0])
    assert data["label"] == INJECT_IMG and INJECT_SCRIPT in data["caveats"]
    assert INJECT_IMG not in text and INJECT_SCRIPT not in text


# ------------------------------------------------------------------ the page and the form


PAGE_INPUTS = (
    "location.search",
    "location.href",
    "document.URL",
    "document.referrer",
    "window.name",
    "onmessage",
    "opener",
)
"""What another site controls when it opens GET / (the one route it can reach) that the
app page's script never reads. Step A5's page reads its own hash and takes its scene
frame's height message only as tests/test_app_page.py checks: the hash only when the user
opened the page (GET /'s from_other_site false), the message only from the frame's own
window and origin, and only a number."""
ACTING_ROUTES = {"/api/launches": "postLaunch", "/scene/": "scenePath"}
"""Routes the app page names, each once, in the one function that asks for it;
tests/test_app_page.py checks that both act only behind the page's may-act guard (a page
another site opened acts only once the user has used it; exit criterion 17) and that a
launch follows a click."""


def test_app_page_template(tmp_path: Path, basis: appform.Basis) -> None:
    """The app page (step A5): ASCII, one data token (strict JSON, '<' escaped, the
    printed URL, the boot id and whether another site opened the page), the brand mark and
    tab icon byte for byte, one inline script with no HTML sink, textContent for every
    value, no external request. GET / is the one route another site can open (with any
    hash, query or referrer), so the script reads none of PAGE_INPUTS and names each of
    ACTING_ROUTES once, in the function that asks for it (review 04; criterion 17;
    tests/test_app_page.py has the rest)."""
    template = app.load_app_template()
    assert template.isascii() and template.count(app.APP_DATA_TOKEN) == 1
    assert "\r" not in template
    assert LOGO.read_text(encoding="utf-8").strip() in template
    (href,) = re.findall(r'<link rel="icon" type="image/svg\+xml" href="([^"]*)">', template)
    assert base64.b64decode(href.removeprefix("data:image/svg+xml;base64,")) == FAVICON.read_bytes()
    script = re.findall(r"<script>(.*?)</script>", template, re.S)
    assert len(script) == 1
    for sink in HTML_SINKS:
        assert sink not in script[0], sink
    for name in PAGE_INPUTS:
        assert name not in script[0], name
    for route, owner in ACTING_ROUTES.items():
        assert script[0].count(route) == 1, route
        body = re.search(rf"\n  function {owner}\(.*?\n  \}}\n", script[0], re.S)
        assert body is not None and route in body.group(0), (route, owner)
    assert "textContent" in script[0] and "step A5" in template
    assert re.findall(r"https?://[^\s\"']+", template) == ["http://www.w3.org/2000/svg"]
    with serving(tmp_path / "root", basis) as server:
        status, _, body = call(server.port, "GET", "/", headers={"Sec-Fetch-Site": "none"})
        other = call(server.port, "GET", "/")[2].decode("ascii")  # no Sec-Fetch-Site: fail safe
    assert '"from_other_site":true' in other
    page = body.decode("ascii")
    (block,) = re.findall(
        r'<script type="application/json" id="app-data">(.*?)</script>', page, re.S
    )
    assert strict(block) == {
        "url": server.url,
        "boot_id": server.boot_id,
        "version": app.__version__,
        "from_other_site": False,
    }
    assert status == 200


def test_api_form(tmp_path: Path, basis: appform.Basis) -> None:
    """GET /api/form: the presets this basis resolves (on the fixed basis the offload
    presets are listed as unavailable with a reason), each with its label, expected
    range and request (which parse_request gives back), no committed name on an edited
    basis; every field with its enumeration and range; the server-start record; SP1's
    headline with six caveat groups; the boot id."""
    with serving(tmp_path / "root", basis) as server:
        status, _, body = call(server.port, "GET", "/api/form")
    info = strict(body)
    assert status == 200 and info["boot_id"] == server.boot_id
    names = [p["name"] for p in info["presets"]] + [p["name"] for p in info["presets_unavailable"]]
    assert sorted(names) == sorted(appform.PRESET_NAMES)
    unavailable = {p["name"] for p in info["presets_unavailable"]}
    assert {"silo_cold_s1", "silo_cold_fix5pct"} <= unavailable
    assert all(p["reason"] for p in info["presets_unavailable"])
    for preset in info["presets"]:
        assert preset["committed_name"] is None
        assert preset["expected_s"][0] < preset["expected_s"][1]
        assert isinstance(appform.parse_request(preset["request"]), appform.Form)
    assert [f["key"] for f in info["fields"]] == list(appform.FIELDS)
    site = next(f for f in info["fields"] if f["key"] == "site")
    assert site["choices"] == list(appform.SITES)
    assert info["server_start"]["state"] == "clean" and info["server_start"]["code_check"] is False
    assert info["limits"]["max_body_bytes"] == app.MAX_JSON_BODY_BYTES
    assert len(info["headline"]["caveats"]) == 6
    assert info["exploratory_caveat"] == replay.EXPLORATORY_CAVEAT


def test_sp1_headline_matches_the_findings_note() -> None:
    """D-SP2-36: the headline text is the note's bold headline verbatim (whitespace
    normalised, '**' removed: only the groups may paraphrase); every number of the
    headline constant and of its six caveat groups, the group titles, the status, the
    directory, the commit and the case's x* (the note's validation measurement, 41,262.908
    kg) are in docs/findings/RQ1-fuel-offload-2d.md; each number is
    also in its own text; each group's phrases (the clauses a paraphrase must keep, such
    as the drive efficiency that moves only the electricity) are in the note and in the
    group's text."""
    note = " ".join(FINDINGS_NOTE.read_text(encoding="utf-8").split())
    head = app.SP1_HEADLINE
    assert head.text in note.replace("**", "")
    assert len(head.caveats) == 6
    for item in (head.status, head.directory, head.commit, head.case, *head.numbers):
        assert item in note, item
    assert f"{head.offload_kg:,.3f} kg" == "41,262.908 kg" and "41,262.908 kg" in note
    for number in head.numbers:
        assert number in head.text, number
    for caveat in head.caveats:
        assert f"**{caveat.title}" in note, caveat.title
        text = " ".join(caveat.text.split())
        for number in caveat.numbers:
            assert number in note, number
            assert number in text, number
        for phrase in caveat.phrases:
            assert phrase in note, phrase
            assert phrase in text, phrase
    drive = head.caveats[5]
    assert drive.phrases == (
        "drive efficiency moves only the electricity",
        "No ullage, centre-of-gravity or residual effect is modelled",
    )


# ------------------------------------------------------------------ resources


def test_no_resource_warning_after_a_server_and_a_job(
    tmp_path: Path, basis: appform.Basis, request_body: dict[str, Any]
) -> None:
    """Open a server, run a stub job, make raw and http.client requests, close it; after
    gc.collect() no ResourceWarning was raised (review 05 finding 6)."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        runner = StubRunner()
        with serving(tmp_path / "root", basis, runner=runner) as server:
            assert call(server.port, "POST", "/api/launches", request_body)[0] == 202
            wait_job(server)
            call(server.port, "GET", "/api/job")
            raw(server.port, b"GET /api/job HTTP/1.0\r\nHost: 127.0.0.1:%d\r\n\r\n" % server.port)
            raw(server.port, b"NONSENSE\r\n\r\n")
        worker = server._worker
        assert worker is not None and not worker.is_alive()
        del server, runner, worker
        gc.collect()
    leaks = [w for w in caught if issubclass(w.category, ResourceWarning)]
    assert not leaks, [str(w.message) for w in leaks]


# ------------------------------------------------------------------ the command


def test_cli_app_busy_port_is_one_error_line(
    tmp_path: Path, basis: appform.Basis, capsys: pytest.CaptureFixture[str]
) -> None:
    """A port already bound: exit 1 and one ASCII error line naming the port, never
    another port; a port out of range too."""
    with serving(tmp_path / "root", basis) as server:
        code = cli.main(["app", "--port", str(server.port), "--results-root", str(tmp_path)])
    out = capsys.readouterr().out.splitlines()
    assert code == 1 and len(out) == 1
    assert out[0].startswith(f"error: port {server.port} on 127.0.0.1 is in use")
    assert out[0].isascii()
    assert cli.main(["app", "--port", "70000"]) == 1
    assert capsys.readouterr().out.startswith("error: --port must be 0 to 65535")


def test_app_repo_root_needs_the_experiment_file(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    with pytest.raises(cli.CliError, match=r"experiments/silo_offload_2d\.yaml not found"):
        cli.app_repo_root([tmp_path])
    assert cli.app_repo_root([REPO / "src"]) == REPO


def test_cli_app_ctrl_c_marks_the_running_launch_and_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """In process: the start lines (the URL, the results root, the server-start git
    state, the Ctrl+C line), a launch running when KeyboardInterrupt reaches
    serve_forever: FAILED.txt in its directory, one stopped line, exit 0; the SIGBREAK
    handler is restored."""
    runner = StubRunner(block=True)
    monkeypatch.setattr(app, "WORKER_JOIN_TIMEOUT_S", 0.1)  # the stub job stays blocked
    before = signal.getsignal(signal.SIGBREAK) if hasattr(signal, "SIGBREAK") else None
    root = tmp_path / "root"

    def serve(server: app.AppServer, runner: StubRunner, form: appform.Form) -> None:
        assert server.start_launch(form)[0] == 202
        assert runner.made.wait(TIMEOUT_S)
        raise KeyboardInterrupt

    code = _cli_app_with(monkeypatch, runner, root, serve)
    out = capsys.readouterr().out.splitlines()
    assert code == 0
    assert re.fullmatch(r"launchsim app: http://127\.0\.0\.1:\d+/   \(this machine only\)", out[0])
    assert out[1] == f"  results root: {root}"
    assert out[2].startswith("  code: git ")
    assert out[4] == "  Ctrl+C stops the server; a running launch is stopped and marked FAILED"
    assert out[5].startswith("  video: ")  # step A6v: ffmpeg's absolute path, or why it is off
    assert out[-2] == cli.stopping_line()
    assert out[-1].startswith("launchsim app: stopped; the running launch is marked FAILED in ")
    assert all(line.isascii() for line in out)
    assert runner.out_dir is not None
    assert app.failed_line(runner.out_dir / results_io.FAILED_MARKER).startswith(STOPPED)
    if before is not None:
        assert signal.getsignal(signal.SIGBREAK) == before
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


def _cli_app_with(
    monkeypatch: pytest.MonkeyPatch,
    runner: StubRunner,
    root: Path,
    serve: Callable[[app.AppServer, StubRunner, appform.Form], None],
    extra_args: tuple[str, ...] = (),
) -> int:
    """cli.main(['app', '--port', '0', '--results-root', root, *extra_args]) with
    ``runner`` as the launch function and ``serve(server, runner, form)`` as serve_forever
    (it may start the shipped silo_cold preset, and ends by raising KeyboardInterrupt or
    another exception); the runner released and abandoned afterwards. A
    KeyboardInterrupt escaping cli.main fails the test (never the session)."""
    monkeypatch.setattr(app, "run_launch", runner)
    shipped = sup.shipped_basis()
    form = appform.preset_form(shipped, "silo_cold")

    def serve_forever(self: app.AppServer, poll_interval: float = app.SERVE_POLL_S) -> None:
        serve(self, runner, form)

    monkeypatch.setattr(app.AppServer, "serve_forever", serve_forever)
    try:
        return cli.main(["app", "--port", "0", "--results-root", str(root), *extra_args])
    except KeyboardInterrupt as exc:
        raise AssertionError("a second interrupt escaped cli.main") from exc
    finally:
        runner.abandon = True
        runner.pre.set()
        runner.gate.set()
        runner.writing.set()


def test_cli_app_a_second_ctrl_c_during_the_stop_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A launch in its writing stage when Ctrl+C comes, and a second Ctrl+C (an
    interrupt_main 0.2 s into the 1 s grace wait): the stopping line at once, no
    traceback, FAILED.txt with the stop's reason, the stopped line last, exit 0, SIGINT's
    handler restored."""
    import _thread

    runner = StubRunner()
    runner.writing.clear()
    monkeypatch.setattr(app, "STOP_WRITING_GRACE_S", 1.0)
    monkeypatch.setattr(app, "WORKER_JOIN_TIMEOUT_S", 0.1)  # the stub job stays blocked
    timers: list[threading.Timer] = []

    def serve(server: app.AppServer, runner: StubRunner, form: appform.Form) -> None:
        assert server.start_launch(form)[0] == 202
        deadline = time.monotonic() + TIMEOUT_S
        while server.job_snapshot()["stage"] != app.STAGE_WRITING:
            assert time.monotonic() < deadline
            time.sleep(POLL_S)
        timer = threading.Timer(0.2, _thread.interrupt_main)
        timers.append(timer)
        timer.start()
        raise KeyboardInterrupt

    code = _cli_app_with(monkeypatch, runner, tmp_path / "root", serve)
    for timer in timers:
        timer.join(TIMEOUT_S)
    out = capsys.readouterr().out.splitlines()
    assert code == 0
    assert out[-2] == cli.stopping_line() and "gets up to 1 s to finish" in out[-2]
    assert out[-1].startswith("launchsim app: stopped; the running launch is marked FAILED in ")
    assert runner.out_dir is not None
    line = app.failed_line(runner.out_dir / results_io.FAILED_MARKER)
    assert line.startswith(f"{STOPPED} while launch 1 was running: stage writing")
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


def test_cli_app_ctrl_c_before_the_directory_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Ctrl+C while the launch is still in its preflight (no directory yet): the worker
    makes its directory after the stop, inside close()'s join, and marks it FAILED; the
    stopped line names it; exit 0."""
    runner = StubRunner(block=True)
    runner.pre.clear()
    monkeypatch.setattr(app, "WORKER_JOIN_TIMEOUT_S", 0.5)  # the stub job stays blocked
    real_stop = app.AppServer.stop_active_job

    def stop(self: app.AppServer) -> Path | None:
        marked = real_stop(self)
        runner.pre.set()  # the directory is made after the stop
        return marked

    monkeypatch.setattr(app.AppServer, "stop_active_job", stop)

    def serve(server: app.AppServer, runner: StubRunner, form: appform.Form) -> None:
        assert server.start_launch(form)[0] == 202
        assert runner.started.wait(TIMEOUT_S)
        raise KeyboardInterrupt

    code = _cli_app_with(monkeypatch, runner, tmp_path / "root", serve)
    assert runner.made.wait(TIMEOUT_S)
    out = capsys.readouterr().out.splitlines()
    assert code == 0
    assert runner.out_dir is not None
    line = app.failed_line(runner.out_dir / results_io.FAILED_MARKER)
    assert line.startswith(f"{STOPPED} while launch 1 was running: stage preflight")
    assert out[-1] == (
        f"launchsim app: stopped; the running launch is marked FAILED in {runner.out_dir}"
    )


def test_cli_app_an_exception_while_serving_marks_the_running_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """serve_forever leaving by an OSError (select failing) while a launch runs: the
    launch is marked FAILED all the same (never left to read incomplete), main prints one
    error line, no stopping or stopped line, exit 1; SIGINT's handler restored."""
    runner = StubRunner(block=True)
    monkeypatch.setattr(app, "WORKER_JOIN_TIMEOUT_S", 0.1)  # the stub job stays blocked

    def serve(server: app.AppServer, runner: StubRunner, form: appform.Form) -> None:
        assert server.start_launch(form)[0] == 202
        assert runner.made.wait(TIMEOUT_S)
        raise OSError(10038, "select failed")

    code = _cli_app_with(monkeypatch, runner, tmp_path / "root", serve)
    out = capsys.readouterr().out.splitlines()
    assert code == 1
    assert [ln for ln in out if ln.startswith("error:")] == out[-1:]
    assert out[-1] == "error: OSError: [Errno 10038] select failed"
    assert cli.stopping_line() not in out
    assert not any(ln.startswith("launchsim app: stopped") for ln in out)
    assert runner.out_dir is not None
    line = app.failed_line(runner.out_dir / results_io.FAILED_MARKER)
    assert line.startswith(f"{STOPPED} while launch 1 was running: stage pad")
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


def test_cli_app_an_interrupt_during_its_start_is_one_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Ctrl+C (or Ctrl+Break, handled as Ctrl+C from the command's first statement) while
    the app reads its basis, or while it builds its server: one line, exit 0, no
    traceback, nothing written, the SIGBREAK handler restored."""
    before = signal.getsignal(signal.SIGBREAK) if hasattr(signal, "SIGBREAK") else None
    seen: list[Any] = []

    def interrupted(*args: Any, **kwargs: Any) -> Any:
        if hasattr(signal, "SIGBREAK"):
            seen.append(signal.getsignal(signal.SIGBREAK))
        raise KeyboardInterrupt

    root = tmp_path / "root"
    for target in ("load_basis", "sp1_files_same"):  # sp1_files_same runs in AppServer()
        with monkeypatch.context() as mp:
            mp.setattr(app, target, interrupted)
            try:
                code = cli.main(["app", "--port", "0", "--results-root", str(root)])
            except KeyboardInterrupt as exc:
                raise AssertionError(f"the interrupt in {target} escaped cli.main") from exc
        captured = capsys.readouterr()
        assert code == 0 and captured.out.splitlines() == [cli.STOPPED_BEFORE_SERVING_LINE]
        assert captured.err == ""
        if before is not None:
            assert signal.getsignal(signal.SIGBREAK) == before
    if hasattr(signal, "SIGBREAK"):
        assert seen == [signal.default_int_handler] * 2
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler
    assert not root.exists()


def test_cli_app_open_opens_the_url_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--open: webbrowser.open_new_tab (faked: no browser opens) is called once, with the
    server's URL, before serving; without the flag it is never called."""
    opened: list[str] = []
    monkeypatch.setattr(cli.webbrowser, "open_new_tab", lambda url: opened.append(url) or True)
    urls: list[str] = []

    def serve(server: app.AppServer, runner: StubRunner, form: appform.Form) -> None:
        urls.append(server.url)
        raise KeyboardInterrupt

    runner = StubRunner()
    code = _cli_app_with(monkeypatch, runner, tmp_path / "root", serve, ("--open",))
    assert code == 0 and len(urls) == 1 and opened == urls
    opened.clear()
    urls.clear()
    assert _cli_app_with(monkeypatch, runner, tmp_path / "root2", serve) == 0
    assert len(urls) == 1 and opened == []
    assert runner.calls == 0
    capsys.readouterr()


def test_cli_app_without_display_files_is_one_error_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A checkout without the display files: one error line at start and exit 1, never a
    server that answers every scene page with a 500."""
    missing = Path("configs") / "no_such_display"
    monkeypatch.setattr(scene, "DEFAULT_DISPLAY_DIR", missing)
    code = cli.main(["app", "--port", "0", "--results-root", str(tmp_path)])
    out = capsys.readouterr().out.splitlines()
    assert code == 1 and len(out) == 1
    assert out[0].startswith("error: configs/no_such_display not found in ")
    assert out[0].endswith(": the scene pages need it")


def test_cli_app_port_held_on_the_wildcard_is_busy(
    tmp_path: Path, basis: appform.Basis, capsys: pytest.CaptureFixture[str]
) -> None:
    """A socket bound (not listening, so no firewall prompt) on 0.0.0.0:P: on Windows a
    127.0.0.1:P bind would still succeed and share the port; the app refuses it with the
    busy line and exit 1. The same for a socket on [::1]:P (skipped without IPv6)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as squatter:
        squatter.bind(("0.0.0.0", 0))
        port = squatter.getsockname()[1]
        code = cli.main(["app", "--port", str(port), "--results-root", str(tmp_path)])
    out = capsys.readouterr().out.splitlines()
    assert code == 1 and len(out) == 1
    assert out[0].startswith(f"error: port {port} on 127.0.0.1 is in use or reserved")
    try:
        squatter6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    except OSError:
        pytest.skip("no IPv6 socket on this machine")
    with squatter6:
        try:
            squatter6.bind(("::1", 0))
        except OSError:
            pytest.skip("no IPv6 loopback on this machine")
        port6 = squatter6.getsockname()[1]
        with pytest.raises(OSError) as caught:
            app.AppServer(
                port=port6,
                basis=basis,
                server_start=START,
                results_root=tmp_path,
                repo_root=tmp_path,
                display_dir=DISPLAY_DIR,
            )
    assert app.port_unavailable(caught.value)


@pytest.mark.slow
@pytest.mark.skipif(sys.platform != "win32", reason="Ctrl+Break is a Windows console event")
def test_ctrl_break_stops_the_app_and_marks_the_launch(tmp_path: Path) -> None:
    """``python -m launchsim app --port 0 --results-root <tmp>`` in a new process group
    with the shipped basis: read the URL, launch the silo_cold preset, wait for its
    directory, send CTRL_BREAK_EVENT: exit 0, exactly the six start lines (the video line
    since step A6v), the stopping line and the stopped line on stdout, nothing on stderr,
    FAILED.txt (review 05 finding 7)."""
    root = tmp_path / "root"
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    lines: list[str] = []
    errors: list[str] = []
    with subprocess.Popen(
        [sys.executable, "-m", "launchsim", "app", "--port", "0", "--results-root", str(root)],
        cwd=REPO,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,  # type: ignore[attr-defined]
    ) as proc:
        assert proc.stdout is not None and proc.stderr is not None

        def read(stream: Any, into: list[str]) -> None:
            for line in stream:
                into.append(line.decode("ascii", errors="replace").rstrip())

        reader = threading.Thread(target=read, args=(proc.stdout, lines), daemon=True)
        err_reader = threading.Thread(target=read, args=(proc.stderr, errors), daemon=True)
        reader.start()
        err_reader.start()
        try:
            deadline = time.monotonic() + 120.0
            port = None
            while port is None:
                assert time.monotonic() < deadline and proc.poll() is None, lines
                found = [re.search(r"http://127\.0\.0\.1:(\d+)/", ln) for ln in lines]
                port = next((int(m.group(1)) for m in found if m), None)
                time.sleep(0.05)
            info = strict(call(port, "GET", "/api/form")[2])
            request = next(p["request"] for p in info["presets"] if p["name"] == "silo_cold")
            status, _, body = call(port, "POST", "/api/launches", request)
            assert status == 202, body
            directory = None
            while directory is None:
                assert time.monotonic() < deadline, lines
                directory = strict(call(port, "GET", "/api/job")[2])["directory"]
                time.sleep(0.05)
            os.kill(proc.pid, signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
            code = proc.wait(timeout=60)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=30)
        reader.join(timeout=30)
        err_reader.join(timeout=30)
    assert code == 0, (lines, errors)
    assert errors == []  # nothing on stderr: no warning, no traceback, through a real launch
    assert len(lines) == 8, lines  # the six start lines, the stopping line, the stopped line
    assert lines[4] == "  Ctrl+C stops the server; a running launch is stopped and marked FAILED"
    assert lines[5].startswith("  video: ")  # step A6v: ffmpeg's path, or why the export is off
    assert lines[6] == cli.stopping_line()
    assert lines[7].startswith("launchsim app: stopped; the running launch is marked FAILED")
    marker = root / directory["experiment"] / directory["timestamp"] / results_io.FAILED_MARKER
    assert app.failed_line(marker).startswith(STOPPED)
