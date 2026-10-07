"""The app's MP4 export (SP2 step A6v; src/launchsim/video.py and the video routes of
src/launchsim/app.py; design docs/phases/inputs/2026-10-05-SP2-design.md section 4.8 and
D-SP2-30; security review 04 findings 1, 2, 5, 6 and 8; delivery review 05 finding 8;
design review 06 finding 9; honesty review 02 finding 9). Every server binds 127.0.0.1 on
port 0 over a folder under tmp_path, never results/; every video goes to a folder under
tmp_path; a fake encoder (a Python script run as the resolved encoder's command) stands in
for ffmpeg in the fast tier, and the session's timeouts are shortened through its Limits.

Fast:

- the PNG header check: a BMP body, a PNG of another size, a PNG declaring 12,000 x
  12,000, an interlaced PNG, a palette PNG, a 16-bit PNG, a truncated body, bytes after
  IEND and a body without IEND: each 422 through the route and the session unchanged;
- frame order: a skipped or repeated index 409; the byte budget (413, the declared body
  read and discarded first); frame 1,801 (422 at creation) and an index past the count
  (409); every refusal after the length check drains the declared body before it is
  answered, so 100 wrong-index posts of 1 MB each and 50 posts to a cancelled session are
  all answered 409 with no socket error (fix round 1: a refusal with the body unread closed
  the socket on unread data, a reset the client saw as a lost connection);
- the frame route by raw sockets: a foreign Origin 403, a cross-site Sec-Fetch-Site 403,
  text/plain and no Content-Type 415, 4 MiB + 1 announced 413 at once, chunked 400, an
  unknown id 404, a non-numeric index 404; the JSON routes keep their rule; finish and
  cancel take an empty JSON object only (a key is 422 unknown_key, the state unchanged);
- the request rules: unknown keys, fps and width off the lists, frames and seconds
  together, a times list of the wrong length, a run not in the directory, a directory not
  listed; the create response (the id, size, times echoed, the footer: the three lines of
  plots.animation_caveats, and the exploratory line first for an exploratory directory;
  the display-only caveat is the scene page's own footer line on every captured frame,
  never a second server line: D-SP2-23, fix round 1);
- the default frame rate (20) keeps the gate pair's natural clip (86.4 wall s, the A6v QA's
  measurement of the player) within the 1,800-frame limit, where 24 fps would not;
- the finished file crosses volumes: os.replace refused with EXDEV (or Windows' error 17)
  falls back to a copy onto the reservation, the session done, the temporary folder gone;
- a fake encoder that never reads stdin: 503 once the queue is full and the room timeout
  passes, then the session fails on the idle or blocked-write timeout, the slot is freed,
  the temporary folder removed; one that exits early (the session fails with its stderr
  tail); one that floods stderr (no hang; the tail capped);
- an abandoned session frees the slot; cancel discards the partial file; finish with
  frames missing is 409; the exclusive reservation keeps an existing file and takes -2;
  the output is refused inside a results tree (the server says the export is off, a
  create is 503, reserve_output raises); a launch during a video and a video during a
  launch are 409; the server's exit closes an open session;
- the ffmpeg lookup, in a subprocess with NoDefaultCurrentDirectoryInExePath cleared and
  an ffmpeg.bat planted in the working directory: the bare shutil.which would take it,
  find_ffmpeg does not (the PATH entry that is the working directory is rejected, another
  entry's ffmpeg is taken, and with no other entry nothing is found);
- MP4_CRF equals plots.MP4_CRF;
- fix round 2 (security pass 2): a wrapper encoder (a .bat, or an sh script) whose child
  is the program that never reads: the session fails within the timeouts, the whole tree is
  dead, the slot free, the folder gone and the server's close prompt; cancels at several
  moments after the start leave no folder (the removal retries); a start that fails after
  the folder is made (the stderr file, the encoder, a thread) removes it; an encoder that
  writes past the stderr cap fails the session with the size in its error; a frame POST to
  an unknown id is 404 with its body drained (DRAIN_POSTS of 1 MB, no socket error); every
  temporary-folder check is on the session's own folder, never a listing of %TEMP%.

Fix round 3 (security pass 3, compliance pass 3, honesty pass 3): a zTXt, iCCP or
compressed iTXt chunk (a zlib bomb at any size), an acTL chunk and an unknown chunk type
are refused by the header check (the uncompressed chunks a canvas writes accepted); numbers
json accepts but float() or round() refuse are 422, never a 500; a playable directory whose
series pandas cannot parse is 422 on the video and the scene routes; an encoder that takes
every frame and never exits fails on the finish timeout, and one left finishing is cancelled
by the server's close; the last ended session's record outlives the next session's
creation; one kept HTTP/1.1 connection carries a whole clip's requests, and a 413 closes
it. Slow: real canvas PNGs from headless Edge at the three sizes pass the header check.

Slow (three, the real ffmpeg): 48 synthesised 1280 x 720 PNG frames through the routes
into an MP4 of 48 frames (ffprobe when present, else the file's size and header); the same
clip saved through a working directory on another volume (the \\\\localhost\\C$ alias of
tmp_path, nothing written outside it; skipped where the alias is unreachable or the same
volume); a frame whose IDAT does not inflate (a header-valid PNG with random pixel data)
fails the session with ffmpeg's reason (-xerror) instead of a shorter clip reported done.
"""

from __future__ import annotations

import base64
import contextlib
import errno
import http.client
import importlib.util
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zlib
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from launchsim import app, appform, plots, replay, run_data, scene, video


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
CLEAN = {"hash": "0123456789ab", "dirty": False, "error": None}
START = app.ServerStart(git=dict(CLEAN), head=None)
POLL_S = 0.02
TIMEOUT_S = 30.0
QUICK_S = 5.0
"""A response that must come at once (the server did not wait for a body) arrives within
this [s]."""
WIDTH, HEIGHT = 960, 540
"""The frame size of the fast tests (the smallest width offered)."""
FAKE_OUTPUT_BYTES = 4096
"""What the copying fake encoder writes as its MP4."""
FLOOD_BYTES = 3 * 1024 * 1024
"""What the flooding fake writes to stderr."""
SHORT = video.Limits(room_timeout_s=0.3, idle_s=1.0, write_block_s=1.0, finish_s=2.0)
"""The shortened timeouts of the fast tier."""
GATE_PAIR_NATURAL_S = 86.4
"""The natural length [wall s] of the gate pair's clip (pad beside silo_cold_s1) under the
Auto law: the A6v QA timed the player over the whole scene at 86.4 s and clipTimes gave
86.35 s (a6v_qa.md run 2); the default frame rate must keep it within MAX_FRAMES."""
BIG_BODY_BYTES = 1024 * 1024
"""A frame body the size of a drawn 1920 x 1080 frame, for the drain tests."""
DRAIN_POSTS = 100
CANCELLED_POSTS = 50
"""Posts of the drain tests: wrong-index frames, frames to a cancelled session and (fix
round 2) frames to an unknown session id."""
UNKNOWN_ID = "AAAAAAAAAAAAAAAAAAAAAA"
"""A well-formed session id no session has."""
CANCEL_RACE_DELAYS_S = (0.05, 0.15, 0.25, 0.35, 0.45, 0.55)
"""How long after its start each session of the cancel-race test is cancelled [s] (the
probe that found the leak left folders at 0.20 s and later; fix round 2)."""
STDERR_CAP_LIMITS = video.Limits(
    **{**SHORT.__dict__, "idle_s": 5.0, "stderr_max_bytes": FLOOD_BYTES // 3}
)
"""The stderr-cap test's limits: a 1 MiB cap the flooding fake (3 MiB) passes, the idle
timeout kept out of the way."""

FAKE_ENCODER = '''
"""A stand-in for ffmpeg (tests/test_video.py): argv[1] is the behaviour, the rest ffmpeg's
argument list (the output path last). never_reads writes its pid beside this script
(never_reads.pid) so a test can see whether a kill reached it through a wrapper."""
import os, sys, time

behaviour = sys.argv[1]
args = sys.argv[2:]
output = args[-1]
if behaviour == "copy":
    n = 0
    while True:
        chunk = sys.stdin.buffer.read(65536)
        if not chunk:
            break
        n += len(chunk)
    with open(output, "wb") as fh:  # the fake's own bytes file (no encoding= applies)
        fh.write(b"\\x00\\x00\\x00\\x18ftypisom" + bytes(%(size)d - 12) + str(n).encode())
    sys.exit(0)
if behaviour == "never_reads":
    pid_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "never_reads.pid")
    with open(pid_file, "w", encoding="utf-8") as fh:
        fh.write(str(os.getpid()))
    time.sleep(60)
    sys.exit(0)
if behaviour == "exit_early":
    sys.stderr.write("boom: the fake encoder refused the input\\n")
    sys.stderr.flush()
    sys.exit(1)
if behaviour == "flood":
    sys.stderr.write("x" * %(flood)d + " END-OF-FLOOD\\n")
    sys.stderr.flush()
    while sys.stdin.buffer.read(65536):
        pass
    sys.exit(2)
if behaviour == "slow_finish":
    while sys.stdin.buffer.read(65536):
        pass
    time.sleep(60)
    with open(output, "wb") as fh:  # the fake's own bytes file (no encoding= applies)
        fh.write(bytes(%(size)d))
    sys.exit(0)
sys.exit(9)
'''


# ------------------------------------------------------------------ helpers


def fake_encoder(folder: Path, behaviour: str) -> video.Encoder:
    """An Encoder whose command runs FAKE_ENCODER with ``behaviour`` under this
    interpreter (the fake replaces the resolved ffmpeg path)."""
    script = folder / "fake_ffmpeg.py"
    if not script.exists():
        script.write_text(
            FAKE_ENCODER % {"size": FAKE_OUTPUT_BYTES, "flood": FLOOD_BYTES},
            encoding="utf-8",
            newline="\n",
        )
    return video.Encoder((sys.executable, str(script), behaviour), video.H264_ENCODER)


def wrapper_encoder(folder: Path, behaviour: str) -> video.Encoder:
    """An Encoder whose command is a wrapper script (Windows: a .bat; elsewhere an sh
    script) that runs the fake encoder as its child and waits for it: the shape of a
    chocolatey or scoop shim, or a .bat, on PATH (fix round 2). A kill of the wrapper alone
    leaves the child with the pipe."""
    inner = fake_encoder(folder, behaviour)
    quoted = " ".join(f'"{part}"' for part in inner.command)
    if sys.platform == "win32":
        wrapper = folder / "ffmpeg_wrapper.bat"
        wrapper.write_text(f"@{quoted} %*\r\n", encoding="utf-8", newline="")
    else:
        wrapper = folder / "ffmpeg_wrapper.sh"
        wrapper.write_text(f'#!/bin/sh\n{quoted} "$@"\n', encoding="utf-8", newline="\n")
        wrapper.chmod(0o755)
    return video.Encoder((str(wrapper),), video.H264_ENCODER)


def process_alive(pid: int) -> bool:
    """Whether a process with ``pid`` exists: tasklist on Windows (os.kill with signal 0
    would terminate it there), a null signal elsewhere."""
    if sys.platform == "win32":
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        ).stdout
        return any(line.split()[1:2] == [str(pid)] for line in out.splitlines())
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def session_spec(directory: Path, frames: int = 5) -> video.SessionSpec:
    """A SessionSpec of the fast tests' size for the launched directory's pad and silo."""
    return video.SessionSpec(
        experiment=directory.parent.name,
        timestamp=directory.name,
        runs=("pad", "silo"),
        run_dir=directory,
        fps=video.DEFAULT_FPS,
        frames=frames,
        width=WIDTH,
        height=HEIGHT,
        footer=(),
    )


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png_bytes(
    width: int = WIDTH,
    height: int = HEIGHT,
    *,
    depth: int = 8,
    colour: int = 2,
    interlace: int = 0,
    rows: int | None = None,
    shade: int = 0x40,
) -> bytes:
    """A valid PNG by hand: IHDR, one IDAT of filter-0 scanlines (``rows`` of them: the
    declared height by default; fewer makes a header-only PNG whose pixel data is short,
    which the header check does not see), IEND."""
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colour]
    bytes_per_px = max(1, channels * depth // 8)
    n_rows = height if rows is None else rows
    raw = b"".join(bytes([0]) + bytes([shade]) * (width * bytes_per_px) for _ in range(n_rows))
    ihdr = struct.pack(">IIBBBBB", width, height, depth, colour, 0, 0, interlace)
    return (
        video.PNG_SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw, 1))
        + _chunk(b"IEND", b"")
    )


