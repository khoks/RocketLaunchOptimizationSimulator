"""The app's MP4 export (SP2 step A6v; design section 4.8, D-SP2-30; security review 04
findings 1, 2, 5, 6 and 8; delivery review 05 finding 8; design review 06 finding 9;
honesty review 02 finding 9). I/O: subprocesses, pipes, threads and files; the physics
modules never import it.

The app page asks the framed scene for one PNG per frame (``captureFrame``) and posts each
to the server, which pipes it to ffmpeg as it arrives; the server never decodes an upload
(Pillow is a dev dependency only). What this module provides:

- the ffmpeg lookup at server start (``find_ffmpeg``): shutil.which over the absolute
  entries of PATH only, each asked for its own folder (so Windows never prepends the
  working directory, review 04 finding 5), a candidate in or under the working directory,
  the repository or the results root rejected, the first survivor probed once for an
  H.264 encoder (libx264, else the generic h264);
- the request rules (``check_fps``, ``check_width``, ``frame_height``, ``frame_count``,
  ``check_times``): fps from FPS_CHOICES, width from WIDTH_CHOICES, the height from the
  composite's fixed 16:9 aspect (both even), 1 to MAX_FRAMES frames, a BYTE_BUDGET per
  session, MAX_FRAME_BYTES per frame;
- the PNG header check every frame body passes BEFORE it is piped (``check_png``): the
  8-byte signature, IHDR as the first chunk with exactly the session's width and height,
  bit depth 8, colour type 2 or 6, no interlace, every later chunk of a type a canvas
  encoder writes (PNG_CANVAS_CHUNKS: no zTXt, iCCP or compressed iTXt, whose zlib streams
  the decoder would inflate with no cap; fix round 3), the ancillary chunks within
  PNG_ANCILLARY_MAX_BYTES, IEND as the last chunk and the body ending there; otherwise the
  frame is refused (422) and the session is unchanged;
- ``VideoSession``: one at a time (the server holds the slot), an id from
  secrets.token_urlsafe looked up in memory and never part of a path, frames accepted in
  order (409 otherwise), one writer thread with a queue of QUEUE_FRAMES frames (a frame
  POST waits at most ``Limits.room_timeout_s`` for room, 503 otherwise), a monitor thread
  that kills the encoder, removes the temporary folder and frees the slot when no frame
  arrives for ``idle_s``, a pipe write blocks for ``write_block_s`` or the finish is not
  complete in ``finish_s`` (the session failed with the last STDERR_TAIL_CHARS of ffmpeg's
  stderr, which goes to a file in the session's temporary folder, outside the repository
  and the results root); the same clean-up on ``close`` (the server stopping);
- the encoder's argument list (``ffmpeg_command``): a forced PNG decoder on a pipe,
  exactly the session's frame count and ``-xerror``, so a frame whose pixel data does not
  decode (the header check sees only the chunk layout) ends the encode with a non-zero
  exit and the session fails with ffmpeg's reason, instead of a shorter clip reported done
  (fix round 1);
- the output reservation (``reserve_output``): on finish the final name
  <experiment>_<timestamp>_<left>-vs-<right>_scene.mp4 is reserved in the server's working
  directory with an exclusive create, -2, -3, ... on a clash (as results_io.make_run_dir
  does), never inside a results tree (run_data's output rule), then the temporary file is
  moved onto it (``place_output``: os.replace, or a copy when the temporary folder, the
  system's, lies on another volume than the working directory, as it does for a server
  started from a repository on another drive; fix round 1); a failed or cancelled session
  removes its reservation.

The caveat footer of every frame is the server's (app.video_footer: plots.animation_caveats
of the shown runs, with the exploratory line for an app run); the display-only caveat is the
scene page's own footer line (scene.FOOTER_TEXT), which every captured frame carries, so
the server does not repeat it (D-SP2-23: one source per caveat; fix round 1).

Fix round 2 (the encoder's lifecycle): a failed session publishes its failed state BEFORE
the encoder is killed, so a poll and the slot never wait on a kill; the kill takes the whole
process tree (Windows: a Job Object with KILL_ON_JOB_CLOSE the process is assigned to at its
start, ``process_tree_handle``; POSIX: its own session and os.killpg), so a wrapper on PATH
(a chocolatey or scoop shim, a .bat) whose child holds the pipe cannot keep the writer
blocked and the slot held; the pipe is closed by the writer thread alone (never from another
thread while a write may be in flight); ``cancel`` and ``close`` return within bounded waits
even when the writer is still blocked (recorded in the session's error); the temporary
folder's removal is retried for TEMP_REMOVE_RETRY_S (Windows releases a just-killed child's
handle on the stderr file a moment after the process has ended) and a folder still there is
recorded in the error and reported to the server, a start that fails after the folder was
made removes it, and the monitor fails a session whose encoder has written more than
``Limits.stderr_max_bytes`` of messages.

Every number is a named module constant; the server passes a ``Limits`` so tests can
shorten the timeouts, and an ``Encoder`` whose command may be a fake encoder.
"""

from __future__ import annotations

import contextlib
import errno
import math
import os
import queue
import re
import secrets
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from launchsim import run_data
from launchsim.results_io import MAX_DIR_SUFFIX

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

# ------------------------------------------------------------------ constants