def frame(k: int = 0) -> bytes:
    """A good frame of the fast tests' size (a shade per index, so bodies differ)."""
    return png_bytes(shade=(0x20 + 7 * k) % 256)


@contextlib.contextmanager
def serving(
    root: Path,
    basis: appform.Basis,
    *,
    encoder: video.Encoder | None,
    work_dir: Path,
    limits: video.Limits = SHORT,
    runner: Any = None,
    video_reason: str = "",
) -> Iterator[app.AppServer]:
    """An AppServer on 127.0.0.1:0 over ``root`` with the given encoder, working directory
    and limits, serving in a daemon thread, closed (and the thread joined) on exit."""
    work_dir.mkdir(parents=True, exist_ok=True)
    server = app.AppServer(
        port=0,
        basis=basis,
        server_start=START,
        results_root=root,
        repo_root=root.parent,
        display_dir=DISPLAY_DIR,
        runner=runner,
        encoder=encoder,
        video_reason=video_reason,
        work_dir=work_dir,
        video_limits=limits,
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


def call(
    port: int,
    method: str,
    path: str,
    body: Any = None,
    headers: dict[str, str] | None = None,
    content_type: str = "application/json",
) -> tuple[int, dict[str, str], Any]:
    """One request through http.client: (status, headers lower-cased, the JSON body or
    None). A bytes body is sent as it is with ``content_type``; anything else as JSON."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT_S)
    try:
        sent = dict(headers or {})
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            sent.setdefault(
                "Content-Type", content_type if isinstance(body, bytes) else "application/json"
            )
        conn.request(method, path, body=data, headers=sent)
        response = conn.getresponse()
        raw = response.read()
        try:
            parsed = json.loads(raw) if raw else None
        except ValueError:
            parsed = None
        return response.status, {k.lower(): v for k, v in response.getheaders()}, parsed
    finally:
        conn.close()


def read_response(sock: socket.socket) -> bytes:
    """One HTTP response from ``sock``: read until the server closes, or (a kept
    connection, fix round 3) until the head and its Content-Length of body bytes have
    arrived."""
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


def split_response(response: bytes) -> tuple[int, bytes]:
    """(status, body) of one raw response; status 0 without a status line."""
    head, _, body = response.partition(b"\r\n\r\n")
    first = head.split(b"\r\n")[0].decode("latin-1") if head else ""
    status = int(first.split(" ")[1]) if first.startswith("HTTP/") else 0
    return status, body


def raw_request(port: int, payload: bytes, timeout: float = TIMEOUT_S) -> tuple[int, bytes]:
    """``payload`` over a raw socket, one response read (``read_response``): (status,
    body)."""
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as sock:
        sock.sendall(payload)
        return split_response(read_response(sock))


def create(
    port: int, directory: Path, runs: list[str], frames: int = 3, **extra: Any
) -> tuple[int, Any]:
    """POST /api/videos for ``directory`` (an app/<timestamp> folder) and ``runs``."""
    request = {
        "experiment": directory.parent.name,
        "timestamp": directory.name,
        "runs": runs,
        "fps": video.DEFAULT_FPS,
        "width": WIDTH,
        "frames": frames,
        **extra,
    }
    status, _, body = call(port, "POST", "/api/videos", request)
    return status, body


def post_frame(port: int, vid: str, k: int, body: bytes) -> tuple[int, Any]:
    status, _, parsed = call(
        port, "POST", f"/api/videos/{vid}/frames/{k}", body, content_type="image/png"
    )
    return status, parsed


def record(port: int, vid: str) -> dict[str, Any]:
    status, _, body = call(port, "GET", f"/api/videos/{vid}")
    assert status == 200, body
    return body["video"]


def wait_state(
    port: int, vid: str, states: tuple[str, ...], timeout: float = TIMEOUT_S
) -> dict[str, Any]:
    """The record once its state is one of ``states``."""
    deadline = time.monotonic() + timeout
    while True:
        rec = record(port, vid)
        if rec["state"] in states:
            return rec
        assert time.monotonic() < deadline, rec
        time.sleep(POLL_S)


def finish_and_wait(port: int, vid: str) -> dict[str, Any]:
    status, _, body = call(port, "POST", f"/api/videos/{vid}/finish", {})
    assert status == 202, body
    return wait_state(port, vid, video.FINAL_STATES)


def session_of(server: app.AppServer, vid: str) -> video.VideoSession:
    return server.video_session(vid)


def wait_until(check: Any, timeout: float = TIMEOUT_S) -> None:
    deadline = time.monotonic() + timeout
    while not check():
        assert time.monotonic() < deadline
        time.sleep(POLL_S)


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def basis() -> appform.Basis:
    return sup.fixed_basis()


@pytest.fixture(scope="module")
def launched(basis: appform.Basis, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One real fixed-guidance launch of the silo_cold preset (run_launch, no plots, about
    a second): an exploratory app directory with the runs pad and silo."""
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


@pytest.fixture
def root(tmp_path: Path, launched: Path) -> Path:
    """A results root holding a copy of the launched directory."""
    root = tmp_path / "root"
    shutil.copytree(launched, root / launched.parent.name / launched.name)
    return root


@pytest.fixture
def directory(root: Path, launched: Path) -> Path:
    return root / launched.parent.name / launched.name


# ------------------------------------------------------------------ the PNG header check


def with_chunk(extra: bytes, body: bytes | None = None) -> bytes:
    """``body`` (a good frame by default) with ``extra`` (a whole chunk) inserted after
    IHDR."""
    data = png_bytes() if body is None else body
    at = len(video.PNG_SIGNATURE) + video.PNG_CHUNK_HEAD + video.IHDR_LENGTH + video.PNG_CHUNK_CRC
    return data[:at] + extra + data[at:]


def bomb_chunk(kind: bytes, inflated_kib: int = 256, keyword: bytes = b"Comment") -> bytes:
    """A zTXt, iCCP or compressed iTXt chunk whose zlib stream inflates to
    ``inflated_kib`` KiB of zeros (the security pass 2 probe's shape at any size): what the
    layout check must refuse (fix round 3), since ffmpeg inflates such a chunk with no cap
    (a 2 MB body inflating to 2 GiB cost it 3 GiB of commit)."""
    comp = zlib.compress(bytes(1024) * inflated_kib, 9)
    if kind == b"zTXt":
        data = keyword + b"\x00\x00" + comp  # keyword, null, method 0, data
    elif kind == b"iCCP":
        data = b"icc\x00\x00" + comp
    else:
        data = keyword + b"\x00\x01\x00\x00\x00" + comp  # the compression flag set
    return _chunk(kind, data)


BAD_PNGS: dict[str, bytes] = {
    "bmp": b"BM" + bytes(60),
    "other size": png_bytes(WIDTH, HEIGHT - 2),
    "12000 x 12000 declared": png_bytes(12_000, 12_000, rows=1),
    "interlaced": png_bytes(interlace=1),
    "palette": png_bytes(colour=3),
    "16-bit": png_bytes(depth=16),
    "truncated": png_bytes()[:-20],
    "bytes after IEND": png_bytes() + b"\x00",
    "no IEND": png_bytes()[: -len(_chunk(b"IEND", b""))],
    "IHDR not first": video.PNG_SIGNATURE + _chunk(b"tEXt", b"a\x00b") + png_bytes()[8:],
    "empty": b"",
    # fix round 3 (security pass 3): compressed ancillary chunks, animation chunks and
    # unknown types are refused before the frame is piped
    "zTXt bomb": with_chunk(bomb_chunk(b"zTXt")),
    "iCCP bomb": with_chunk(bomb_chunk(b"iCCP")),
    "compressed iTXt bomb": with_chunk(bomb_chunk(b"iTXt")),
    "acTL (animated PNG)": with_chunk(_chunk(b"acTL", bytes(8))),
    "unknown chunk type": with_chunk(_chunk(b"abCd", b"x")),
    "second IHDR": with_chunk(png_bytes()[8 : 8 + 12 + video.IHDR_LENGTH]),
    "ancillary over the limit": with_chunk(
        _chunk(b"tEXt", b"k\x00" + bytes(video.PNG_ANCILLARY_MAX_BYTES))
    ),
}

CANVAS_CHUNKS = (
    (b"sRGB", b"\x00"),
    (b"gAMA", struct.pack(">I", 45455)),
    (b"cHRM", struct.pack(">8I", 31270, 32900, 64000, 33000, 30000, 60000, 15000, 6000)),
    (b"pHYs", struct.pack(">IIB", 2835, 2835, 1)),
    (b"sBIT", b"\x08\x08\x08"),
    (b"tEXt", b"Software\x00a canvas"),
    (b"tIME", struct.pack(">HBBBBB", 2026, 10, 7, 0, 0, 0)),
    (b"bKGD", bytes(6)),
)
"""The uncompressed ancillary chunks a canvas encoder may write, each accepted."""


def test_check_png_refuses_each_bad_body_and_accepts_a_canvas_png() -> None:
    for label, body in BAD_PNGS.items():
        with pytest.raises(video.VideoError) as exc:
            video.check_png(body, WIDTH, HEIGHT)
        assert exc.value.status == 422 and exc.value.code == "bad_png", label
        assert "bytes" not in exc.value.message or label == "bytes after IEND", label
    for label in ("zTXt bomb", "iCCP bomb", "compressed iTXt bomb", "acTL (animated PNG)"):
        with pytest.raises(video.VideoError, match="a chunk type not of a canvas PNG"):
            video.check_png(BAD_PNGS[label], WIDTH, HEIGHT)
        assert len(BAD_PNGS[label]) < video.MAX_FRAME_BYTES  # under the frame cap: the check alone
    video.check_png(png_bytes(), WIDTH, HEIGHT)
    video.check_png(png_bytes(colour=6), WIDTH, HEIGHT)  # truecolour with alpha (toBlob's)
    # the chunks a canvas PNG may carry: each alone, and all of them with two IDATs
    for kind, data in CANVAS_CHUNKS:
        video.check_png(with_chunk(_chunk(kind, data)), WIDTH, HEIGHT)
    good = png_bytes()
    idat_at = len(video.PNG_SIGNATURE) + 12 + video.IHDR_LENGTH
    idat_len = struct.unpack(">I", good[idat_at : idat_at + 4])[0]
    idat = good[idat_at + 8 : idat_at + 8 + idat_len]
    split = (
        good[:idat_at]
        + b"".join(_chunk(k, d) for k, d in CANVAS_CHUNKS)
        + _chunk(b"IDAT", idat[:100])
        + _chunk(b"IDAT", idat[100:])
        + _chunk(b"IEND", b"")
    )
    video.check_png(split, WIDTH, HEIGHT)
    assert video.frame_height(WIDTH) == HEIGHT
    for width in video.WIDTH_CHOICES:
        assert video.frame_height(width) % 2 == 0 and width % 2 == 0
        assert video.frame_height(width) * video.ASPECT_W == width * video.ASPECT_H


def test_bad_frames_are_422_and_the_session_unchanged(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "copy"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        status, body = create(port, directory, ["pad", "silo"], frames=2)
        assert status == 201, body
        vid = body["video"]["id"]
        for label, bad in BAD_PNGS.items():
            status, parsed = post_frame(port, vid, 0, bad)
            assert status == 422 and parsed["error"] == "bad_png", (label, parsed)
            rec = record(port, vid)
            assert rec["state"] == video.STATE_CAPTURING and rec["received"] == 0, label
            assert rec["bytes"] == 0
        # the session still takes its frames
        assert post_frame(port, vid, 0, frame(0))[0] == 200
        assert post_frame(port, vid, 1, frame(1))[0] == 200
        rec = finish_and_wait(port, vid)
        assert rec["state"] == video.STATE_DONE, rec
        assert Path(rec["path"]).is_file() and Path(rec["path"]).stat().st_size >= FAKE_OUTPUT_BYTES
        assert rec["path"] == str((tmp_path / "work" / rec["file_name"]).resolve())
        assert rec["file_name"] == f"app_{directory.name}_pad-vs-silo_scene.mp4"
        assert not server.video_busy()


# ------------------------------------------------------------------ order, budget, count


def test_frame_order_is_enforced(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "copy"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=3)[1]["video"]["id"]
        status, body = post_frame(port, vid, 1, frame())
        assert status == 409 and body["error"] == "frame_order"
        assert post_frame(port, vid, 0, frame())[0] == 200
        status, body = post_frame(port, vid, 0, frame())
        assert status == 409 and body["error"] == "frame_order"  # repeated
        status, body = post_frame(port, vid, 2, frame())
        assert status == 409 and body["error"] == "frame_order"  # skipped
        assert post_frame(port, vid, 1, frame())[0] == 200
        assert post_frame(port, vid, 2, frame())[0] == 200
        status, body = post_frame(port, vid, 3, frame())
        assert status == 409 and body["error"] == "frames_complete"
        assert record(port, vid)["received"] == 3
        assert finish_and_wait(port, vid)["state"] == video.STATE_DONE


def test_byte_budget_refuses_the_frame_after_draining_it(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    """A frame that would pass the budget is 413 'budget' with the session unchanged; since
    fix round 1 the declared body (within the frame cap) is read and discarded before the
    refusal is answered, so the client sees the 413 and not a reset connection (only a body
    over the cap is refused unread: test_frame_route_by_raw_sockets)."""
    sizes = [len(frame(k)) for k in range(4)]  # the shades compress to slightly different sizes
    budget = sum(sizes[:3]) + 10
    limits = video.Limits(**{**SHORT.__dict__, "byte_budget": budget})
    with serving(
        root,
        basis,
        encoder=fake_encoder(tmp_path, "copy"),
        work_dir=tmp_path / "work",
        limits=limits,
    ) as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=5)[1]["video"]["id"]
        for k in range(3):
            assert post_frame(port, vid, k, frame(k))[0] == 200
        t0 = time.monotonic()
        status, body = post_frame(port, vid, 3, frame(3))
        assert status == 413 and time.monotonic() - t0 < QUICK_S
        assert body["error"] == "budget"
        rec = record(port, vid)
        assert (
            rec["state"] == video.STATE_CAPTURING
            and rec["received"] == 3
            and rec["bytes"] == sum(sizes[:3])
            and rec["budget_bytes"] == budget
        )
        # the budget rule itself, on the session: the same 413 with the body in hand
        session = session_of(server, vid)
        with pytest.raises(video.VideoError) as exc:
            session.accept_frame(3, frame(3))
        assert exc.value.status == 413 and exc.value.code == "budget"
        assert record(port, vid)["received"] == 3
        status, _, body = call(port, "POST", f"/api/videos/{vid}/cancel", {})
        assert status == 200 and body["video"]["state"] == video.STATE_CANCELLED


def test_frame_count_limits(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "copy"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        status, body = create(port, directory, ["pad", "silo"], frames=video.MAX_FRAMES + 1)
        assert status == 422 and body["error"] == "bad_length"
        status, body = create(port, directory, ["pad", "silo"], frames=0)
        assert status == 422 and body["error"] == "bad_length"
        request = {
            "experiment": directory.parent.name,
            "timestamp": directory.name,
            "runs": ["pad"],
            "fps": 10,
            "width": WIDTH,
        }
        status, _, body = call(
            port, "POST", "/api/videos", {**request, "seconds": 180.1}
        )  # 1801 frames
        assert status == 422 and body["error"] == "bad_length"
        status, _, body = call(
            port, "POST", "/api/videos", {**request, "seconds": 1.0, "frames": 10}
        )
        assert status == 422 and body["error"] == "bad_length"
        status, _, body = call(port, "POST", "/api/videos", request)
        assert status == 422 and body["error"] == "bad_length"
        status, _, body = call(port, "POST", "/api/videos", {**request, "seconds": 180.0})
        assert status == 201 and body["video"]["frames"] == 1800
        assert call(port, "POST", f"/api/videos/{body['video']['id']}/cancel", {})[0] == 200
    assert video.frame_count(24, None, 75.0) == 1800
    assert video.frame_count(video.DEFAULT_FPS, None, 90.0) == 1800
    with pytest.raises(video.VideoError):
        video.frame_count(24, None, 75.1)
    with pytest.raises(video.VideoError):
        video.frame_count(24, True, None)
    with pytest.raises(video.VideoError):
        video.frame_count(24, None, float("inf"))


def test_default_rate_keeps_the_gate_pair_within_the_frame_limit() -> None:
    """Fix round 1 (design 4.8, review 06 finding 9: the clip follows the player's default
    rate): at the page's default frame rate the gate pair's natural clip (GATE_PAIR_NATURAL_S)
    fits MAX_FRAMES, so the page never scales it to a faster clock; at 24 fps it would not."""
    assert video.DEFAULT_FPS == 20 and video.DEFAULT_FPS in video.FPS_CHOICES
    assert round(video.DEFAULT_FPS * GATE_PAIR_NATURAL_S) <= video.MAX_FRAMES
    assert round(24 * GATE_PAIR_NATURAL_S) > video.MAX_FRAMES
    assert video.MAX_FRAMES == 1800  # review 04 finding 6 and design 4.8 fix it


def test_refusals_after_the_length_check_drain_the_body(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    """Fix round 1: a refusal of a frame whose Content-Length passed the cap (a wrong index,
    a cancelled session) is answered only after the declared body has been read, so every one
    of DRAIN_POSTS wrong-index posts with a BIG_BODY_BYTES body is a 409 frame_order with no
    socket error (before the fix about 18% of them were connection aborts), and every one
    of CANCELLED_POSTS posts to a cancelled session a 409 video_not_capturing. Fix round 2:
    the header checks run before the session is looked up, so a post to an unknown id (the
    page after a server restart) is a 404 with its body drained too, DRAIN_POSTS of them
    without a socket error (before, about 60% were connection aborts)."""
    big = bytes(BIG_BODY_BYTES)
    # the posts are not frames, so the idle timeout is kept out of the way (the test is about
    # the drain, not the timeouts)
    limits = video.Limits(**{**SHORT.__dict__, "idle_s": 30.0})
    with serving(
        root,
        basis,
        encoder=fake_encoder(tmp_path, "copy"),
        work_dir=tmp_path / "work",
        limits=limits,
    ) as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=3)[1]["video"]["id"]
        status, body = post_frame(port, vid, 0, frame(0))
        assert status == 200, body
        errors: list[str] = []
        statuses: list[tuple[int, Any]] = []
        for _ in range(DRAIN_POSTS):
            try:
                status, body = post_frame(port, vid, 2, big)
            except OSError as exc:
                errors.append(type(exc).__name__)
                continue
            statuses.append((status, body["error"]))
        assert errors == [], errors
        assert statuses == [(409, "frame_order")] * DRAIN_POSTS
        rec = record(port, vid)
        assert rec["received"] == 1 and rec["bytes"] == len(frame(0))
        status, _, body = call(port, "POST", f"/api/videos/{vid}/cancel", {})
        assert status == 200, body
        statuses.clear()
        for _ in range(CANCELLED_POSTS):
            try:
                status, body = post_frame(port, vid, 1, big)
            except OSError as exc:
                errors.append(type(exc).__name__)
                continue
            statuses.append((status, body["error"]))
        assert errors == [], errors
        assert statuses == [(409, "video_not_capturing")] * CANCELLED_POSTS
        assert not server.video_busy()
        statuses.clear()
        for _ in range(DRAIN_POSTS):
            try:
                status, body = post_frame(port, UNKNOWN_ID, 0, big)
            except OSError as exc:
                errors.append(type(exc).__name__)
                continue
            statuses.append((status, body["error"]))
        assert errors == [], errors
        assert statuses == [(404, "not_found")] * DRAIN_POSTS
        assert record(port, vid)["received"] == 1
        # the header checks come first: an unknown id with a wrong media type is 415, over
        # the cap 413 (unread) and the id itself is still never echoed
        status, _, body = call(port, "POST", f"/api/videos/{UNKNOWN_ID}/frames/0", b"x" * 10)
        assert (status, body["error"]) == (415, "unsupported_media_type")
        status, _, body = call(
            port,
            "POST",
            f"/api/videos/{UNKNOWN_ID}/frames/0",
            b"",
            headers={"Content-Length": str(video.MAX_FRAME_BYTES + 1)},
            content_type="image/png",
        )
        assert (status, body["error"]) == (413, "frame_too_large")
        assert UNKNOWN_ID not in json.dumps(body)


def test_finish_and_cancel_take_an_empty_object_only(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    """Fix round 1 (D-SP2-31): POST .../finish and .../cancel accept {} and refuse any key
    with 422 unknown_key, the session unchanged, as POST /api/videos does."""
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "copy"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=1)[1]["video"]["id"]
        assert post_frame(port, vid, 0, frame(0))[0] == 200
        for route in ("finish", "cancel"):
            status, _, body = call(port, "POST", f"/api/videos/{vid}/{route}", {"x": 1})
            assert (status, body["error"]) == (422, "unknown_key"), (route, body)
            assert record(port, vid)["state"] == video.STATE_CAPTURING
        rec = finish_and_wait(port, vid)
        assert rec["state"] == video.STATE_DONE
        vid = create(port, directory, ["pad"], frames=2)[1]["video"]["id"]
        status, _, body = call(port, "POST", f"/api/videos/{vid}/cancel", {"ignored": [1, 2]})
        assert (status, body["error"]) == (422, "unknown_key")
        assert record(port, vid)["state"] == video.STATE_CAPTURING
        status, _, body = call(port, "POST", f"/api/videos/{vid}/cancel", {})
        assert status == 200 and body["video"]["state"] == video.STATE_CANCELLED


# ------------------------------------------------------------------ the frame route's guard


def test_frame_route_by_raw_sockets(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    body = frame()
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "copy"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=2)[1]["video"]["id"]
        own = f"127.0.0.1:{port}".encode()
        path = f"/api/videos/{vid}/frames/0".encode()

        def post(
            headers: bytes, data: bytes = body, target: bytes = path, length: int | None = None
        ) -> bytes:
            n = len(data) if length is None else length
            return (
                b"POST "
                + target
                + b" HTTP/1.1\r\nHost: "
                + own
                + b"\r\n"
                + headers
                + b"Content-Length: "
                + str(n).encode()
                + b"\r\n\r\n"
                + data
            )

        png = b"Content-Type: image/png\r\n"
        cases = [
            ("foreign Origin", post(png + b"Origin: http://127.0.0.1:1\r\n"), 403),
            ("null Origin", post(png + b"Origin: null\r\n"), 403),
            ("cross-site", post(png + b"Sec-Fetch-Site: cross-site\r\n"), 403),
            ("same-site (another port)", post(png + b"Sec-Fetch-Site: same-site\r\n"), 403),
            ("text/plain", post(b"Content-Type: text/plain\r\n"), 415),
            ("no Content-Type (a no-cors post drops it)", post(b""), 415),
            (
                "image/png with a parameter",
                post(b"Content-Type: image/png; charset=binary\r\n"),
                415,
            ),
            ("application/json", post(b"Content-Type: application/json\r\n"), 415),
            ("chunked", post(png + b"Transfer-Encoding: chunked\r\n"), 400),
            ("unknown id", post(png, target=b"/api/videos/AAAAAAAAAAAAAAAAAAAAAA/frames/0"), 404),
            ("id with a bad character", post(png, target=b"/api/videos/a.b/frames/0"), 404),
            ("index not digits", post(png, target=f"/api/videos/{vid}/frames/x".encode()), 404),
            ("index too long", post(png, target=f"/api/videos/{vid}/frames/00000".encode()), 404),
            ("no such sub-route", post(png, target=f"/api/videos/{vid}/frame/0".encode()), 404),
            ("query string", post(png, target=path + b"?x=1"), 400),
            ("same-origin, image/png", post(png + b"Sec-Fetch-Site: same-origin\r\n"), 200),
        ]
        wrong = []
        for label, request, want in cases:
            got = raw_request(port, request)[0]
            if got != want:
                wrong.append(f"{label}: {got} (expected {want})")
        assert not wrong, wrong
        # 4 MiB + 1 announced: 413 at once, no body read
        over = video.MAX_FRAME_BYTES + 1
        t0 = time.monotonic()
        status, answer = raw_request(
            port, post(png, data=b"", target=f"/api/videos/{vid}/frames/1".encode(), length=over)
        )
        assert status == 413 and json.loads(answer)["error"] == "frame_too_large"
        assert time.monotonic() - t0 < QUICK_S
        # the JSON routes keep the JSON rule: a PNG body to finish is 415, to create 415
        status, answer = raw_request(port, post(png, target=f"/api/videos/{vid}/finish".encode()))
        assert status == 415
        status, answer = raw_request(port, post(png, target=b"/api/videos"))
        assert status == 415
        # GET of the record needs the same-origin rule too
        get = (
            b"GET /api/videos/"
            + vid.encode()
            + b" HTTP/1.1\r\nHost: "
            + own
            + b"\r\nSec-Fetch-Site: cross-site\r\n\r\n"
        )
        assert raw_request(port, get)[0] == 403
        get = b"GET /api/videos/" + vid.encode() + b" HTTP/1.1\r\nHost: " + own + b"\r\n\r\n"
        assert raw_request(port, get)[0] == 200
        assert (
            raw_request(port, b"GET /api/videos/nope HTTP/1.1\r\nHost: " + own + b"\r\n\r\n")[0]
            == 404
        )
        rec = record(port, vid)
        assert rec["received"] == 1
        assert call(port, "POST", f"/api/videos/{vid}/cancel", {})[0] == 200


def test_one_connection_carries_an_exports_requests(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    """Fix round 3 (honesty pass 3, the blocker; compliance pass 3 finding 5): the server
    answers HTTP/1.1 and keeps the connection, so an export's frame POSTs, its finish and
    its polls travel on one connection instead of one per frame (Windows' loopback stack
    refused one of about 1,700 new connections now and then, and the page saw a lost
    frame). Here: the create, every frame, the finish and the polls of a whole clip on one
    raw socket, each response HTTP/1.1 with a Content-Length and the socket still open;
    then a 413 (a frame over the cap, answered before its body is read) closes the
    connection with its response, so the unread body is never read as a request."""
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "copy"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        own = f"127.0.0.1:{port}".encode()

        def request(method: bytes, target: bytes, ctype: bytes, data: bytes) -> bytes:
            return (
                method
                + b" "
                + target
                + b" HTTP/1.1\r\nHost: "
                + own
                + b"\r\nContent-Type: "
                + ctype
                + b"\r\nContent-Length: "
                + str(len(data)).encode()
                + b"\r\n\r\n"
                + data
            )

        create_body = json.dumps(
            {
                "experiment": directory.parent.name,
                "timestamp": directory.name,
                "runs": ["pad", "silo"],
                "fps": video.DEFAULT_FPS,
                "width": WIDTH,
                "frames": 3,
            }
        ).encode()
        with socket.create_connection(("127.0.0.1", port), timeout=TIMEOUT_S) as sock:
            sock.sendall(request(b"POST", b"/api/videos", b"application/json", create_body))
            status, body = split_response(read_response(sock))
            assert status == 201, body
            vid = json.loads(body)["video"]["id"].encode()
            for k in range(3):
                sock.sendall(
                    request(
                        b"POST", b"/api/videos/" + vid + b"/frames/%d" % k, b"image/png", frame(k)
                    )
                )
                response = read_response(sock)
                assert response.startswith(b"HTTP/1.1 200 "), response[:80]
                assert json.loads(split_response(response)[1])["received"] == k + 1
            sock.sendall(
                request(b"POST", b"/api/videos/" + vid + b"/finish", b"application/json", b"{}")
            )
            assert split_response(read_response(sock))[0] == 202
            get = b"GET /api/videos/" + vid + b" HTTP/1.1\r\nHost: " + own + b"\r\n\r\n"
            deadline = time.monotonic() + TIMEOUT_S
            while True:
                sock.sendall(get)
                status, body = split_response(read_response(sock))
                assert status == 200
                rec = json.loads(body)["video"]
                if rec["state"] in video.FINAL_STATES:
                    break
                assert time.monotonic() < deadline
                time.sleep(POLL_S)
            assert rec["state"] == video.STATE_DONE and Path(rec["path"]).is_file(), rec
            # the connection is still open: a second create on it is 201
            sock.sendall(request(b"POST", b"/api/videos", b"application/json", create_body))
            status, body = split_response(read_response(sock))
            assert status == 201, body
            vid2 = json.loads(body)["video"]["id"].encode()
            # a 413 answered with the body unread closes the connection
            over = video.MAX_FRAME_BYTES + 1
            sock.sendall(
                b"POST /api/videos/"
                + vid2
                + b"/frames/0 HTTP/1.1\r\nHost: "
                + own
                + b"\r\nContent-Type: image/png\r\nContent-Length: "
                + str(over).encode()
                + b"\r\n\r\n"
            )
            response = read_response(sock)
            assert response.startswith(b"HTTP/1.1 413 "), response[:80]
            assert json.loads(split_response(response)[1])["error"] == "frame_too_large"
            assert sock.recv(65536) == b""  # closed by the server
        assert call(port, "POST", f"/api/videos/{vid2.decode()}/cancel", {})[0] == 200


# ------------------------------------------------------------------ the request rules, the footer


def test_create_request_rules(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "copy"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        good = {
            "experiment": directory.parent.name,
            "timestamp": directory.name,
            "runs": ["pad", "silo"],
            "fps": 24,
            "width": 1280,
            "frames": 3,
        }
        refusals = [
            ({**good, "extra": 1}, 422, "unknown_key"),
            ({**good, "fps": 25}, 422, "bad_fps"),
            ({**good, "fps": "24"}, 422, "bad_fps"),
            ({**good, "fps": True}, 422, "bad_fps"),
            ({**good, "width": 1000}, 422, "bad_width"),
            ({**good, "frames": 3.0}, 422, "bad_length"),
            ({**good, "runs": ["pad", "pad"]}, 422, "bad_runs"),
            ({**good, "runs": ["pad", "silo", "x"]}, 422, "bad_runs"),
            ({**good, "runs": []}, 422, "bad_runs"),
            ({**good, "runs": ["nope"]}, 422, "bad_selection"),
            ({**good, "times": [0.0, 1.0]}, 422, "bad_times"),
            ({**good, "times": [0.0, 2.0, 1.0]}, 422, "bad_times"),
            ({**good, "times": [0.0, "1", 2.0]}, 422, "bad_times"),
            ({**good, "experiment": "nope"}, 404, "not_found"),
            ({**good, "timestamp": "20260101T000000Z"}, 404, "not_found"),
            ({**good, "experiment": 1}, 422, "bad_directory"),
        ]
        for request, want, code in refusals:
            status, _, body = call(port, "POST", "/api/videos", request)
            assert (status, body["error"]) == (want, code), (request, body)
            assert not server.video_busy()
        # fix round 3 (security pass 3): numbers json accepts but float() or round() refuse
        # are the one-line 422, never a 500 (sent as bytes: json.dumps would reformat them)
        big = "1" + "0" * 400
        template = json.dumps({k: v for k, v in good.items() if k != "frames"})
        raw_cases = [
            (template[:-1] + ', "seconds": ' + big + "}", "bad_length"),
            (template[:-1] + ', "seconds": -' + big + "}", "bad_length"),
            (template[:-1] + ', "seconds": 1e308}', "bad_length"),
            (template[:-1] + ', "seconds": 1e400}', "bad_length"),
            (template[:-1] + ', "frames": ' + big + "}", "bad_length"),
            (template[:-1] + ', "frames": 2, "times": [' + big + ", " + big + "]}", "bad_times"),
            (template[:-1] + ', "frames": 2, "times": [0, -' + big + "]}", "bad_times"),
            (template[:-1] + ', "frames": 1, "times": [1e400]}', "bad_times"),
        ]
        for text, code in raw_cases:
            server.last_error = None
            status, _, body = call(port, "POST", "/api/videos", text.encode("ascii"))
            assert (status, body["error"]) == (422, code), (text[-60:], body)
            assert server.last_error is None, text[-60:]
            assert not server.video_busy()
        assert video.check_times([10**15, 10**15], 2) == [1e15, 1e15]
        assert video.frame_count(10, None, 3.04) == 30 and video.frame_count(10, None, 180) == 1800
        with pytest.raises(video.VideoError, match="1 to 1800 frames"):
            video.frame_count(10, None, 0.04)  # rounds to no frame
        status, _, body = call(port, "POST", "/api/videos", {**good, "times": [0.0, 1.5, 2.25]})
        assert status == 201, body
        rec = body["video"]
        assert len(rec["id"]) >= 20 and rec["state"] == video.STATE_CAPTURING
        assert (rec["width"], rec["height"], rec["fps"], rec["frames"]) == (1280, 720, 24, 3)
        assert body["times"] == [0.0, 1.5, 2.25]
        # the footer: the three lines of plots.animation_caveats for the shown runs, the
        # exploratory line first (an app directory); the display-only caveat is the scene
        # page's own footer line on every captured frame, not a second line here (fix round 1)
        runs, metrics = plots.load_animation_runs(directory, ["pad", "silo"])
        config = run_data.read_yaml(directory / run_data.CONFIG_FILE)
        vehicle = config["vehicle"]["name"]
        assert body["footer"] == plots.animation_caveats(runs, vehicle, metrics["label"])
        assert body["footer"][0] == replay.EXPLORATORY_CAVEAT and len(body["footer"]) == 4
        # fix round 2 (honesty review pass 2): 'no sized structural mass', and the penalty
        # clause only when a shown run is a penalty row (none here)
        assert "no sized structural mass for the" in body["footer"][2]
        assert "penalty row" not in body["footer"][2]
        assert not any("display-only" in line for line in body["footer"])
        assert "display-only reconstructions and are not model output" in scene.FOOTER_TEXT
        assert not hasattr(video, "DISPLAY_ONLY_LINE")
        # a second create while this one is open is 409
        status, _, body = call(port, "POST", "/api/videos", good)
        assert status == 409 and body["error"] == "video_busy"
        assert call(port, "POST", f"/api/videos/{rec['id']}/cancel", {})[0] == 200
        # a recorded (not exploratory) directory: four lines, none exploratory
        metrics_path = directory / run_data.METRICS_FILE
        data = json.loads(metrics_path.read_text(encoding="utf-8"))
        data["label"] = None
        metrics_path.write_text(json.dumps(data), encoding="utf-8")
        server.forget_row(directory)
        status, _, body = call(port, "POST", "/api/videos", {**good, "runs": ["pad"]})
        assert status == 201, body
        assert len(body["footer"]) == 3 and replay.EXPLORATORY_CAVEAT not in body["footer"]
        assert "push load" not in body["footer"][1]  # the pad alone: no push
        assert body["video"]["file_name"] == f"app_{directory.name}_pad_scene.mp4"
        assert call(port, "POST", f"/api/videos/{body['video']['id']}/cancel", {})[0] == 200
    assert video.MP4_CRF == plots.MP4_CRF


def test_unparseable_series_in_a_playable_directory_is_422(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    """Fix round 3 (security pass 3, finding 3): a directory whose row is playable (a header
    and a row in each series) but whose pad/timeseries.csv pandas cannot parse, or parses
    with text cells, is 422 no_video with the fixed text (never a 500: ParserError and the
    float conversion are ValueErrors), no session made, the row forgotten; and the scene
    route of the same directory is 422 no_scene with a fixed text that quotes no cell."""
    garbage = root / directory.parent.name / "20260101T000001Z"
    shutil.copytree(directory, garbage)
    (garbage / "pad" / run_data.SERIES_FILE).write_text(
        'a,b\n1,2\n"unterminated\n', encoding="utf-8", newline="\n"
    )
    textual = root / directory.parent.name / "20260101T000002Z"
    shutil.copytree(directory, textual)
    header = (directory / "pad" / run_data.SERIES_FILE).read_text(encoding="utf-8").splitlines()[0]
    cells = ",".join(["x"] * len(header.split(",")))
    (textual / "pad" / run_data.SERIES_FILE).write_text(
        header + "\n" + cells + "\n", encoding="utf-8", newline="\n"
    )
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "copy"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        for folder in (garbage, textual):
            rows = [r for g in call(port, "GET", "/api/results")[2]["groups"] for r in g["rows"]]
            row = next(r for r in rows if r["timestamp"] == folder.name)
            assert row["playable"] is True, row
            server.last_error = None
            status, body = create(port, folder, ["pad", "silo"], frames=2)
            assert (status, body["error"]) == (422, "no_video"), body
            assert body["message"] == "the directory's files cannot be read for a video"
            assert server.last_error is None and not server.video_busy()
            status, _, body = call(
                port, "GET", f"/scene/{folder.parent.name}/{folder.name}/pad,silo"
            )
            assert (status, body["error"]) == (422, "no_scene"), body
            assert body["message"] == "the directory's files cannot be read for a scene"
            assert "x" * 2 not in body["message"] and server.last_error is None
        # the unchanged directory still films
        status, body = create(port, directory, ["pad", "silo"], frames=1)
        assert status == 201, body
        assert call(port, "POST", f"/api/videos/{body['video']['id']}/cancel", {})[0] == 200


def test_the_last_ended_session_stays_readable(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    """Fix round 3 (compliance pass 3, finding 6): the record of a done session is still
    served after the next session is created (the page polls it 500 ms after finish, and a
    second tab's Save can land in between), with its state and path; an older id is 404."""
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "copy"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        first = create(port, directory, ["pad"], frames=1)[1]["video"]["id"]
        assert post_frame(port, first, 0, frame())[0] == 200
        rec_a = finish_and_wait(port, first)
        assert rec_a["state"] == video.STATE_DONE
        second = create(port, directory, ["pad"], frames=1)[1]["video"]["id"]
        status, _, body = call(port, "GET", f"/api/videos/{first}")
        assert status == 200 and body["video"]["state"] == video.STATE_DONE
        assert body["video"]["path"] == rec_a["path"] and Path(rec_a["path"]).is_file()
        assert call(port, "POST", f"/api/videos/{second}/cancel", {})[0] == 200
        third = create(port, directory, ["pad"], frames=1)[1]["video"]["id"]
        assert call(port, "GET", f"/api/videos/{second}")[0] == 200  # the last ended one
        assert call(port, "GET", f"/api/videos/{first}")[0] == 404  # older: gone
        assert call(port, "POST", f"/api/videos/{first}/cancel", {})[0] == 404
        assert call(port, "POST", f"/api/videos/{third}/cancel", {})[0] == 200
        assert not server.video_busy()


def test_form_reports_the_video_block(tmp_path: Path, basis: appform.Basis, root: Path) -> None:
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "copy"), work_dir=tmp_path / "work"
    ) as server:
        info = call(server.port, "GET", "/api/form")[2]["video"]
    assert info["available"] is True and info["reason"] == ""
    assert info["fps_choices"] == list(video.FPS_CHOICES)
    assert info["default_fps"] == video.DEFAULT_FPS == 20  # fix round 1: 24 scaled the gate clip
    assert info["widths"] == [960, 1280, 1920] and info["default_width"] == 1280
    assert info["sizes"] == [[960, 540], [1280, 720], [1920, 1080]]
    assert info["max_frames"] == SHORT.max_frames == 1800 and info["folder"] == str(
        tmp_path / "work"
    )
    with serving(
        root,
        basis,
        encoder=None,
        work_dir=tmp_path / "work",
        video_reason="ffmpeg not found on PATH",
    ) as server:
        info = call(server.port, "GET", "/api/form")[2]["video"]
        status, _, body = call(
            server.port,
            "POST",
            "/api/videos",
            {
                "experiment": "a",
                "timestamp": "b",
                "runs": ["pad"],
                "fps": 24,
                "width": 960,
                "frames": 1,
            },
        )
    assert info["available"] is False and info["reason"] == "ffmpeg not found on PATH"
    assert status == 503 and body["error"] == app.VIDEO_UNAVAILABLE_CODE


# ------------------------------------------------------------------ fake encoders


def test_encoder_that_never_reads_gives_503_then_the_session_fails(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "never_reads"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=50)[1]["video"]["id"]
        session = session_of(server, vid)
        assert session.temp_dir.is_dir()
        statuses = []
        for k in range(8):
            status, body = post_frame(port, vid, k, frame(k))
            statuses.append(status)
            if status != 200:
                break
        # the pipe and the queue fill: a frame waits the room timeout and is 503, or the
        # blocked write has already failed the session (409 with its reason)
        assert statuses[-1] in (503, 409), statuses
        assert statuses.count(200) >= 1
        rec = wait_state(port, vid, (video.STATE_FAILED,), timeout=10.0)
        assert "no frame arrived" in rec["error"] or "took no frame" in rec["error"], rec
        wait_until(lambda: not server.video_busy())
        wait_until(lambda: not session.temp_dir.exists())
        assert session._proc.poll() is not None  # killed
        status, body = post_frame(port, vid, len(statuses), frame())
        assert status == 409 and body["error"] == "video_not_capturing"
        # nothing left behind was noted (fix round 2: a folder the removal could not take,
        # a writer still blocked, are recorded in the error)
        error = record(port, vid)["error"]
        assert "could not be removed" not in error and "still blocked" not in error, error
        # the slot is free: a new session starts (and is cancelled)
        status, body = create(port, directory, ["pad"], frames=2)
        assert status == 201
        second = session_of(server, body["video"]["id"])
        assert call(port, "POST", f"/api/videos/{body['video']['id']}/cancel", {})[0] == 200
    assert not session.temp_dir.exists() and not second.temp_dir.exists()
    assert not list((tmp_path / "work").iterdir())


def test_encoder_that_exits_early_fails_with_its_stderr_tail(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "exit_early"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=2)[1]["video"]["id"]
        session = session_of(server, vid)
        session._proc.wait(TIMEOUT_S)  # the fake has exited before any frame
        k = 0
        while k < 2:
            status = post_frame(port, vid, k, frame(k))[0]
            if status != 200:
                break
            k += 1
        if k == 2:
            status = call(port, "POST", f"/api/videos/{vid}/finish", {})[0]
            assert status in (202, 409)
        rec = wait_state(port, vid, (video.STATE_FAILED,), timeout=10.0)
        assert "boom: the fake encoder refused the input" in rec["error"], rec
        assert rec["path"] is None and not list((tmp_path / "work").iterdir())
        wait_until(lambda: not session.temp_dir.exists())
        assert not server.video_busy()


def test_encoder_that_floods_stderr_does_not_hang(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "flood"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=2)[1]["video"]["id"]
        for k in range(2):
            status, body = post_frame(port, vid, k, frame(k))
            if status != 200:
                break
        else:
            status, _, body = call(port, "POST", f"/api/videos/{vid}/finish", {})
            assert status in (202, 409), body
        t0 = time.monotonic()
        rec = wait_state(port, vid, (video.STATE_FAILED,), timeout=20.0)
        assert time.monotonic() - t0 < 20.0
        assert (
            rec["error"].endswith("END-OF-FLOOD)")
            and len(rec["error"]) < video.STDERR_TAIL_CHARS + 80
        ), rec["error"]
        assert "exited 2" in rec["error"] or "stopped taking" in rec["error"]
        assert not server.video_busy()


def test_encoder_that_floods_stderr_past_the_cap_fails_the_session(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    """Fix round 2 (security pass 2, finding 4): the monitor fails a session whose encoder
    has written more than ``Limits.stderr_max_bytes`` of messages (the flooding fake's 3 MiB
    against a 1 MiB cap here; STDERR_MAX_BYTES, 16 MiB, in production), within a few
    MONITOR_POLL_S, the error naming the size (the tail still kept), the slot freed and the
    folder removed."""
    with serving(
        root,
        basis,
        encoder=fake_encoder(tmp_path, "flood"),
        work_dir=tmp_path / "work",
        limits=STDERR_CAP_LIMITS,
    ) as server:
        port = server.port
        t0 = time.monotonic()
        vid = create(port, directory, ["pad", "silo"], frames=50)[1]["video"]["id"]
        session = session_of(server, vid)
        rec = wait_state(port, vid, (video.STATE_FAILED,), timeout=8 * video.MONITOR_POLL_S + 2.0)
        assert time.monotonic() - t0 < STDERR_CAP_LIMITS.idle_s  # the cap, not the idle timeout
        found = re.match(r"the encoder wrote ([0-9.]+) MiB of messages \(ffmpeg: x+", rec["error"])
        assert found is not None, rec["error"]
        assert float(found.group(1)) > STDERR_CAP_LIMITS.stderr_max_bytes / video.MIB
        wait_until(lambda: not server.video_busy())
        wait_until(lambda: not session.temp_dir.exists())
        assert session._proc.poll() is not None
        status, body = create(port, directory, ["pad"], frames=1)
        assert status == 201
        assert call(port, "POST", f"/api/videos/{body['video']['id']}/cancel", {})[0] == 200
    assert video.STDERR_MAX_BYTES == 16 * video.MIB and video.DEFAULT_LIMITS.stderr_max_bytes == (
        video.STDERR_MAX_BYTES
    )
    assert FLOOD_BYTES < video.STDERR_MAX_BYTES  # the shipped flood test stays under the cap


def test_encoder_that_never_finishes_fails_on_the_finish_timeout(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    """Fix round 3 (security pass 3, finding 4): the third lifecycle timeout. An encoder that
    takes every frame and then never exits (the slow_finish fake: stdin to EOF, then a 60 s
    sleep) fails the session within ``Limits.finish_s`` of the finish, its process tree
    killed, the folder removed, the slot free, nothing in the working directory; and a
    second such session left FINISHING when the server exits is cancelled by the server's
    close within the thread-join budget, with nothing left behind."""
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "slow_finish"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=2)[1]["video"]["id"]
        session = session_of(server, vid)
        for k in range(2):
            assert post_frame(port, vid, k, frame(k))[0] == 200
        status, _, body = call(port, "POST", f"/api/videos/{vid}/finish", {})
        assert status == 202 and body["video"]["state"] == video.STATE_FINISHING, body
        t0 = time.monotonic()
        budget = SHORT.finish_s + video.TERMINATE_WAIT_S + 1.0
        rec = wait_state(port, vid, (video.STATE_FAILED,), timeout=budget)
        assert time.monotonic() - t0 < budget
        assert f"did not finish within {SHORT.finish_s:g} s" in rec["error"], rec
        assert rec["path"] is None
        wait_until(lambda: session._proc.poll() is not None, timeout=video.TERMINATE_WAIT_S + 1.0)
        wait_until(lambda: not session.temp_dir.exists())
        wait_until(lambda: not server.video_busy())
        assert not list((tmp_path / "work").iterdir())
        error = record(port, vid)["error"]
        assert "could not be removed" not in error and "still blocked" not in error, error
        # a second session, finishing when the serving context exits
        vid = create(port, directory, ["pad", "silo"], frames=1)[1]["video"]["id"]
        second = session_of(server, vid)
        assert post_frame(port, vid, 0, frame())[0] == 200
        assert call(port, "POST", f"/api/videos/{vid}/finish", {})[0] == 202
        wait_until(lambda: second._proc.stdin is None or second._proc.stdin.closed)
        assert second.state == video.STATE_FINISHING
        t_close = time.monotonic()
    assert time.monotonic() - t_close < 2 * video.THREAD_JOIN_S
    assert second.state == video.STATE_CANCELLED
    assert second._proc.poll() is not None
    assert not second.temp_dir.exists()
    assert second.error is None, second.error
    assert not list((tmp_path / "work").iterdir())


def test_wrapper_encoder_is_killed_with_its_child_and_the_session_fails(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    """Fix round 2 (security pass 2, finding 1): the encoder resolved on PATH is a wrapper
    (a .bat here, an sh script elsewhere; a chocolatey or scoop shim behaves the same) whose
    child is the program that never reads. Before the fix the kill reached the wrapper
    alone: the child kept the pipe, the writer stayed blocked in flush, stdin.close from the
    monitor blocked on the pipe's lock, and the failure was never published (the slot held,
    frames 503, the server's close waiting on the child). Now the failed state is published
    before the kill, the kill takes the whole tree (a Job Object, or the process group), the
    folder goes, a new session starts and the server's close returns promptly."""
    encoder = wrapper_encoder(tmp_path, "never_reads")
    pid_file = tmp_path / "never_reads.pid"
    with serving(root, basis, encoder=encoder, work_dir=tmp_path / "work") as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=50)[1]["video"]["id"]
        session = session_of(server, vid)
        wait_until(lambda: pid_file.is_file() and pid_file.read_text(encoding="utf-8") != "")
        inner = int(pid_file.read_text(encoding="utf-8"))
        assert inner != session._proc.pid and process_alive(inner)
        statuses = []
        for k in range(12):
            status, _ = post_frame(port, vid, k, frame(k))
            statuses.append(status)
            if status != 200:
                break
        assert statuses[-1] in (503, 409) and statuses.count(200) >= 1, statuses
        budget = SHORT.write_block_s + video.TERMINATE_WAIT_S + 1.0
        rec = wait_state(port, vid, (video.STATE_FAILED,), timeout=budget)
        assert "no frame arrived" in rec["error"] or "took no frame" in rec["error"], rec
        assert not server.video_busy()
        wait_until(lambda: not process_alive(inner), timeout=video.TERMINATE_WAIT_S)
        assert session._proc.poll() is not None
        wait_until(lambda: not session.temp_dir.exists())
        error = record(port, vid)["error"]
        assert "could not be removed" not in error and "still blocked" not in error, error
        status, body = create(port, directory, ["pad"], frames=2)
        assert status == 201, body
        second = session_of(server, body["video"]["id"])
        assert call(port, "POST", f"/api/videos/{body['video']['id']}/cancel", {})[0] == 200
        t_close = time.monotonic()
    assert time.monotonic() - t_close < 2 * video.THREAD_JOIN_S
    assert not session.temp_dir.exists() and not second.temp_dir.exists()
    assert not process_alive(inner)
    assert not list((tmp_path / "work").iterdir())


def test_cancel_at_any_moment_leaves_no_temporary_folder(
    tmp_path: Path, root: Path, directory: Path
) -> None:
    """Fix round 2 (security pass 2, finding 2): sessions on the never-reading fake, each
    cancelled a different time after its start (the probe left a folder in 4 of 16 such
    cancels: Windows released the killed child's handle on the stderr file after
    proc.wait() returned, and the one rmtree failed silently). The removal now retries, so
    every session's folder is gone when cancel returns and nothing is noted in its
    error."""
    encoder = fake_encoder(tmp_path, "never_reads")
    work = tmp_path / "work"
    work.mkdir()
    for delay in CANCEL_RACE_DELAYS_S:
        session = video.VideoSession(
            session_spec(directory), encoder, work, repo_root=root.parent, results_root=root
        )
        try:
            assert session.accept_frame(0, frame(0)) == 1
            time.sleep(delay)
        finally:
            session.cancel()
        assert session.state == video.STATE_CANCELLED
        assert session._proc.poll() is not None, delay
        assert not session.temp_dir.exists(), delay
        assert session.error is None, (delay, session.error)
    assert not list(work.iterdir())


def test_a_start_that_fails_after_the_folder_is_made_removes_it(
    tmp_path: Path, root: Path, directory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fix round 2 (security pass 2, finding 2): a VideoSession whose start fails after
    its temporary folder was made (the stderr file cannot be opened, the encoder cannot
    start, a thread cannot start) raises and leaves no folder; a started process is
    killed."""
    made: list[Path] = []
    original_mkdtemp = tempfile.mkdtemp

    def recording_mkdtemp(*args: Any, **kwargs: Any) -> str:
        path = original_mkdtemp(*args, **kwargs)
        made.append(Path(path))
        return path

    monkeypatch.setattr(video.tempfile, "mkdtemp", recording_mkdtemp)
    work = tmp_path / "work"
    work.mkdir()
    spec = session_spec(directory)
    kwargs: dict[str, Any] = {"repo_root": root.parent, "results_root": root, "limits": SHORT}
    original_open = video.open_stderr_file

    def refusing_open(path: Path) -> Any:
        raise PermissionError(errno.EACCES, "denied", str(path))

    monkeypatch.setattr(video, "open_stderr_file", refusing_open)
    with pytest.raises(video.VideoError) as exc:
        video.VideoSession(spec, fake_encoder(tmp_path, "copy"), work, **kwargs)
    assert (exc.value.status, exc.value.code) == (503, "temp_failed")
    assert "denied" not in exc.value.message and "PermissionError" in exc.value.message
    monkeypatch.setattr(video, "open_stderr_file", original_open)
    with pytest.raises(video.VideoError) as exc:
        video.VideoSession(spec, video.Encoder((str(tmp_path / "missing.exe"),)), work, **kwargs)
    assert (exc.value.status, exc.value.code) == (503, "encoder_failed")
    # the monitor thread cannot start: the writer (started) is woken and the process killed
    original_thread = threading.Thread

    class RefusingMonitor(original_thread):  # type: ignore[misc,valid-type]
        def start(self) -> None:
            if str(self.name).startswith("launchsim-video-monitor"):
                raise RuntimeError("no thread")
            super().start()

    monkeypatch.setattr(video.threading, "Thread", RefusingMonitor)
    with pytest.raises(RuntimeError, match="no thread"):
        video.VideoSession(spec, fake_encoder(tmp_path, "never_reads"), work, **kwargs)
    monkeypatch.setattr(video.threading, "Thread", original_thread)
    assert len(made) == 3
    wait_until(lambda: not any(p.exists() for p in made))
    assert not list(work.iterdir())


def test_an_abandoned_session_frees_the_slot(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    limits = video.Limits(**{**SHORT.__dict__, "idle_s": 0.5})
    with serving(
        root,
        basis,
        encoder=fake_encoder(tmp_path, "copy"),
        work_dir=tmp_path / "work",
        limits=limits,
    ) as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=3)[1]["video"]["id"]
        session = session_of(server, vid)
        assert post_frame(port, vid, 0, frame())[0] == 200
        assert server.video_busy()
        rec = wait_state(port, vid, (video.STATE_FAILED,), timeout=10.0)
        assert "no frame arrived for 0.5 s" in rec["error"]
        wait_until(lambda: not server.video_busy())
        wait_until(lambda: not session.temp_dir.exists())
        assert not list((tmp_path / "work").iterdir())
        # a launch may start again (the stub runner is None here, so only the check matters)
        assert create(port, directory, ["pad"], frames=1)[0] == 201


def test_cancel_discards_the_partial_file(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "copy"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=4)[1]["video"]["id"]
        session = session_of(server, vid)
        for k in range(2):
            assert post_frame(port, vid, k, frame(k))[0] == 200
        status, _, body = call(port, "POST", f"/api/videos/{vid}/finish", {})
        assert status == 409 and body["error"] == "frames_missing"
        status, _, body = call(port, "POST", f"/api/videos/{vid}/cancel", {})
        assert status == 200 and body["video"]["state"] == video.STATE_CANCELLED
        wait_until(lambda: not session.temp_dir.exists())
        assert session._proc.poll() is not None
        assert not list((tmp_path / "work").iterdir())
        assert post_frame(port, vid, 2, frame())[0] == 409
        status, _, body = call(port, "POST", f"/api/videos/{vid}/cancel", {})
        assert status == 409 and body["error"] == "video_ended"
        assert record(port, vid)["state"] == video.STATE_CANCELLED
        assert not server.video_busy()


def test_reservation_keeps_an_existing_file_and_takes_minus_2(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    stem = video.output_stem("app", directory.name, ["pad", "silo"])
    existing = work / f"{stem}.mp4"
    existing.write_bytes(b"keep me")
    with serving(root, basis, encoder=fake_encoder(tmp_path, "copy"), work_dir=work) as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=1)[1]["video"]["id"]
        assert post_frame(port, vid, 0, frame())[0] == 200
        rec = finish_and_wait(port, vid)
        assert rec["state"] == video.STATE_DONE
        assert Path(rec["path"]) == (work / f"{stem}-2.mp4").resolve()
        assert existing.read_bytes() == b"keep me"
        assert Path(rec["path"]).stat().st_size >= FAKE_OUTPUT_BYTES
        # a third takes -3
        vid = create(port, directory, ["pad", "silo"], frames=1)[1]["video"]["id"]
        assert post_frame(port, vid, 0, frame())[0] == 200
        rec = finish_and_wait(port, vid)
        assert Path(rec["path"]) == (work / f"{stem}-3.mp4").resolve()
    assert sorted(p.name for p in work.iterdir()) == [
        f"{stem}-2.mp4",
        f"{stem}-3.mp4",
        f"{stem}.mp4",
    ]
    # the rule itself: an empty exclusive file, -2 on a clash
    folder = tmp_path / "plain"
    folder.mkdir()
    first = video.reserve_output(folder, "x_scene", directory)
    assert first == (folder / "x_scene.mp4").resolve() and first.stat().st_size == 0
    assert (
        video.reserve_output(folder, "x_scene", directory) == (folder / "x_scene-2.mp4").resolve()
    )


def _refusing_replace(original: Callable[..., Any], error: OSError) -> Callable[..., Any]:
    """An os.replace that raises ``error`` for the session's temporary MP4 and delegates
    every other call to ``original``."""

    def replace(src: Any, dst: Any, *args: Any, **kwargs: Any) -> Any:
        if Path(src).name == video.TEMP_OUTPUT:
            raise error
        return original(src, dst, *args, **kwargs)

    return replace


def test_cross_volume_move_falls_back_to_a_copy(
    tmp_path: Path,
    basis: appform.Basis,
    root: Path,
    directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fix round 1: os.replace refusing the move across volumes (errno EXDEV, or Windows'
    ERROR_NOT_SAME_DEVICE 17, which a server started from a repository on another drive
    than the system temporary folder hits on every export) is answered with a copy onto the
    reservation: the session done, the file holding the fake encoder's output, the temporary
    folder removed. Any other OSError still fails the session and removes the reservation."""
    original = os.replace
    monkeypatch.setattr(
        video.os, "replace", _refusing_replace(original, OSError(errno.EXDEV, "cross-device link"))
    )
    sessions: list[video.VideoSession] = []
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "copy"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=2)[1]["video"]["id"]
        session = session_of(server, vid)
        sessions.append(session)
        total = 0
        for k in range(2):
            assert post_frame(port, vid, k, frame(k))[0] == 200
            total += len(frame(k))
        rec = finish_and_wait(port, vid)
        assert rec["state"] == video.STATE_DONE, rec
        data = Path(rec["path"]).read_bytes()
        assert data[:12] == b"\x00\x00\x00\x18ftypisom" and data.endswith(str(total).encode())
        assert len(data) == FAKE_OUTPUT_BYTES + len(str(total))
        wait_until(lambda: not session.temp_dir.exists())
        assert Path(rec["path"]).parent == (tmp_path / "work").resolve()
        # Windows' own error object: winerror 17 (its errno is EXDEV too)
        monkeypatch.setattr(
            video.os,
            "replace",
            _refusing_replace(
                original, OSError(errno.EXDEV, "cannot move to a different disk drive", None, 17)
            ),
        )
        vid = create(port, directory, ["pad", "silo"], frames=1)[1]["video"]["id"]
        sessions.append(session_of(server, vid))
        assert post_frame(port, vid, 0, frame())[0] == 200
        rec = finish_and_wait(port, vid)
        assert rec["state"] == video.STATE_DONE and rec["path"].endswith("-2.mp4"), rec
        assert Path(rec["path"]).stat().st_size == FAKE_OUTPUT_BYTES + len(str(len(frame())))
        # another error is not a cross-volume move: the session fails, the reservation goes
        denied = PermissionError(errno.EACCES, "denied")
        monkeypatch.setattr(video.os, "replace", _refusing_replace(original, denied))
        vid = create(port, directory, ["pad", "silo"], frames=1)[1]["video"]["id"]
        sessions.append(session_of(server, vid))
        assert post_frame(port, vid, 0, frame())[0] == 200
        rec = finish_and_wait(port, vid)
        assert rec["state"] == video.STATE_FAILED and "could not be saved" in rec["error"], rec
        assert "PermissionError" in rec["error"]
    assert len(sessions) == 3 and not any(s.temp_dir.exists() for s in sessions)
    assert sorted(p.name for p in (tmp_path / "work").iterdir()) == [
        f"app_{directory.name}_pad-vs-silo_scene-2.mp4",
        f"app_{directory.name}_pad-vs-silo_scene.mp4",
    ]
    # the helpers themselves
    assert video.cross_volume_error(OSError(errno.EXDEV, "x"))
    assert video.cross_volume_error(OSError(0, "x", None, 17)) if sys.platform == "win32" else True
    assert not video.cross_volume_error(OSError(errno.EACCES, "x"))
    src, dst = tmp_path / "src.bin", tmp_path / "dst.bin"
    src.write_bytes(b"abc" * 1000)
    dst.write_bytes(b"")
    monkeypatch.setattr(
        video.os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError(errno.EXDEV, "x"))
    )
    video.place_output(src, dst)
    assert not src.exists() and dst.read_bytes() == b"abc" * 1000
    src.write_bytes(b"z")
    monkeypatch.setattr(
        video.os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError(errno.EACCES, "x"))
    )
    with pytest.raises(PermissionError):
        video.place_output(src, dst)
    assert src.exists() and dst.read_bytes() == b"abc" * 1000


def test_output_is_refused_inside_a_results_tree(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    inside = root / "videos"  # under the results root
    with serving(root, basis, encoder=fake_encoder(tmp_path, "copy"), work_dir=inside) as server:
        info = call(server.port, "GET", "/api/form")[2]["video"]
        assert info["available"] is False and "inside a results tree" in info["reason"]
        status, body = create(server.port, directory, ["pad"], frames=1)
        assert status == 503 and body["error"] == app.VIDEO_UNAVAILABLE_CODE
    named = tmp_path / "results" / "clips"  # any folder named results
    assert video.folder_reason(named, tmp_path / "elsewhere") is not None
    assert video.folder_reason(tmp_path / "work", root) is None
    named.mkdir(parents=True)
    with pytest.raises(video.VideoOutputError):
        video.reserve_output(named, "x_scene", directory)
    with pytest.raises(run_data.RunDataError):
        video.reserve_output(root / "app", "x_scene", directory)
    assert not list(named.iterdir())


def test_a_launch_and_a_video_never_run_together(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from test_app_server import StubRunner
    finally:
        sys.path.pop(0)
    runner = StubRunner(block=True)
    form = appform.preset_form(basis, "silo_cold")
    with serving(
        root,
        basis,
        encoder=fake_encoder(tmp_path, "copy"),
        work_dir=tmp_path / "work",
        runner=runner,
    ) as server:
        port = server.port
        assert server.start_launch(form)[0] == 202
        assert runner.made.wait(TIMEOUT_S)
        status, body = create(port, directory, ["pad", "silo"], frames=2)
        assert status == 409 and body["error"] == "launch_running"
        runner.gate.set()
        wait_until(lambda: server.job_snapshot()["state"] != app.JOB_RUNNING)
        status, body = create(port, directory, ["pad", "silo"], frames=2)
        assert status == 201
        vid = body["video"]["id"]
        status, result = server.start_launch(form)
        assert status == 409 and result["error"] == "video_busy", result
        assert runner.calls == 1
        assert call(port, "POST", f"/api/videos/{vid}/cancel", {})[0] == 200
        runner.gate.set()
        status, result = server.start_launch(form)
        assert status == 202
        wait_until(lambda: server.job_snapshot()["state"] != app.JOB_RUNNING)


def test_server_exit_closes_an_open_session(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    with serving(
        root, basis, encoder=fake_encoder(tmp_path, "never_reads"), work_dir=tmp_path / "work"
    ) as server:
        port = server.port
        vid = create(port, directory, ["pad", "silo"], frames=5)[1]["video"]["id"]
        session = session_of(server, vid)
        assert post_frame(port, vid, 0, frame())[0] == 200
        proc = session._proc
        t_close = time.monotonic()
    assert time.monotonic() - t_close < 2 * video.THREAD_JOIN_S
    assert session.state == video.STATE_CANCELLED
    assert proc.poll() is not None
    assert not session.temp_dir.exists()
    assert session.error is None, session.error
    assert not list((tmp_path / "work").iterdir())


# ------------------------------------------------------------------ the ffmpeg lookup


LOOKUP_PROBE = """
import json, os, shutil, sys
from pathlib import Path
from launchsim import video
work = Path(sys.argv[1]); other = Path(sys.argv[2]); empty = Path(sys.argv[3])
bare = shutil.which("ffmpeg")  # '.\\\\ffmpeg.BAT' here: relative, resolved in this process
out = {"bare": None if bare is None else str(Path(bare).resolve())}
cases = (("cwd+other", [work, other]), ("other", [other]), ("cwd", [work]),
         ("empty", [empty]), ("relative", [Path(".")]))
for label, entries in cases:
    os.environ["PATH"] = os.pathsep.join(str(e) for e in entries)
    found = video.find_ffmpeg(work, work / "nope", work / "nope2", probe=None)
    command = None if found.encoder is None else list(found.encoder.command)
    out[label] = {"command": command, "reason": found.reason, "rejected": list(found.rejected)}
print(json.dumps(out))
"""


def test_ffmpeg_lookup_rejects_a_candidate_in_the_working_directory(tmp_path: Path) -> None:
    """Review 04 finding 5: run from a working directory that holds an ffmpeg.bat, with
    NoDefaultCurrentDirectoryInExePath cleared, so Windows' bare lookup would take it;
    find_ffmpeg rejects it (the PATH entry that is the working directory), takes another
    entry's ffmpeg, finds nothing when there is no other, and ignores a relative entry."""
    work = tmp_path / "work"
    other = tmp_path / "other"
    empty = tmp_path / "empty"
    for folder in (work, other, empty):
        folder.mkdir()
    ext = ".bat" if sys.platform == "win32" else ""
    for folder in (work, other):
        planted = folder / f"ffmpeg{ext}"
        planted.write_text("@echo off\r\n" if ext else "#!/bin/sh\n", encoding="utf-8")
        planted.chmod(0o755)
    # os.environ upper-cases the names on Windows: compare without case
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper() != "NoDefaultCurrentDirectoryInExePath".upper()
    }
    env["PYTHONPATH"] = str(REPO / "src")
    proc = subprocess.run(
        [sys.executable, "-c", LOOKUP_PROBE, str(work), str(other), str(empty)],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    planted_in_work = str((work / f"ffmpeg{ext}").resolve())
    if sys.platform == "win32":
        # the trap: the standard lookup takes the file in the working directory (PATH is the
        # parent's here, which holds the real ffmpeg or none; the cwd is searched first)
        assert out["bare"] is not None and Path(out["bare"]) == Path(planted_in_work)
    assert out["cwd+other"]["command"] == [str((other / f"ffmpeg{ext}").resolve())]
    assert out["cwd+other"]["rejected"] == [planted_in_work]
    assert out["other"]["command"] == [str((other / f"ffmpeg{ext}").resolve())]
    assert out["cwd"]["command"] is None and out["cwd"]["rejected"] == [planted_in_work]
    assert "not used" in out["cwd"]["reason"]
    assert out["empty"]["command"] is None and out["empty"]["rejected"] == []
    assert out["relative"]["command"] is None and out["relative"]["rejected"] == []
    # the repository and the results root are rejected too
    found = video.find_ffmpeg(
        tmp_path / "elsewhere", other, tmp_path / "r", environ={"PATH": str(other)}, probe=None
    )
    assert found.encoder is None and found.rejected == (str((other / f"ffmpeg{ext}").resolve()),)
    found = video.find_ffmpeg(
        tmp_path / "elsewhere",
        tmp_path / "r",
        other.parent,
        environ={"PATH": str(other)},
        probe=None,
    )
    assert found.encoder is None and len(found.rejected) == 1
    # the probe's failure is the reason
    found = video.find_ffmpeg(
        tmp_path / "x",
        tmp_path / "y",
        tmp_path / "z",
        environ={"PATH": str(other)},
        probe=lambda c: (_ for _ in ()).throw(
            video.VideoError(503, "no_h264_encoder", "ffmpeg lists no H.264 encoder")
        ),
    )
    assert found.encoder is None and "no H.264 encoder" in found.reason
    assert video.path_entries(
        {"PATH": os.pathsep.join([".", "", str(other), str(other), " "])}
    ) == [other]


def test_probe_codec_on_fakes(tmp_path: Path) -> None:
    script = tmp_path / "probe.py"
    script.write_text(
        "import sys\n"
        "mode = sys.argv[1]\n"
        "if mode == 'x264': print(' V....D libx264              libx264 H.264 (codec h264)')\n"
        "elif mode == 'mf': print(' V....D h264_mf     H264 via MediaFoundation (codec h264)')\n"
        "elif mode == 'none': print(' V....D libx265              x265 (codec hevc)')\n"
        "elif mode == 'fail': sys.exit(3)\n",
        encoding="utf-8",
    )
    run = lambda mode: video.probe_codec((sys.executable, str(script), mode))  # noqa: E731
    assert run("x264") == "libx264" and run("mf") == "h264"
    with pytest.raises(video.VideoError, match=r"no H\.264 encoder"):
        run("none")
    with pytest.raises(video.VideoError, match="exited 3"):
        run("fail")
    with pytest.raises(video.VideoError, match="could not be run"):
        video.probe_codec((str(tmp_path / "missing.exe"),))


def test_ffmpeg_command_is_the_fixed_list() -> None:
    enc = video.Encoder(("C:/x/ffmpeg.exe",), "libx264")
    out = Path("D:/t/scene.mp4")
    assert video.ffmpeg_command(enc, 24, 48, out) == [
        "C:/x/ffmpeg.exe",
        "-hide_banner",
        "-xerror",  # fix round 1: a frame that does not decode fails the encode, never a short clip
        "-loglevel",
        "error",
        "-nostats",
        "-f",
        "image2pipe",
        "-c:v",
        "png",
        "-framerate",
        "24",
        "-i",
        "pipe:0",
        "-frames:v",
        "48",
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        str(video.MP4_CRF),
        "-movflags",
        "+faststart",
        "-n",
        str(out),
    ]
    assert video.output_stem("silo_offload_2d", "20261003T112934Z", ["pad", "silo_cold_s1"]) == (
        "silo_offload_2d_20261003T112934Z_pad-vs-silo_cold_s1_scene"
    )


# ------------------------------------------------------------------ real canvas PNGs (slow)


EDGE_CANDIDATES = (
    Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
)
NODE = shutil.which("node")
CANVAS_DRIVER = """
// headless Edge over the DevTools protocol (this build's --dump-dom writes nothing from a
// subprocess): argv[2] the browser, argv[3] a profile folder; prints one line per size,
// "<w>x<h>:<base64 of the canvas's toBlob PNG>".
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const sleep = ms => new Promise(r => setTimeout(r, ms));
const EXPR = `(async () => {
  const sizes = [[960, 540], [1280, 720], [1920, 1080]];
  const lines = [];
  for (const [w, h] of sizes) {
    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    const ctx = cv.getContext("2d");
    const g = ctx.createLinearGradient(0, 0, w, h);
    g.addColorStop(0, "#102030"); g.addColorStop(1, "#f0e0d0");
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#ffffff"; ctx.font = "20px sans-serif";
    for (let i = 0; i < 40; i++) ctx.fillText("caveat line " + i + " lorem ipsum", 10, 30 + i * 12);
    const blob = await new Promise(r => cv.toBlob(r, "image/png"));
    const buf = new Uint8Array(await blob.arrayBuffer());
    let s = ""; for (let i = 0; i < buf.length; i++) s += String.fromCharCode(buf[i]);
    lines.push(w + "x" + h + ":" + btoa(s));
  }
  return lines.join("\\\\n");
})()`;
(async () => {
  const [edge, profile] = process.argv.slice(2);
  const proc = spawn(edge, ["--headless=new", "--disable-gpu", "--no-first-run",
    "--no-default-browser-check", "--disable-background-networking", "--disable-component-update",
    "--remote-debugging-port=0", "--user-data-dir=" + profile, "about:blank"], { stdio: "ignore" });
  let port = "";
  const portFile = path.join(profile, "DevToolsActivePort");
  for (let i = 0; i < 300 && !port; i++) {
    try { port = fs.readFileSync(portFile, "utf8").split("\\n")[0].trim(); }
    catch (e) { /* not yet */ }
    if (!port) await sleep(100);
  }
  if (!port) throw new Error("no DevTools port");
  const version = await (await fetch("http://127.0.0.1:" + port + "/json/version")).json();
  const ws = new WebSocket(version.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    ws.addEventListener("open", res);
    ws.addEventListener("error", rej);
  });
  let seq = 0;
  const pending = new Map();
  ws.addEventListener("message", ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); p(m); }
  });
  const send = (method, params, sessionId) => new Promise(res => {
    const id = ++seq;
    pending.set(id, res);
    ws.send(JSON.stringify({ id, method, params: params || {}, sessionId }));
  });
  const { result: { targetId } } = await send("Target.createTarget", { url: "about:blank" });
  const attach = await send("Target.attachToTarget", { targetId, flatten: true });
  const sessionId = attach.result.sessionId;
  await send("Runtime.enable", {}, sessionId);
  const params = { expression: EXPR, returnByValue: true, awaitPromise: true };
  const r = await send("Runtime.evaluate", params, sessionId);
  if (!r.result || r.result.exceptionDetails) {
    throw new Error("evaluate failed: " + JSON.stringify(r).slice(0, 500));
  }
  process.stdout.write(r.result.result.value + "\\n");
  await send("Browser.close");
  await sleep(300);
  try { proc.kill(); } catch (e) { /* gone */ }
})().catch(e => { process.stderr.write(String(e) + "\\n"); process.exit(1); });
"""


@pytest.mark.slow
def test_real_canvas_pngs_pass_the_header_check(tmp_path: Path) -> None:
    """Fix round 3: a real canvas toBlob PNG at 960 x 540, 1280 x 720 and 1920 x 1080
    (headless Edge over the DevTools protocol, drawing a gradient and text, the frame's
    shape) passes check_png with its size, so the chunk whitelist refuses nothing a canvas
    encoder writes; skipped where Edge or node is not installed."""
    edge = next((p for p in EDGE_CANDIDATES if p.is_file()), None)
    if edge is None or NODE is None:
        pytest.skip("headless Edge and node are needed")
    driver = tmp_path / "canvas_driver.js"
    driver.write_text(CANVAS_DRIVER, encoding="utf-8", newline="\n")
    profile = tmp_path / "profile"
    profile.mkdir()
    out = subprocess.run(
        [NODE, str(driver), str(edge), str(profile)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )
    assert out.returncode == 0, out.stderr[-600:]
    sizes = {}
    for line in out.stdout.strip().splitlines():
        label, _, b64 = line.partition(":")
        w, h = (int(v) for v in label.split("x"))
        sizes[(w, h)] = base64.b64decode(b64)
    assert set(sizes) == {(w, video.frame_height(w)) for w in video.WIDTH_CHOICES}
    for (w, h), body in sizes.items():
        assert body.startswith(video.PNG_SIGNATURE) and len(body) < video.MAX_FRAME_BYTES
        video.check_png(body, w, h)
        with pytest.raises(video.VideoError):
            video.check_png(body, w, h + 2)


# ------------------------------------------------------------------ the real encoder (slow)


REAL_W, REAL_H = 1280, 720
REAL_FRAMES = 48
"""The slow tier's clip: 2.0 s at 24 fps of REAL_W x REAL_H frames."""


def bar_frame(k: int, width: int = REAL_W, height: int = REAL_H) -> bytes:
    """Frame ``k`` of the slow tier: a moving bar on a gradient (real motion for the
    encoder), a valid PNG by hand."""
    rows = []
    x0 = (k * 20) % (width - 40)
    for y in range(height):
        row = bytearray()
        shade = (y * 255) // height
        for x in range(width):
            if x0 <= x < x0 + 40:
                row += b"\xff\x40\x10"
            else:
                row += bytes((shade, 200 - shade // 2, 90))
        rows.append(b"\x00" + bytes(row))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        video.PNG_SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(b"".join(rows), 1))
        + _chunk(b"IEND", b"")
    )


def bad_idat_frame(width: int = REAL_W, height: int = REAL_H) -> bytes:
    """A frame whose header is the session's (the header check passes it) and whose IDAT
    is random bytes that do not inflate: what ffmpeg's decoder refuses."""
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        video.PNG_SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", os.urandom(4096))
        + _chunk(b"IEND", b"")
    )


def real_encoder(work: Path, root: Path) -> video.Encoder:
    """The installed ffmpeg as the server resolves it, or a skip."""
    lookup = video.find_ffmpeg(work, REPO, root)
    if lookup.encoder is None:
        pytest.skip(f"ffmpeg not found: {lookup.reason}")
    return lookup.encoder


def real_clip(
    server: app.AppServer, directory: Path, frames: list[bytes]
) -> tuple[list[tuple[int, Any]], dict[str, Any]]:
    """Create a 24 fps REAL_W-wide session of ``len(frames)`` frames, post them in order
    until one is refused, then finish (when every frame was taken) and wait for the final
    state: (the statuses posted, the final record)."""
    port = server.port
    request = {
        "experiment": directory.parent.name,
        "timestamp": directory.name,
        "runs": ["pad", "silo"],
        "fps": 24,
        "width": REAL_W,
        "frames": len(frames),
    }
    status, _, body = call(port, "POST", "/api/videos", request)
    assert status == 201 and body["video"]["frames"] == len(frames), body
    vid = body["video"]["id"]
    posted: list[tuple[int, Any]] = []
    for k, data in enumerate(frames):
        posted.append(post_frame(port, vid, k, data))
        if posted[-1][0] != 200:
            break
    if len(posted) == len(frames) and posted[-1][0] == 200:
        status, _, body = call(port, "POST", f"/api/videos/{vid}/finish", {})
        assert status in (202, 409), body
    return posted, wait_state(port, vid, video.FINAL_STATES, timeout=120.0)


def probe_frames(encoder: video.Encoder, path: Path) -> dict[str, Any] | None:
    """ffprobe's stream entry of ``path`` (frames counted) when ffprobe sits beside the
    encoder, else None."""
    ffprobe = shutil.which("ffprobe", path=str(Path(encoder.command[0]).parent))
    if ffprobe is None:
        return None
    out = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_read_frames,width,height,r_frame_rate",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)["streams"][0]


def assert_real_clip(encoder: video.Encoder, rec: dict[str, Any], work: Path, name: str) -> None:
    """``rec`` is a done session whose file sits in ``work`` under ``name``, a non-empty MP4
    ('ftyp') of REAL_FRAMES frames by ffprobe when present."""
    assert rec["state"] == video.STATE_DONE, rec
    path = Path(rec["path"])
    assert path.parent == work.resolve() and path.name == name
    data = path.read_bytes()
    assert len(data) > 2000 and data[4:8] == b"ftyp"
    stream = probe_frames(encoder, path)
    if stream is not None:
        assert int(stream["nb_read_frames"]) == REAL_FRAMES
        assert (stream["width"], stream["height"], stream["r_frame_rate"]) == (
            REAL_W,
            REAL_H,
            "24/1",
        )


@pytest.mark.slow
def test_real_ffmpeg_encodes_48_frames(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    """48 synthesised 1280 x 720 frames (a moving bar on a gradient, so the encoder has real
    motion) through the routes with the installed ffmpeg: done, an MP4 whose frame count
    is 48 by ffprobe when present, else a non-empty file with an MP4 'ftyp' header and the
    size of a real clip."""
    work = tmp_path / "work"
    encoder = real_encoder(work, root)
    with serving(root, basis, encoder=encoder, work_dir=work, limits=video.DEFAULT_LIMITS) as srv:
        posted, rec = real_clip(srv, directory, [bar_frame(k) for k in range(REAL_FRAMES)])
    assert [s for s, _ in posted] == [200] * REAL_FRAMES
    assert_real_clip(encoder, rec, work, f"app_{directory.name}_pad-vs-silo_scene.mp4")


def other_volume_alias(folder: Path) -> Path:
    """``folder`` addressed through its drive's administrative share
    (\\\\localhost\\C$\\...): another volume to MoveFileExW, the same bytes on disk, so a
    cross-volume save is exercised without writing outside ``folder``. Skips off Windows,
    when the alias is unreachable, or when os.replace onto it is not refused as a
    cross-volume move here."""
    if sys.platform != "win32" or len(folder.drive) != 2 or folder.drive[1] != ":":
        pytest.skip("the administrative-share alias needs a Windows drive letter")
    alias = Path(f"\\\\localhost\\{folder.drive[0]}$" + str(folder)[2:])
    if not alias.is_dir():
        pytest.skip(f"{alias} is not reachable")
    probe = folder / "alias-probe.bin"
    probe.write_bytes(b"x")
    try:
        os.replace(probe, alias / "alias-probe-moved.bin")
    except OSError as exc:
        if not video.cross_volume_error(exc):
            raise
    else:
        (folder / "alias-probe-moved.bin").unlink()
        pytest.skip("os.replace onto the alias is not a cross-volume move here")
    probe.unlink()
    return alias


@pytest.mark.slow
def test_real_ffmpeg_saves_across_volumes(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    """Fix round 1 (the blocker): the same 48-frame clip saved through a working directory
    on another volume than the system temporary folder (``other_volume_alias`` of a folder
    under tmp_path): the session done, the file on the alias with 48 frames, the temporary
    file gone."""
    plain = tmp_path / "work"
    plain.mkdir()
    work = other_volume_alias(plain)
    encoder = real_encoder(work, root)
    with serving(root, basis, encoder=encoder, work_dir=work, limits=video.DEFAULT_LIMITS) as srv:
        posted, rec = real_clip(srv, directory, [bar_frame(k) for k in range(REAL_FRAMES)])
        session = session_of(srv, rec["id"])
    assert [s for s, _ in posted] == [200] * REAL_FRAMES
    name = f"app_{directory.name}_pad-vs-silo_scene.mp4"
    assert_real_clip(encoder, rec, work, name)
    assert (plain / name).is_file() and (plain / name).stat().st_size > 2000  # the same bytes
    assert not session.temp_dir.exists()  # the session's own folder (fix round 2), never %TEMP%


@pytest.mark.slow
def test_real_ffmpeg_fails_a_frame_whose_idat_does_not_inflate(
    tmp_path: Path, basis: appform.Basis, root: Path, directory: Path
) -> None:
    """Fix round 1: a header-valid frame whose pixel data does not inflate (what the header
    check cannot see) ends the encode with -xerror: the session failed with ffmpeg's reason
    in its error, no file in the working directory, the temporary folder removed; before
    the fix ffmpeg dropped the frame, exited 0 and a shorter clip was reported done."""
    work = tmp_path / "work"
    encoder = real_encoder(work, root)
    frames = [bar_frame(0), bar_frame(1), bad_idat_frame(), bar_frame(3)]
    with serving(root, basis, encoder=encoder, work_dir=work, limits=video.DEFAULT_LIMITS) as srv:
        posted, rec = real_clip(srv, directory, frames)
        session = session_of(srv, rec["id"])
        assert posted[0][0] == 200 and posted[1][0] == 200, posted
        assert rec["state"] == video.STATE_FAILED, rec
        assert "the encoder exited" in rec["error"] and "exited 0" not in rec["error"], rec
        assert "ffmpeg:" in rec["error"], rec["error"]
        # the decoder's own line survives ffmpeg 8's thread messages in the 600-character tail
        assert "inflate returned error" in rec["error"] and "dec:png" in rec["error"], rec["error"]
        assert rec["path"] is None
        wait_until(lambda: not srv.video_busy())
        wait_until(lambda: not session.temp_dir.exists())
    assert not list(work.iterdir())
    assert not session.temp_dir.exists()