FORMAT_MP4 = "mp4"
FORMATS: tuple[str, ...] = (FORMAT_MP4,)
"""The one video format (D-SP2-30: MP4 through ffmpeg; no GIF from the app)."""
FPS_CHOICES: tuple[int, ...] = (10, 15, 20, 24, 30)
"""Frame rates a session may be created with [frames per second]."""
DEFAULT_FPS = 20
"""The page's default frame rate. 20 rather than 24 (fix round 1): design 4.8 and review 06
finding 9 have the clip follow the player's default rate, and the natural clip of the gate
pair (pad beside silo_cold_s1, 86.4 wall s under the Auto law) is 1,727 frames at 20 fps,
within MAX_FRAMES, and 2,072 at 24 fps, over it, where the page would scale the clip to a
faster clock."""
WIDTH_CHOICES: tuple[int, ...] = (960, 1280, 1920)
"""Frame widths a session may be created with [px]; the height follows the aspect."""
DEFAULT_WIDTH = 1280
"""The page's default frame width [px]."""
ASPECT_W, ASPECT_H = 16, 9
"""The composite's fixed aspect (``frame_height``): 960 x 540, 1280 x 720, 1920 x 1080,
every side even, as libx264 with yuv420p needs (review 05 finding 8)."""
MIN_FRAMES, MAX_FRAMES = 1, 1800
"""Frames per session, inclusive (review 04 finding 6 and design 4.8 fix the 1,800: 90 s
at DEFAULT_FPS, 75 s at 24 fps)."""
BYTE_BUDGET = 512 * 1024 * 1024
"""The most frame bytes one session accepts [bytes] (512 MiB; review 04 finding 6)."""
MAX_FRAME_BYTES = 4 * 1024 * 1024
"""The largest frame body [bytes] (4 MiB); a longer Content-Length is 413 before any byte
is read. A drawn 1280 x 720 frame is about 100 to 300 kB."""
ID_BYTES = 16
"""Random bytes of a session id (secrets.token_urlsafe: 22 URL-safe characters)."""
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")
"""What a session id in a path may look like (``fullmatch``) before it is compared."""
FRAME_INDEX_PATTERN = re.compile(r"[0-9]{1,4}")
"""A frame index in a path (``fullmatch``): ASCII digits, at most four (MAX_FRAMES has
four)."""
MAX_TIME_INT = 10**15
"""The largest integer a scene time may be given as [s] (``check_times``; fix round 3): an
int beyond it is refused before float() would overflow on hundreds of digits."""
QUEUE_FRAMES = 2
"""Frames the writer thread's queue holds (review 04 finding 5)."""
ROOM_TIMEOUT_S = 10.0
"""How long [s] a frame POST waits for room in the queue (503 afterwards)."""
IDLE_S = 30.0
"""No frame for this long [s] fails a capturing session (an abandoned tab)."""
WRITE_BLOCK_S = 30.0
"""A pipe write blocked for this long [s] fails the session (a stalled encoder)."""
FINISH_S = 120.0
"""A finish not complete in this long [s] fails the session."""
MONITOR_POLL_S = 0.25
"""How often [s] the monitor thread checks the three timeouts."""
TERMINATE_WAIT_S = 5.0
"""How long [s] a kill waits for the encoder process to end before giving up on it."""
THREAD_JOIN_S = 5.0
"""How long [s] ``close`` waits for the writer and monitor threads."""
WRITER_WAIT_S = 1.0
"""How long [s] a tear-down waits for a writer thread blocked in a pipe write after the
kill: the write fails at once when the tree kill took every reader of the pipe; a writer
still blocked after this (a reader the kill could not reach) is abandoned and recorded in
the session's error (fix round 2), never waited on by a request or the server's stop."""
TEMP_REMOVE_RETRY_S = 3.0
"""How long [s] the temporary folder's removal is retried, every TEMP_REMOVE_POLL_S, before
the folder is recorded as left: Windows releases a just-killed child's handle on the stderr
file a moment after the process has ended (fix round 2)."""
TEMP_REMOVE_POLL_S = 0.1
"""The interval [s] of the removal retries."""
STDERR_MAX_BYTES = 16 * 1024 * 1024
"""The most the encoder may write to its stderr file [bytes] (16 MiB) before the monitor
fails the session: the real ffmpeg at -loglevel error writes little; a misbehaving or
substituted encoder on PATH must not fill the disk (fix round 2)."""
MIB = 1024 * 1024
"""Bytes in a MiB, for the size in that failure's message."""
STDERR_TAIL_CHARS = 600
"""Characters of ffmpeg's stderr kept in a failed session's message: enough (fix round 1)
for the decoder's own line ('inflate returned error -3') to survive the thread and task
messages ffmpeg 8 writes after it (about 400 characters)."""
MP4_CRF = 20
"""x264 constant rate factor of the clip: plots.MP4_CRF's value (the animation's), kept in
step by a test so the two MP4 writers match."""
H264_ENCODER = "libx264"
H264_CODEC = "h264"
"""The encoder asked for: libx264 when the build lists it, else the generic codec name
(ffmpeg then picks any H.264 encoder it has)."""
FFMPEG_NAME = "ffmpeg"
REJECTED_NOTE = (
    " (a candidate in the working directory, the repository or the results root is not used)"
)
"""Added to the not-found reason when the lookup rejected a candidate."""
PROBE_TIMEOUT_S = 30.0
"""How long [s] the one ``ffmpeg -encoders`` probe at server start may take."""
ENCODER_LINE_PATTERN = re.compile(r"^\s*V\S*\s+(\S+)\s+(.*)$")
"""One line of ``ffmpeg -encoders``: the video flag column, the name, the description."""
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_CHUNK_HEAD = 8
PNG_CHUNK_CRC = 4
IHDR_LENGTH = 13
PNG_BIT_DEPTH = 8
PNG_COLOUR_TYPES: tuple[int, ...] = (2, 6)
"""Truecolour and truecolour with alpha: what a canvas's toBlob PNG is."""
PNG_NO_INTERLACE = 0
PNG_MAX_CHUNK = 2**31 - 1
"""The PNG specification's largest chunk length."""
PNG_CANVAS_CHUNKS: frozenset[bytes] = frozenset(
    (b"IDAT", b"IEND", b"sRGB", b"gAMA", b"cHRM", b"pHYs", b"sBIT", b"tEXt", b"tIME", b"bKGD")
)
"""The chunk types a frame may carry after IHDR (fix round 3, security pass 3): the image
data, the end, and the uncompressed ancillary chunks a canvas encoder may write. Any other
type is refused before the frame is piped: in particular zTXt, iCCP and a compressed iTXt
hold zlib streams the decoder inflates with no cap (a 2 MB body inflating to 2 GiB passed
the layout check and cost ffmpeg 3 GiB of commit), and the animated-PNG chunks (acTL, fcTL,
fdAT) and unknown types are nothing a canvas writes."""
PNG_ANCILLARY_MAX_BYTES = 64 * 1024
"""The most bytes [bytes] the ancillary chunks of one frame may hold together (64 KiB; a
canvas PNG carries a few dozen at most)."""
TEMP_PREFIX = "launchsim-video-"
STDERR_FILE = "ffmpeg-stderr.txt"
TEMP_OUTPUT = "scene.mp4"
OUTPUT_SUFFIX = ".mp4"
OUTPUT_TAIL = "_scene"
RUNS_JOIN = "-vs-"
"""The output name: <experiment>_<timestamp>_<left>-vs-<right>_scene.mp4."""
MAX_OUTPUT_SUFFIX = MAX_DIR_SUFFIX
"""Clash suffixes tried (-2 to -1000), as results_io.make_run_dir does."""
CROSS_VOLUME_WINERROR = 17
"""ERROR_NOT_SAME_DEVICE: Windows' os.replace (MoveFileExW without MOVEFILE_COPY_ALLOWED)
across volumes; POSIX raises errno.EXDEV."""
COPY_CHUNK_BYTES = 1024 * 1024
"""Chunk size [bytes] of the cross-volume copy (``place_output``)."""

STATE_CAPTURING = "capturing"
STATE_FINISHING = "finishing"
STATE_DONE = "done"
STATE_FAILED = "failed"
STATE_CANCELLED = "cancelled"
OPEN_STATES: tuple[str, ...] = (STATE_CAPTURING, STATE_FINISHING)
"""States in which the session holds the server's one video slot."""
FINAL_STATES: tuple[str, ...] = (STATE_DONE, STATE_FAILED, STATE_CANCELLED)

HTTP_CONFLICT = 409
HTTP_PAYLOAD_TOO_LARGE = 413
HTTP_UNPROCESSABLE = 422
HTTP_UNAVAILABLE = 503
HTTP_INTERNAL = 500
"""The statuses a VideoError carries (the server maps them to its Refused)."""


# ------------------------------------------------------------------ errors and settings


class VideoError(Exception):
    """A refusal of the video routes: the HTTP ``status``, a short ``code`` and a one-line
    ``message`` that never echoes a request's bytes."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class VideoOutputError(run_data.RunDataError):
    """The output path rule refused the reserved name (inside a results tree)."""


@dataclass(frozen=True)
class Limits:
    """The session's limits; the server's defaults are the module constants, and tests
    shorten the timeouts through them."""

    max_frames: int = MAX_FRAMES
    byte_budget: int = BYTE_BUDGET
    max_frame_bytes: int = MAX_FRAME_BYTES
    queue_frames: int = QUEUE_FRAMES
    room_timeout_s: float = ROOM_TIMEOUT_S
    idle_s: float = IDLE_S
    write_block_s: float = WRITE_BLOCK_S
    finish_s: float = FINISH_S
    stderr_max_bytes: int = STDERR_MAX_BYTES


DEFAULT_LIMITS = Limits()


@dataclass(frozen=True)
class Encoder:
    """The resolved encoder: ``command`` is the absolute path of ffmpeg alone in
    production (tests pass an interpreter and a fake script); ``codec`` the -c:v value
    (H264_ENCODER or H264_CODEC); ``display`` what the start line prints."""

    command: tuple[str, ...]
    codec: str = H264_ENCODER

    @property
    def display(self) -> str:
        """The command for the start line (one path in production)."""
        return " ".join(self.command)


@dataclass(frozen=True)
class Lookup:
    """``find_ffmpeg``'s result: the encoder, or None with the reason; the candidates
    rejected (their folders were the working directory, the repository or the results
    root, or under one of them)."""

    encoder: Encoder | None
    reason: str
    rejected: tuple[str, ...] = ()


# ------------------------------------------------------------------ the ffmpeg lookup


def path_entries(environ: Mapping[str, str] | None = None) -> list[Path]:
    """The absolute entries of PATH, in order, duplicates and relative entries ('.', an
    empty entry) dropped. ``environ`` defaults to os.environ."""
    env = os.environ if environ is None else environ
    out: list[Path] = []
    for raw in env.get("PATH", "").split(os.pathsep):
        text = raw.strip().strip('"')
        if not text:
            continue
        entry = Path(text)
        if entry.is_absolute() and entry not in out:
            out.append(entry)
    return out


def in_or_under(path: Path, folders: Sequence[Path]) -> Path | None:
    """The first of ``folders`` that ``path`` equals or lies under (resolved), else None."""
    resolved = path.resolve()
    for folder in folders:
        try:
            if resolved.is_relative_to(folder.resolve()):
                return folder
        except OSError:
            continue
    return None


def probe_codec(command: Sequence[str], timeout_s: float = PROBE_TIMEOUT_S) -> str:
    """Run ``command -hide_banner -encoders`` once and return H264_ENCODER when the build
    lists libx264, else H264_CODEC when any encoder of codec h264 is listed. Raises
    VideoError (503) when the program cannot run, times out, exits non-zero or has no
    H.264 encoder."""
    try:
        proc = subprocess.run(
            [*command, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VideoError(
            HTTP_UNAVAILABLE,
            "ffmpeg_probe_failed",
            f"ffmpeg could not be run: {type(exc).__name__}",
        ) from exc
    if proc.returncode != 0:
        raise VideoError(
            HTTP_UNAVAILABLE, "ffmpeg_probe_failed", f"ffmpeg -encoders exited {proc.returncode}"
        )
    names: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        found = ENCODER_LINE_PATTERN.match(line)
        if found:
            names[found.group(1)] = found.group(2)
    if H264_ENCODER in names:
        return H264_ENCODER
    if any(f"(codec {H264_CODEC})" in text or name == H264_CODEC for name, text in names.items()):
        return H264_CODEC
    raise VideoError(HTTP_UNAVAILABLE, "no_h264_encoder", "ffmpeg lists no H.264 encoder")


def find_ffmpeg(
    work_dir: Path,
    repo_root: Path,
    results_root: Path,
    environ: Mapping[str, str] | None = None,
    probe: Callable[[Sequence[str]], str] | None = probe_codec,
) -> Lookup:
    """Resolve ffmpeg once at server start (review 04 finding 5): for each absolute PATH
    entry, in order, shutil.which of ``<entry>/ffmpeg`` (a command with a directory part is
    looked up in that folder alone, with PATHEXT on Windows, and the working directory is
    never prepended); a hit whose resolved path is in or under ``work_dir``, ``repo_root``
    or ``results_root`` is rejected and the search goes on; the first survivor is probed
    (``probe``: None skips the probe and takes H264_ENCODER) and returned as an Encoder
    with its absolute path. Without a hit the reason says so."""
    folders = (Path(work_dir), Path(repo_root), Path(results_root))
    rejected: list[str] = []
    for entry in path_entries(environ):
        hit = shutil.which(str(entry / FFMPEG_NAME))
        if hit is None:
            continue
        resolved = Path(hit).resolve()
        if in_or_under(resolved, folders) is not None:
            rejected.append(str(resolved))
            continue
        command = (str(resolved),)
        try:
            codec = H264_ENCODER if probe is None else probe(command)
        except VideoError as exc:
            return Lookup(None, f"{resolved}: {exc.message}", tuple(rejected))
        return Lookup(Encoder(command, codec), "", tuple(rejected))
    where = "" if not rejected else REJECTED_NOTE
    return Lookup(None, f"ffmpeg not found on PATH{where}", tuple(rejected))


def folder_reason(work_dir: Path, results_root: Path) -> str | None:
    """Why videos cannot be written from ``work_dir``: it is inside a results tree (any
    folder named results, or the results root), else None (run_data's output rule)."""
    if run_data.results_ancestors(work_dir) or run_data.is_inside(work_dir, results_root):
        return (
            "the server's working directory is inside a results tree, where nothing is "
            "written by hand: start the app from another folder to save videos"
        )
    return None


# ------------------------------------------------------------------ the request rules


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def check_fps(value: Any) -> int:
    """``value`` as a frame rate of FPS_CHOICES (an int, not a bool); VideoError 422."""
    if not _is_int(value) or value not in FPS_CHOICES:
        raise VideoError(
            HTTP_UNPROCESSABLE, "bad_fps", f"fps must be one of {', '.join(map(str, FPS_CHOICES))}"
        )
    return int(value)


def check_width(value: Any) -> int:
    """``value`` as a frame width of WIDTH_CHOICES [px]; VideoError 422."""
    if not _is_int(value) or value not in WIDTH_CHOICES:
        raise VideoError(
            HTTP_UNPROCESSABLE,
            "bad_width",
            f"width must be one of {', '.join(map(str, WIDTH_CHOICES))}",
        )
    return int(value)


def frame_height(width: int) -> int:
    """The frame height [px] of ``width`` at the composite's aspect (ASPECT_W:ASPECT_H);
    both sides even for every width of WIDTH_CHOICES."""
    return width * ASPECT_H // ASPECT_W


def frame_count(fps: int, frames: Any, seconds: Any, limits: Limits = DEFAULT_LIMITS) -> int:
    """The session's frame count from exactly one of ``frames`` (an int) or ``seconds`` (a
    finite positive number: round(fps x seconds)), MIN_FRAMES to ``limits.max_frames``;
    VideoError 422 otherwise."""
    too_long = VideoError(
        HTTP_UNPROCESSABLE, "bad_length", f"a clip has {MIN_FRAMES} to {limits.max_frames} frames"
    )
    if (frames is None) == (seconds is None):
        raise VideoError(HTTP_UNPROCESSABLE, "bad_length", "give frames or seconds, not both")
    if frames is not None:
        if not _is_int(frames):
            raise VideoError(HTTP_UNPROCESSABLE, "bad_length", "frames must be an integer")
        n = int(frames)
    else:
        if isinstance(seconds, bool) or not isinstance(seconds, int | float):
            raise VideoError(HTTP_UNPROCESSABLE, "bad_length", "seconds must be a number")
        # fix round 3: an int json accepts but float() refuses (hundreds of digits) is over
        # the frame limit before it is converted; fps x seconds is checked finite before
        # round(), which refuses an infinite float
        if _is_int(seconds) and not -limits.max_frames <= seconds <= limits.max_frames:
            raise too_long
        span = float(seconds)
        if not (span > 0.0) or span == float("inf"):
            raise VideoError(HTTP_UNPROCESSABLE, "bad_length", "seconds must be positive")
        total = float(fps) * span
        if not math.isfinite(total):
            raise too_long
        n = round(total)
    if not MIN_FRAMES <= n <= limits.max_frames:
        raise too_long
    return n


def check_times(value: Any, frames: int) -> list[float] | None:
    """``value`` (optional: None gives None) as the scene times of the clip's frames: a
    list of exactly ``frames`` finite numbers, non-decreasing; VideoError 422 otherwise.
    The server records them (the rate law lives in the scene page, which computed them)."""
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != frames:
        raise VideoError(
            HTTP_UNPROCESSABLE,
            "bad_times",
            f"times must list the scene time of each of the {frames} frames",
        )
    out: list[float] = []
    last = -float("inf")
    not_finite = VideoError(
        HTTP_UNPROCESSABLE, "bad_times", "times must be finite and non-decreasing"
    )
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int | float):
            raise VideoError(HTTP_UNPROCESSABLE, "bad_times", "every time must be a number")
        # fix round 3: an int of hundreds of digits (json accepts it) is refused as not
        # finite instead of overflowing float()
        if _is_int(item) and abs(item) > MAX_TIME_INT:
            raise not_finite
        t = float(item)
        if not math.isfinite(t) or t < last:
            raise not_finite
        out.append(t)
        last = t
    return out


def check_runs(value: Any, max_runs: int) -> list[str]:
    """``value`` as 1 to ``max_runs`` distinct run names (strings; their membership in the
    directory is the server's check); VideoError 422 otherwise."""
    if (
        not isinstance(value, list)
        or not 1 <= len(value) <= max_runs
        or not all(isinstance(v, str) and v for v in value)
        or len(set(value)) != len(value)
    ):
        raise VideoError(
            HTTP_UNPROCESSABLE, "bad_runs", f"runs must name 1 to {max_runs} distinct runs"
        )
    return [str(v) for v in value]


# ------------------------------------------------------------------ the PNG header check


def _refuse_png(reason: str) -> VideoError:
    return VideoError(
        HTTP_UNPROCESSABLE, "bad_png", f"the frame is not a PNG of the session: {reason}"
    )


def check_png(body: bytes, width: int, height: int) -> None:
    """Check ``body`` BEFORE it is piped (review 04 finding 6): the PNG signature; IHDR as
    the first chunk, 13 bytes, with exactly ``width`` x ``height``, bit depth
    PNG_BIT_DEPTH, a colour type of PNG_COLOUR_TYPES, no interlace; every chunk's length
    within the body; every later chunk of a type in PNG_CANVAS_CHUNKS (fix round 3: no
    compressed ancillary chunk, no animation chunk, no unknown type), the ancillary ones
    within PNG_ANCILLARY_MAX_BYTES together; IEND the last chunk and the body ending with
    it. Chunk CRCs are not checked (ffmpeg's decoder does). Raises VideoError (422) with a
    fixed reason."""
    n = len(body)
    if n < len(PNG_SIGNATURE) + PNG_CHUNK_HEAD or body[: len(PNG_SIGNATURE)] != PNG_SIGNATURE:
        raise _refuse_png("no PNG signature")
    pos = len(PNG_SIGNATURE)
    first = True
    ancillary = 0
    while True:
        if pos + PNG_CHUNK_HEAD > n:
            raise _refuse_png("truncated before a chunk head")
        length, kind = struct.unpack(">I4s", body[pos : pos + PNG_CHUNK_HEAD])
        if length > PNG_MAX_CHUNK:
            raise _refuse_png("a chunk length is over the PNG limit")
        data_at = pos + PNG_CHUNK_HEAD
        end = data_at + length + PNG_CHUNK_CRC
        if end > n:
            raise _refuse_png("truncated inside a chunk")
        if first:
            if kind != b"IHDR" or length != IHDR_LENGTH:
                raise _refuse_png("IHDR is not the first chunk")
            w, h, depth, colour, _compression, _filter, interlace = struct.unpack(
                ">IIBBBBB", body[data_at : data_at + IHDR_LENGTH]
            )
            if (w, h) != (width, height):
                raise _refuse_png(f"its size is not {width} x {height}")
            if depth != PNG_BIT_DEPTH or colour not in PNG_COLOUR_TYPES:
                raise _refuse_png("its bit depth or colour type is not a canvas PNG's")
            if interlace != PNG_NO_INTERLACE:
                raise _refuse_png("it is interlaced")
            first = False
        elif kind == b"IEND":
            if length != 0:
                raise _refuse_png("IEND carries data")
            if end != n:
                raise _refuse_png("bytes follow IEND")
            return
        elif kind not in PNG_CANVAS_CHUNKS:
            raise _refuse_png("a chunk type not of a canvas PNG")
        elif kind != b"IDAT":
            ancillary += length
            if ancillary > PNG_ANCILLARY_MAX_BYTES:
                raise _refuse_png("its ancillary chunks are over the limit")
        pos = end


# ------------------------------------------------------------------ the output name


def output_stem(experiment: str, timestamp: str, runs: Sequence[str]) -> str:
    """<experiment>_<timestamp>_<left>-vs-<right>_scene (one run: its name alone), from
    names the server's own listing validated."""
    return f"{experiment}_{timestamp}_{RUNS_JOIN.join(runs)}{OUTPUT_TAIL}"


def reserve_output(folder: Path, stem: str, run_dir: Path) -> Path:
    """Reserve <folder>/<stem>.mp4 with an exclusive create (an empty file), trying
    <stem>-2.mp4, <stem>-3.mp4, ... up to MAX_OUTPUT_SUFFIX on a clash, as
    results_io.make_run_dir does; each candidate passes run_data's output rule first
    (never inside a results tree: VideoOutputError). Returns the reserved path (absolute).
    Raises FileExistsError when every suffix is taken."""
    for n in range(1, MAX_OUTPUT_SUFFIX + 1):
        name = f"{stem}{OUTPUT_SUFFIX}" if n == 1 else f"{stem}-{n}{OUTPUT_SUFFIX}"
        path = Path(folder) / name
        run_data.check_outside_results(path, run_dir, what="video", error=VideoOutputError)
        try:
            with path.open(
                "xb"
            ):  # an exclusive create of an empty bytes file (no encoding= applies)
                pass
        except FileExistsError:
            continue
        return path.resolve()
    raise FileExistsError(f"more than {MAX_OUTPUT_SUFFIX} videos named {stem} in {folder}")


def ffmpeg_command(encoder: Encoder, fps: int, frames: int, output: Path) -> list[str]:
    """The argument list of the encoder process (review 04 finding 5): exit on the first
    error (-xerror: a frame whose IDAT does not inflate ends the encode non-zero instead of
    being dropped from a clip reported complete; fix round 1), a forced PNG decoder on an
    image2pipe input from stdin, exactly ``frames`` frames, no audio, H.264 in yuv420p at
    MP4_CRF, a fast-start MP4, never overwriting (-n)."""
    return [
        *encoder.command,
        "-hide_banner",
        "-xerror",
        "-loglevel",
        "error",
        "-nostats",
        "-f",
        "image2pipe",
        "-c:v",
        "png",
        "-framerate",
        str(fps),
        "-i",
        "pipe:0",
        "-frames:v",
        str(frames),
        "-an",
        "-c:v",
        encoder.codec,
        "-pix_fmt",
        "yuv420p",
        "-crf",
        str(MP4_CRF),
        "-movflags",
        "+faststart",
        "-n",
        str(output),
    ]


def cross_volume_error(exc: OSError) -> bool:
    """True when ``exc`` is a rename refused across volumes: errno EXDEV (POSIX) or
    Windows' ERROR_NOT_SAME_DEVICE (CROSS_VOLUME_WINERROR)."""
    return exc.errno == errno.EXDEV or getattr(exc, "winerror", None) == CROSS_VOLUME_WINERROR


def place_output(src: Path, dst: Path) -> None:
    """Move the finished file ``src`` onto the reservation ``dst`` (an empty file this
    process created exclusively): os.replace, and when that fails across volumes
    (``cross_volume_error``: the system temporary folder on one drive, the working
    directory on another) a copy in COPY_CHUNK_BYTES chunks into ``dst``, flushed and
    fsynced, then ``src`` removed (fix round 1). Any other OSError propagates."""
    try:
        os.replace(src, dst)
    except OSError as exc:
        if not cross_volume_error(exc):
            raise
    else:
        return
    with (
        src.open("rb") as reader,  # bytes files (no encoding= applies)
        dst.open("wb") as writer,  # a bytes file too (no encoding= applies)
    ):
        shutil.copyfileobj(reader, writer, COPY_CHUNK_BYTES)
        writer.flush()
        os.fsync(writer.fileno())
    src.unlink()


def stderr_tail(path: Path, chars: int = STDERR_TAIL_CHARS) -> str:
    """The last ``chars`` characters of the encoder's stderr file (UTF-8, replacement
    characters for anything else, whitespace collapsed), '' when unreadable."""
    try:
        text = path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return ""
    return " ".join(text.split())[-chars:]


def open_stderr_file(path: Path) -> Any:
    """The encoder's stderr file, opened for writing (bytes; a seam tests fail)."""
    return path.open("wb")  # a bytes file (no encoding= applies)


def remove_tree(path: Path, retry_s: float = TEMP_REMOVE_RETRY_S) -> bool:
    """Remove the folder ``path`` and everything in it, retrying every TEMP_REMOVE_POLL_S
    for ``retry_s`` [s] when a file in it is still held (Windows releases a just-killed
    child's handle on an inherited file a moment after the process has ended; fix round
    2). True when the folder is gone."""
    deadline = time.monotonic() + retry_s
    while True:
        shutil.rmtree(path, ignore_errors=True)
        if not path.exists():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(TEMP_REMOVE_POLL_S)


# ------------------------------------------------------------------ the process tree

if sys.platform == "win32":
    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000

    class _IoCounters(ctypes.Structure):
        _fields_ = [
            (name, ctypes.c_ulonglong)
            for name in (
                "ReadOperationCount",
                "WriteOperationCount",
                "OtherOperationCount",
                "ReadTransferCount",
                "WriteTransferCount",
                "OtherTransferCount",
            )
        ]

    class _JobBasicLimits(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
            ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _JobExtendedLimits(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _JobBasicLimits),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    _kernel32.SetInformationJobObject.restype = wintypes.BOOL
    _kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    _kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _kernel32.TerminateJobObject.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL


def popen_tree_kwargs() -> dict[str, Any]:
    """The extra Popen keyword arguments that let the encoder's whole process tree be
    killed as one (fix round 2): on POSIX ``start_new_session`` (its own process group,
    for os.killpg); on Windows CREATE_NO_WINDOW alone (the Job Object is assigned after
    the start, ``process_tree_handle``)."""
    if sys.platform == "win32":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {"start_new_session": True}


def process_tree_handle(proc: subprocess.Popen[bytes]) -> Any:
    """Windows: a Job Object ``proc`` is assigned to (so every process it starts from now
    on is in it too) with KILL_ON_JOB_CLOSE, returned as its handle (an int) for
    ``kill_process_tree`` and ``close_tree_handle``; None when the job cannot be made or
    the assignment is refused (the plain kill of ``proc`` then stands). Elsewhere None."""
    if sys.platform != "win32":
        return None
    job = _kernel32.CreateJobObjectW(None, None)
    if not job:
        return None
    info = _JobExtendedLimits()
    info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    ok = _kernel32.SetInformationJobObject(
        job, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(info), ctypes.sizeof(info)
    )
    if ok:
        ok = _kernel32.AssignProcessToJobObject(job, int(proc._handle))
    if not ok:
        _kernel32.CloseHandle(job)
        return None
    return int(job)


def kill_process_tree(proc: subprocess.Popen[bytes], job: Any) -> None:
    """Kill ``proc`` and every process under it without waiting: TerminateJobObject of
    ``job`` on Windows (proc.kill when there is no job), os.killpg of its own process
    group on POSIX (started with ``popen_tree_kwargs``; proc.kill when the group is
    gone). Errors are ignored: the caller waits for the process with a timeout."""
    try:
        if sys.platform == "win32":
            if job is not None and _kernel32.TerminateJobObject(job, 1):
                return
            proc.kill()
        else:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
    except OSError:
        pass


def close_tree_handle(job: Any) -> None:
    """Close the Job Object handle ``job`` (None: nothing), once the process has ended."""
    if job is not None and sys.platform == "win32":
        _kernel32.CloseHandle(job)


# ------------------------------------------------------------------ the session


@dataclass(frozen=True)
class SessionSpec:
    """What a session is created with (the server validated every field)."""

    experiment: str
    timestamp: str
    runs: tuple[str, ...]
    run_dir: Path
    fps: int
    frames: int
    width: int
    height: int
    footer: tuple[str, ...]
    times: tuple[float, ...] | None = None


class VideoSession:
    """One MP4 export: created with its ``spec``, the ``encoder`` and the ``output_dir``
    (the server's working directory), it starts the encoder process at once (stdin a pipe,
    stdout discarded, stderr to a file in a fresh temporary folder outside ``repo_root``
    and ``results_root``, cwd that folder, the process tree killable as one:
    ``process_tree_handle``), a writer thread fed by a queue of ``limits.queue_frames``
    frames and a monitor thread for the timeouts and the stderr cap. Thread-safe:
    ``accept_frame``, ``finish``, ``cancel``, ``record`` and ``close`` may be called from
    any thread. ``report`` (optional) is called with one line when the session leaves
    something behind (its temporary folder, an encoder process that did not end), so the
    server can record it. Raises VideoError (503) when the temporary folder would lie
    inside the repository or the results root, its stderr file cannot be made, or the
    encoder cannot start; a start that fails after the folder was made removes it (fix
    round 2)."""

    def __init__(
        self,
        spec: SessionSpec,
        encoder: Encoder,
        output_dir: Path,
        *,
        repo_root: Path,
        results_root: Path,
        limits: Limits = DEFAULT_LIMITS,
        report: Callable[[str], None] | None = None,
    ) -> None:
        self.spec = spec
        self.encoder = encoder
        self.output_dir = Path(output_dir)
        self.limits = limits
        self.report = report
        self.id = secrets.token_urlsafe(ID_BYTES)
        self.state = STATE_CAPTURING
        self.received = 0
        self.bytes_used = 0
        self.error: str | None = None
        self.path: Path | None = None
        self.t0 = time.monotonic()
        self.t_end: float | None = None
        self._lock = threading.Lock()
        self._accept_lock = threading.Lock()
        self._cleanup_lock = threading.Lock()
        self._last_frame_at = self.t0
        self._write_since: float | None = None
        self._finish_at: float | None = None
        self._killed_at: float | None = None
        self._reserved: Path | None = None
        self._failing = False
        self._cleaned = False
        self._done = threading.Event()
        self._queue: queue.Queue[bytes | None] = queue.Queue(maxsize=limits.queue_frames)
        self._job: Any = None
        self.temp_dir = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX))
        try:
            self._start(spec, encoder, repo_root, results_root)
        except BaseException:
            self._abandon_start()
            raise

    def _start(
        self, spec: SessionSpec, encoder: Encoder, repo_root: Path, results_root: Path
    ) -> None:
        """Everything after the temporary folder is made: its check, the stderr file, the
        encoder process (in a killable tree: ``_proc``, ``_job``), the writer and monitor
        threads. Raises VideoError (503)."""
        if in_or_under(self.temp_dir, (Path(repo_root), Path(results_root))) is not None:
            raise VideoError(
                HTTP_UNAVAILABLE,
                "temp_inside_tree",
                "the temporary folder would lie inside the repository or the results root",
            )
        self.temp_output = self.temp_dir / TEMP_OUTPUT
        self._stderr_path = self.temp_dir / STDERR_FILE
        try:
            self._stderr = open_stderr_file(self._stderr_path)
        except OSError as exc:
            raise VideoError(
                HTTP_UNAVAILABLE,
                "temp_failed",
                f"the encoder's message file could not be made: {type(exc).__name__}",
            ) from exc
        try:
            self._proc = subprocess.Popen(
                ffmpeg_command(encoder, spec.fps, spec.frames, self.temp_output),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=self._stderr,
                cwd=self.temp_dir,
                shell=False,
                **popen_tree_kwargs(),
            )
        except OSError as exc:
            raise VideoError(
                HTTP_UNAVAILABLE,
                "encoder_failed",
                f"the encoder could not start: {type(exc).__name__}",
            ) from exc
        self._job = process_tree_handle(self._proc)
        self._writer = threading.Thread(
            target=self._write_loop, name=f"launchsim-video-writer-{self.id[:6]}", daemon=True
        )
        self._monitor = threading.Thread(
            target=self._watch, name=f"launchsim-video-monitor-{self.id[:6]}", daemon=True
        )
        self._writer.start()
        self._monitor.start()

    def _abandon_start(self) -> None:
        """A start that failed after the temporary folder was made (fix round 2): the
        session cancelled, a started process tree killed and waited for briefly, a started
        writer woken, the stderr file and job handle closed, the folder removed."""
        with self._lock:
            self.state = STATE_CANCELLED
            self.t_end = time.monotonic()
        proc: subprocess.Popen[bytes] | None = getattr(self, "_proc", None)
        if proc is not None:
            kill_process_tree(proc, self._job)
            with contextlib.suppress(subprocess.TimeoutExpired):
                proc.wait(TERMINATE_WAIT_S)
        with contextlib.suppress(queue.Full):
            self._queue.put_nowait(None)
        stderr = getattr(self, "_stderr", None)
        if stderr is not None:
            with contextlib.suppress(OSError):
                stderr.close()
        close_tree_handle(self._job)
        self._job = None
        if proc is None or proc.poll() is not None:
            remove_tree(self.temp_dir)

    # ---------------------------------------------------------- queries

    @property
    def is_open(self) -> bool:
        """True while the session holds the slot (capturing or finishing)."""
        with self._lock:
            return self.state in OPEN_STATES

    @property
    def remaining_bytes(self) -> int:
        """What the byte budget still allows [bytes]."""
        with self._lock:
            return max(0, self.limits.byte_budget - self.bytes_used)

    def record(self) -> dict[str, Any]:
        """The session as plain data (GET /api/videos/<id>): id, state, format, the fps,
        frame count, size, frames received, bytes accepted and the budget, the elapsed
        time, the directory and runs, the output's absolute path once done, the error
        once failed, the file name reserved or planned."""
        with self._lock:
            end = self.t_end if self.t_end is not None else time.monotonic()
            spec = self.spec
            named = self.path or self._reserved
            file_name = (
                named.name
                if named is not None
                else output_stem(spec.experiment, spec.timestamp, spec.runs) + OUTPUT_SUFFIX
            )
            return {
                "id": self.id,
                "state": self.state,
                "format": FORMAT_MP4,
                "fps": spec.fps,
                "frames": spec.frames,
                "received": self.received,
                "width": spec.width,
                "height": spec.height,
                "bytes": self.bytes_used,
                "budget_bytes": self.limits.byte_budget,
                "elapsed_s": round(end - self.t0, 3),
                "experiment": spec.experiment,
                "timestamp": spec.timestamp,
                "runs": list(spec.runs),
                "path": None if self.path is None else str(self.path),
                "error": self.error,
                "file_name": file_name,
            }

    # ---------------------------------------------------------- the routes' actions

    def check_next(self, index: int, size: int = 0) -> None:
        """VideoError unless the session is capturing (409), ``index`` is the next frame
        (409: a repeated or skipped index, or every frame posted) and ``size`` more bytes
        fit the budget (413). The frame route calls it before it reads a body."""
        with self._lock:
            self._check_next(index, size)

    def _check_next(self, index: int, size: int) -> None:
        """``check_next`` under the lock."""
        self._check_capturing()
        if self.received >= self.spec.frames:
            raise VideoError(HTTP_CONFLICT, "frames_complete", "every frame has been posted")
        if index != self.received:
            raise VideoError(HTTP_CONFLICT, "frame_order", f"frame {self.received} is the next one")
        if self.bytes_used + size > self.limits.byte_budget:
            raise VideoError(HTTP_PAYLOAD_TOO_LARGE, "budget", "the session's byte budget is spent")

    def accept_frame(self, index: int, body: bytes) -> int:
        """Take frame ``index`` (which must be the next, ``received``): the session must be
        capturing (409 otherwise), the body within the budget (413), a PNG of the
        session's size (``check_png``, 422), then queued for the writer within
        ``limits.room_timeout_s`` (503 otherwise). Returns the frames received so far.
        Two posts of one index are serialised, so the second is 409."""
        with self._accept_lock:
            with self._lock:
                self._check_next(index, len(body))
            check_png(body, self.spec.width, self.spec.height)
            self._queue_within_room(body)
            with self._lock:
                self._check_capturing()
                self.received += 1
                self.bytes_used += len(body)
                self._last_frame_at = time.monotonic()
                return self.received

    def finish(self) -> None:
        """Close the clip: every frame posted (409 otherwise), the end-of-input marker
        queued (503 when the queue has no room within the room timeout), the state
        finishing; the writer then closes the pipe, waits for the encoder and reserves the
        output. Poll ``record`` for done or failed."""
        with self._accept_lock:
            with self._lock:
                self._check_capturing()
                if self.received != self.spec.frames:
                    raise VideoError(
                        HTTP_CONFLICT,
                        "frames_missing",
                        f"{self.received} of {self.spec.frames} frames posted: post the rest "
                        "or cancel",
                    )
            self._queue_within_room(None)
            with self._lock:
                self._check_capturing()
                self.state = STATE_FINISHING
                self._finish_at = time.monotonic()

    def _queue_within_room(self, item: bytes | None) -> None:
        """Put ``item`` on the writer's queue within ``limits.room_timeout_s`` (VideoError
        503 otherwise: the encoder has not taken the queued frames)."""
        try:
            self._queue.put(item, timeout=self.limits.room_timeout_s)
        except queue.Full:
            raise VideoError(
                HTTP_UNAVAILABLE,
                "encoder_busy",
                "the encoder has not taken the queued frames within "
                f"{self.limits.room_timeout_s:g} s",
            ) from None

    def cancel(self) -> None:
        """Discard the session: the state cancelled at once (the slot freed), then the
        encoder's process tree killed, any reservation removed and the temporary folder
        removed (``_tear_down``, whose waits are bounded; 409 once the session has
        ended)."""
        with self._lock:
            if self.state in FINAL_STATES:
                raise VideoError(HTTP_CONFLICT, "video_ended", f"the video session is {self.state}")
            self.state = STATE_CANCELLED
            self.t_end = time.monotonic()
        self._tear_down()

    def close(self) -> None:
        """The server is stopping: cancel an open session (no error when it has ended),
        join the threads briefly (a writer still blocked in a pipe write is waited for
        WRITER_WAIT_S only and left: fix round 2) and remove the temporary folder, trying
        again when an earlier removal left it."""
        with self._lock:
            open_ = self.state in OPEN_STATES
            if open_:
                self.state = STATE_CANCELLED
                self.t_end = time.monotonic()
        if open_:
            self._tear_down()
        self._writer.join(self._writer_wait())
        self._monitor.join(THREAD_JOIN_S)
        self._cleanup()

    def _writer_wait(self) -> float:
        """How long to wait for the writer thread: WRITER_WAIT_S while it is in a pipe
        write (which may never return), THREAD_JOIN_S otherwise."""
        with self._lock:
            blocked = self._write_since is not None
        return WRITER_WAIT_S if blocked else THREAD_JOIN_S

    # ---------------------------------------------------------- internals

    def _check_capturing(self) -> None:
        """Under the lock: VideoError 409 unless the session is capturing."""
        if self.state != STATE_CAPTURING:
            why = f": {self.error}" if self.error else ""
            raise VideoError(
                HTTP_CONFLICT, "video_not_capturing", f"the video session is {self.state}{why}"
            )

    def _fail(self, reason: str) -> None:
        """Fail the session (once): read the tail of the encoder's stderr so far, publish
        the failed state with ``reason`` and that tail in one step (a poll never sees the
        reason without the tail) BEFORE the encoder is killed (fix round 2: a poll, the
        slot and the server's stop never wait on a kill, which a wrapper's surviving child
        can hold up), then tear the session down."""
        with self._lock:
            if self.state in FINAL_STATES or self._failing:
                return
            self._failing = True
        tail = stderr_tail(self._stderr_path)
        with self._lock:
            if self.state in FINAL_STATES:  # cancelled meanwhile
                return
            self.state = STATE_FAILED
            self.t_end = time.monotonic()
            self.error = f"{reason} (ffmpeg: {tail})" if tail else reason
        self._tear_down()

    def _note(self, text: str) -> None:
        """Add ``text`` to the session's error (a cancelled session's error starts with it)
        and report it to the server (``report``)."""
        with self._lock:
            if self.error is None:
                self.error = text
            elif text not in self.error:
                self.error = f"{self.error}; {text}"
        if self.report is not None:
            self.report(text)

    def _kill(self) -> None:
        """Kill the encoder's process tree without waiting, once (``kill_process_tree``);
        nothing when the process has ended. Never closes the pipe: the writer thread owns
        it (fix round 2)."""
        with self._lock:
            killed = self._killed_at is not None
            if not killed:
                self._killed_at = time.monotonic()
        if not killed and self._proc.poll() is None:
            kill_process_tree(self._proc, self._job)

    def _tear_down(self) -> None:
        """After a fail or cancel (the final state already published): kill the encoder
        tree, drain the queue and wake the writer (at most one frame POST can be blocked
        in a put, since posts hold the accept lock, so the marker always fits), remove a
        reservation never filled, wait TERMINATE_WAIT_S for the process, join the writer
        (WRITER_WAIT_S only while it is in a pipe write; one still blocked afterwards is
        abandoned and recorded: fix round 2), then remove the temporary folder
        (``_cleanup``)."""
        self._kill()
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        with contextlib.suppress(queue.Full):
            self._queue.put_nowait(None)
        with self._lock:
            reserved = self._reserved if self.path is None else None
            self._reserved = None
        if reserved is not None:
            with contextlib.suppress(OSError):
                reserved.unlink(missing_ok=True)
        with contextlib.suppress(subprocess.TimeoutExpired):
            self._proc.wait(TERMINATE_WAIT_S)
        if threading.current_thread() is not self._writer:
            self._writer.join(self._writer_wait())
            with self._lock:
                abandoned = self._writer.is_alive() and self._write_since is not None
            if abandoned:
                self._note("the writer thread is still blocked on the encoder's pipe")
        self._cleanup()

    def _cleanup(self) -> None:
        """Once the session has ended and the process has exited (Windows keeps the stderr
        file open until then): close the stderr file and the job handle (the first call),
        then remove the temporary folder, retrying for TEMP_REMOVE_RETRY_S
        (``remove_tree``; one call at a time); a folder still there is recorded in the
        error and reported (``_note``), and a later call (the server's ``close``) tries
        again (fix round 2). Ends the monitor thread (``_done``)."""
        with self._lock:
            if self.state in OPEN_STATES or self._proc.poll() is None:
                return
            first = not self._cleaned
            self._cleaned = True
        if first:
            with contextlib.suppress(OSError):
                self._stderr.close()
            close_tree_handle(self._job)
            self._job = None
        with self._cleanup_lock:
            removed = not self.temp_dir.exists() or remove_tree(self.temp_dir)
        if not removed:
            self._note(f"the temporary folder {self.temp_dir} could not be removed")
        self._done.set()

    def _close_pipe(self) -> None:
        """Close the encoder's stdin: the writer thread alone calls it, between its writes
        (a close from another thread while a write is in flight blocks on the pipe's lock
        for as long as the write does; fix round 2)."""
        with contextlib.suppress(OSError, ValueError):
            if self._proc.stdin is not None:
                self._proc.stdin.close()

    def _write_loop(self) -> None:
        """The writer thread: pipe each queued frame to the encoder (the write may block;
        the monitor times it), and on the end-of-input marker close the pipe, wait for
        the encoder and complete (``_complete``); the pipe is closed on every exit."""
        try:
            while True:
                item = self._queue.get()
                with self._lock:
                    if self.state in FINAL_STATES:
                        return  # failed or cancelled meanwhile: nothing more is written
                    if item is not None:
                        self._write_since = time.monotonic()
                if item is None:
                    break
                try:
                    assert self._proc.stdin is not None
                    self._proc.stdin.write(item)
                    self._proc.stdin.flush()
                except OSError:
                    with self._lock:
                        self._write_since = None
                    self._close_pipe()
                    self._fail("the encoder stopped taking frames")
                    return
                with self._lock:
                    self._write_since = None
            with self._lock:
                finishing = self.state == STATE_FINISHING
            if not finishing:
                return
            self._close_pipe()
            rc = self._proc.wait()
            self._complete(rc)
        finally:
            self._close_pipe()
            self._cleanup()

    def _complete(self, rc: int) -> None:
        """The encoder has ended after the finish: a non-zero exit or no output fails the
        session; else the final name is reserved in the output folder and the temporary
        file moved onto it (``place_output``: os.replace, or a copy across volumes), the
        state done with the path."""
        self._stderr.close()
        if rc != 0:
            self._fail(f"the encoder exited {rc}")
            return
        try:
            size = self.temp_output.stat().st_size
        except OSError:
            size = 0
        if size <= 0:
            self._fail("the encoder wrote no file")
            return
        stem = output_stem(self.spec.experiment, self.spec.timestamp, self.spec.runs)
        with self._lock:
            if self.state != STATE_FINISHING:
                return
            try:
                reserved = reserve_output(self.output_dir, stem, self.spec.run_dir)
                self._reserved = reserved
                place_output(self.temp_output, reserved)
            except (OSError, run_data.RunDataError) as exc:
                failure = f"the video could not be saved: {type(exc).__name__}: {exc}"
            else:
                self.path = reserved
                self.state = STATE_DONE
                self.t_end = time.monotonic()
                return
        self._fail(failure)

    def _stderr_size(self) -> int:
        """The encoder's stderr file size [bytes] now (0 when it cannot be read)."""
        try:
            return int(self._stderr_path.stat().st_size)
        except OSError:
            return 0

    def _watch(self) -> None:
        """The monitor thread: every MONITOR_POLL_S, fail an open session whose encoder has
        written more than ``stderr_max_bytes`` of messages (fix round 2), a capturing
        session with no frame for ``idle_s``, a write blocked for ``write_block_s`` or a
        finish not complete in ``finish_s``; once the session has ended, remove the
        temporary folder when the process has exited (``_cleanup``) or, when the killed
        process is still there TERMINATE_WAIT_S later, record that and stop."""
        limits = self.limits
        while not self._done.wait(MONITOR_POLL_S):
            with self._lock:
                state = self.state
                last = self._last_frame_at
                since = self._write_since
                finish_at = self._finish_at
                killed_at = self._killed_at
            now = time.monotonic()
            if state in FINAL_STATES:
                if self._proc.poll() is not None:
                    self._cleanup()
                    return
                if killed_at is not None and now - killed_at > TERMINATE_WAIT_S:
                    self._note(
                        f"the encoder process {self._proc.pid} did not end after the kill; "
                        f"the temporary folder {self.temp_dir} is kept"
                    )
                    self._done.set()
                    return
                continue
            size = self._stderr_size()
            if size > limits.stderr_max_bytes:
                self._fail(f"the encoder wrote {size / MIB:.1f} MiB of messages")
            elif state == STATE_CAPTURING and now - last > limits.idle_s:
                self._fail(f"no frame arrived for {limits.idle_s:g} s")
            elif since is not None and now - since > limits.write_block_s:
                self._fail(f"the encoder took no frame for {limits.write_block_s:g} s")
            elif (
                state == STATE_FINISHING
                and finish_at is not None
                and now - finish_at > limits.finish_s
            ):
                self._fail(f"the encoder did not finish within {limits.finish_s:g} s")
