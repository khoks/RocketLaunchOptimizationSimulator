Provenance: SP2 step A0 survey 07 of 9 (read-only agent report, 2026-10-05, line numbers checked at commit b69ff0c); below this header, a byte copy from the session scratchpad (a0/07-server-and-worker.md); a record, not edited (README.md).

# 07 - App server and job runner: thread or process, and the server's safety rules

SP2 step A0 survey, 2026-10-05. Repository at HEAD b69ff0c, clean before and after
(`git status --porcelain`: 0 lines). Phase file sections read: 5.1, 5.6, risks R7, R11, R16.
Python 3.12.11 (uv-managed CPython, win32), 32 logical CPUs, `sys.getswitchinterval()` =
0.005 s. Standard library only for everything proposed here.

Verdict in one paragraph: **a worker thread in the server process is good enough.** While a
real planar search, a real plain launch and a real stage-1 offload solve ran in a worker
thread, 4,212 status requests issued every 100 ms were all answered in under 170 ms
(median 17-21 ms over a new connection per request, 4-5 ms over a kept-alive connection;
3 of 4,212 above 100 ms, none above 250 ms), and a 1 MB JSON payload built with
`json.dumps` on every request came back in 48-65 ms median (idle: 38-53 ms). A status poll
every 500 ms is therefore never late by more than a third of its period. No interpreter
setting needs changing. The child process is the fallback only if cancelling a launch
becomes a requirement.

Scratch files (all under the a0 scratch folder, nothing in the repository):
`m07_measure.py`, `m07_poll_client.py` (latency), `m07_safety.py` (stdlib defaults, bind
matrix, prototype of the rules), `m07_interrupt.py` (interrupted launch), `m07_connect.py`
(connection breakdown); outputs `m07_log.txt`, `m07_results_{probe,si005,si0005,plain,solve}.json`,
`m07_runA_out.txt`, `m07_safety_out.txt`, `m07_interrupt_out.txt`, `m07_connect_out.txt`;
working folder `m07_work/` (three scratch launch directories written by `write_run`, never
under `results/`).

Process note: for part of the session the harness was in plan mode and file writes were not
allowed. Run A below was therefore made with an inline program (same handlers and job as
`m07_measure.py`, a pipe-based client, no file written); its console output is saved
verbatim in `m07_runA_out.txt`. Runs B to E repeat and extend it with the saved scripts.

---

## 1. Measurement

### 1.1 Set-up

- Server: `http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)`, `serve_forever` in a
  daemon thread. Two instances: one HTTP/1.0 (the stdlib default, one connection and one
  handler thread per request) and one HTTP/1.1 (persistent connection).
- Handler: `GET /status` returns a 74-byte JSON object; `GET /scene` runs
  `json.dumps(BIG, separators=(",", ":"), allow_nan=False)` on a dict of 10 float columns
  on every request: 1,001,717 bytes.
- Job, in a daemon worker thread (the task's job): `yaml.safe_load` of
  `experiments/silo_offload_2d.yaml` and its vehicle file, `config.resolve_experiment(exp,
  veh)`, `sim.run_resolved(resolved.baseline)` (the searched pad run). No file output.
- Two larger jobs, the app's real composition from an in-memory dict (pad + `silo_cold`,
  sweeps and sensitivity removed): `resolve_experiment`, `results_io.check_result_names`,
  `sim.check_resolved`, `sim.run_resolved` twice, `results_io.planar_experiment_result`,
  `results_io.write_run(er, <scratch dir>, plots=True)`. "plain": no offload block.
  "solve": one solved stage-1 case (`{name: silo_cold_s1, of: silo_cold, solve: stage1}`,
  no paired pad, no pad control), which R7 asks to be measured.
- Clients: (a) "in-proc": `urllib` in the server's own process (as the task asks; it
  competes for the same GIL, so it overstates what a browser sees); (b) "new": a separate
  Python process using `http.client`, one new connection per request against the HTTP/1.0
  server (what a browser does against an HTTP/1.0 server); (c) "keep": a separate process
  with one persistent connection against the HTTP/1.1 server (what a browser does against
  an HTTP/1.1 server). Requests every 100 ms for `/status`, every 500 ms for `/scene`.
- Latency = `time.perf_counter()` around connect/request/read of the whole body in the
  client. Job wall time = `perf_counter` in the worker; job CPU = `time.thread_time()` of
  the worker thread.
- Load: other surveyors' jobs ran on the machine during runs B to E. The same job's CPU
  time ranged from 18.1 s to 45.2 s between runs with nothing changed. So job times are
  compared through the fraction of wall time the worker was not running,
  (wall - CPU) / wall, and latencies as ratios to the idle latency of the same run.

### 1.2 Latency of `/status` (74 bytes), requests every 100 ms

Idle (50 requests each):

| client | run P (quiet) | run B | run C |
|---|---|---|---|
| in-proc urllib, new connection: median / p95 / max [ms] | 15.73 / 21.83 / 30.37 | 2.77 / 26.13 / 26.60 | 17.89 / 26.51 / 26.87 |
| subprocess, new connection | 13.73 / 23.69 / 34.14 | 15.48 / 25.64 / 25.73 | 12.29 / 25.15 / 26.46 |
| subprocess, kept-alive | 0.55 / 0.78 / 9.39 | 0.71 / 0.90 / 14.53 | 0.68 / 0.96 / 21.05 |

The idle new-connection latency is bimodal on this machine: about 2 ms or about 15-26 ms.
`m07_connect.py` (raw socket, 40 requests) put the slow mode in the hand-off to the new
handler thread (server "accept to handler": median 0.70 ms, max 25.77 ms; client connect:
median 0.71 ms, max 26.03 ms; handler itself 0.17 ms). It is there with no job running.

During the job (count / median / p95 / max [ms]; job wall and worker CPU [s]):

| run, switch interval | scenario | job wall / CPU | n | median | p95 | max | > 100 ms |
|---|---|---|---|---|---|---|---|
| A, 0.005 (quiet) | alone | 20.62 / 20.19 | - | - | - | - | - |
| A | in-proc urllib | 20.64 / 19.97 | 207 | 14.45 | 30.96 | 68.26 | 0 |
| A | subprocess, new connection | 19.09 / 18.34 | 191 | 17.10 | 29.18 | 41.90 | 0 |
| A | subprocess, kept-alive | 18.66 / 18.38 | 187 | 4.83 | 15.71 | 31.89 | 0 |
| A | alone again | 24.59 / 23.97 | - | - | - | - | - |
| B, 0.005 (loaded) | alone | 46.31 / 45.20 | - | - | - | - | - |
| B | in-proc urllib | 38.11 / 36.52 | 380 | 15.10 | 30.41 | 158.27 | 1 |
| B | subprocess, new connection | 27.79 / 26.77 | 277 | 19.75 | 30.80 | 168.03 | 1 |
| B | subprocess, kept-alive | 23.63 / 22.91 | 236 | 3.67 | 11.08 | 30.73 | 0 |
| B | alone again | 23.16 / 22.52 | - | - | - | - | - |
| C, 0.0005 (loaded) | alone | 34.56 / 33.47 | - | - | - | - | - |
| C | in-proc urllib | 41.64 / 40.31 | 417 | 7.54 | 22.54 | 31.27 | 0 |
| C | subprocess, new connection | 24.66 / 24.20 | 245 | 18.14 | 26.42 | 111.38 | 1 |
| C | subprocess, kept-alive | 21.65 / 21.31 | 216 | 1.09 | 1.91 | 2.29 | 0 |
| C | alone again | 37.17 / 35.55 | - | - | - | - | - |
| D, 0.005, plain launch | alone | 48.76 / 47.28 | - | - | - | - | - |
| D, plain launch | subprocess, new connection | 53.18 / 51.31 | 531 | 20.73 | 34.69 | 95.99 | 0 |
| E, 0.005, stage-1 solve launch | subprocess, new connection | 132.53 / 127.41 | 1,325 | 18.05 | 31.66 | 97.32 | 0 |

Totals: 4,212 status samples during a job; 3 above 100 ms (158.27, 168.03, 111.38); 0 above
250 ms.

Per stage of the two real launches (subprocess client, new connection per request):

| stage | plain: wall [s], n, median / p95 / max [ms] | solve: wall [s], n, median / p95 / max [ms] |
|---|---|---|
| resolve + names + preflight | 0.01, - | 0.01, - |
| pad baseline (`run_resolved`) | 21.09, 211, 20.46 / 33.65 / 49.51 | 24.42, 244, 21.10 / 32.41 / 97.32 |
| variant `silo_cold` | 27.07, 270, 21.04 / 34.69 / 95.99 | 28.44, 284, 18.43 / 31.92 / 44.00 |
| `planar_experiment_result` (solve: with the offload pass) | 2.28, 23, 18.65 / 34.21 / 36.31 | 74.10, 741, 16.66 / 30.50 / 76.30 |
| `write_run(plots=True)` | 2.70, 27, 18.34 / 46.10 / 63.08 | 5.54, 56, 20.96 / 72.91 / 87.38 |

The write stage (pandas `to_csv` of 3.6 MB per run, matplotlib PNGs) holds the GIL a little
longer per slice (p95 46-73 ms) but never blocked a request beyond 88 ms.

The solve launch finished normally in the worker thread: `silo_cold_s1` solve status `ok`,
offload 41,262.9 kg at P_ref 26,054.4 kg (SP1's recorded headline, reproduced from a dict;
a scratch consistency check, not a result). It wrote a normal directory (metrics.json,
resolved_config.yaml, summary.md, `pad/`, `silo_cold/`, `silo_cold_s1/`, `plots/`;
11.7 MB). The plain launch wrote 7.8 MB (metrics.json 76,862 B, summary.md 15,394 B, two
runs, 16 PNGs).

### 1.3 Latency of a 1 MB JSON payload (`json.dumps` per request), requests every 500 ms

`json.dumps` of the object alone, idle: 25.3 ms (run P), 39.9 ms (B), 36.6 ms (C).

| run | scenario | n | median | p95 | max [ms] | idle median of the same run | ratio |
|---|---|---|---|---|---|---|---|
| A, 0.005 | new connection, during job | 49 | 48.00 | 71.03 | 93.62 | 37.92 (run P) | 1.27 |
| A, 0.005 | kept-alive, during job | 43 | 38.39 | 54.10 | 64.33 | 23.90 (run P) | 1.61 |
| B, 0.005 | new connection, during job | 51 | 55.77 | 75.91 | 76.51 | 51.48 | 1.08 |
| C, 0.0005 | new connection, during job | 86 | 64.59 | 86.66 | 128.56 | 53.37 | 1.21 |

229 samples, 1 above 100 ms, none above 250 ms. Most of the time is the `json.dumps`
itself, which runs in C under the GIL in one piece.

For scale: one recorded run at full resolution
(`results/silo_offload_2d/20261003T112934Z/pad/timeseries.csv`, 10,779 rows x 32 columns,
3,636,073 bytes) takes about 50 ms in `pandas.read_csv` and 115 ms in `json.dumps`, and is
3,929,623 bytes of JSON. So a payload should be decimated, and its encoded bytes cached per
(directory, run selection).

### 1.4 Cost to the job

Fraction of the job's wall time in which the worker thread was not running,
(wall - CPU) / wall:

| scenario | run A | run B | run C (0.0005) | run D (plain) |
|---|---|---|---|---|
| alone (two per run) | 2.1%, 2.5% | 2.4%, 2.8% | 3.2%, 4.4% | 3.0% |
| `/status` every 100 ms, in-proc | 3.2% | 4.2% | 3.2% | - |
| `/status` every 100 ms, new connection | 3.9% | 3.7% | 1.9% | 3.5% |
| `/status` every 100 ms, kept-alive | 1.5% | 3.0% | 1.6% | - |
| 1 MB `/scene` every 500 ms | 8.7% (new), 9.5% (kept) | 9.3% | 2.5% | - |

The stage-1 solve launch (run E, `/status` every 100 ms, new connection): 3.9%
((132.53 - 127.41) / 132.53).

A status poll at 10 per second costs the job at most about 2 points of wall time, which is
inside the spread of the "alone" runs. At the app's 2 per second it is not measurable.
Building a 1 MB payload twice a second costs 6-7 points at the default interval, as
expected from 2 x 25-40 ms of `json.dumps` per second; the app fetches a payload once per
view, not twice a second. Wall and CPU times themselves cannot resolve this: the same job
took 18.1 to 45.2 s of CPU depending on the machine's load (the plain launch 48.76 s alone
and 53.18 s polled is within that spread).

### 1.5 What the numbers mean

- **Status poll every 500 ms.** The answer arrives in about 4-5 ms (kept-alive) or 17-21 ms
  (new connection) while a solve runs; the slowest of 4,212 took 168 ms, a third of the
  period. Polls cannot pile up. The page could poll at 250 ms and still be safe.
- **Ratios to idle** (robust to the load): new connection, median 1.25-1.5x idle (17.10
  against 13.73; 19.75 against 15.48; 18.14 against 12.29), p95 1.0-1.4x; kept-alive, about
  +3 to +4 ms per request at the default interval (4.83 against 0.55; 3.67 against 0.71),
  +0.4 ms at 0.0005 s (1.09 against 0.68); 1 MB payload 1.1-1.6x.
- **Why it works.** A thread waiting for the GIL is granted it after at most one switch
  interval (5 ms), and a small HTTP exchange needs only a few acquisitions (accept in the
  `serve_forever` thread, start of the handler thread, read, write). The search is Python
  bytecode calling short numpy/scipy routines, so it never holds the GIL for long; the
  longest observed blockage, including pandas CSV writing and matplotlib, was under 170 ms.
- **`sys.setswitchinterval`.** Leave it at the default 0.005 s. Lowering it to 0.0005 s cut
  the kept-alive latency (median 3.7-4.8 ms to 1.1 ms, p95 11-16 ms to 1.9 ms) but did
  nothing for new connections (18.14 ms against 17.10-19.75 ms), whose cost is connection
  and thread set-up, not the GIL. Nothing in the app needs millisecond answers, and the
  setting is process-wide.
- **`localhost` is slow, `127.0.0.1` is not.** `getaddrinfo("localhost")` returns
  `['::1', '127.0.0.1']` on this machine; with an IPv4-only server, `urllib` against
  `http://localhost:<port>/` took 2,038-2,064 ms per request (three runs): the IPv6 address
  is tried first and takes about 2 s to fail before the IPv4 one is used. The command must
  print the `127.0.0.1` URL and tests must use `127.0.0.1`.
- **Time per launch seen today** (loaded machine): pad baseline 18.4-46.3 s; plain launch
  48.8-53.2 s (pad 20.5-21.1 s, variant 23.6-27.1 s, comparison 2.0-2.3 s, writing with
  plots 2.6-2.7 s); stage-1 solve launch 132.5 s (offload pass 74.1 s, writing 5.5 s). The
  cached pad would save 20-24 s: about 40% of a plain launch, 18% of a solve launch. Plots
  are 4-5% of a launch, so writing them by default is affordable (open design point).

### 1.6 Verdict for R7 and R16

Thread. The measured reason: with the job in a worker thread the server stayed responsive
within 170 ms worst case over 4,212 polls and three kinds of real job, including a real
stage-1 solve and the writing stage, and the polling took no measurable time from the job.
R7's fall-back is not needed. For R16 the page gets a fresh job state on every poll, so the
elapsed time and stage line can update twice a second for the whole launch.

---

## 2. The child-process alternative (not needed for responsiveness)

What it would look like on Windows, so that the choice can be revisited if cancellation is
wanted.

**Start method.** `multiprocessing.get_start_method()` is `spawn` here. A spawned child
re-imports the package: `import launchsim.sim, launchsim.results_io` took 2.9-4.3 s under
today's load (1,331 modules; a bare interpreter start is 0.18-0.20 s). `python -m launchsim`
is safe for spawn (`src/launchsim/__main__.py:5` guards `main()` with
`if __name__ == "__main__"`); the `launchsim.exe` console script
(`pyproject.toml [project.scripts]`) would have to be tested.

**Two shapes.**

1. `subprocess` running the CLI: `python -m launchsim run <temp.yaml> --results-root <root>`.
   Needs the experiment dict written to a temporary YAML outside the repository with an
   absolute vehicle path (`cli.resolve_vehicle_path`, cli.py:229, resolves a relative path
   against the experiment file's folder or its repository), `cwd` at the repository root so
   `git_info` sees the repository (`cli.repo_root_or_cwd`, cli.py:279). It always runs the
   baseline (`results_io.run_experiment`, results_io.py:836), prints the directory only at
   the end (cli.py:395), reports a refusal as one `error:` line and exit code 1, and cannot
   carry the exploratory label or the server-start provenance without new CLI options.
2. `multiprocessing.Process` running a module-level function of the app module (the same
   composition the thread would run), with a `Pipe` or `Queue` for stage messages. This is
   the better of the two.

**What it can return.** Not the result objects. `pickle.dumps(RunResult)` fails:
`AttributeError: Can't get local object 'hold_rhs_for.<locals>.rhs'`. The local function is
at `src/launchsim/phases/prelude.py:521` (returned by `hold_rhs_for`, line 507) and sits in
`PhaseSpec.rhs` (`phases/engine.py:219`). Field by field: `Result.phases`, `Result.search`
and `Result.trace` fail; `RunResult.resolved` (12,918 B), `Result.metrics` (10,080 B),
`Result.timeseries` (2,816,945 B, 2.5 ms), `Result.events`, `Result.loss_budget`,
`Result.closure` and `Result.assumptions` pickle. `ExperimentResult` fails for the same
reason. So the child returns plain data (stage messages, then the directory's experiment
name and timestamp, or the refusal text), and the server reads the written directory. That
fits section 5.1 of the phase file: the scene reads a results directory, never simulator
objects.

**The cached pad across a process boundary.** The comparison needs the baseline's trace
(`compare.py:935` `trace = baseline.trace`; also 629-630, 1456, 1499), and the trace does
not pickle, so the parent cannot hand a cached baseline to a child, nor can a child hand
one back. The options: (a) a long-lived worker process that keeps the cache in its own
memory between launches (lost when it is cancelled or crashes: the next launch pays the
baseline again plus the 3-4 s import); (b) no cache: every launch pays the baseline
(18-46 s today); (c) make the phase closures picklable, which touches `phases/` and is a
physics-core change needing Plan mode; not worth it for this.

**Cancellation.** `Process.terminate()` (TerminateProcess) stops the child at once with no
`except`/`finally`, so the parent writes the marker:
`results_io.write_failure_marker(out_dir, exc)` (results_io.py:567), with `out_dir` sent
over the pipe right after `make_run_dir`. A thread cannot be cancelled safely; a launch can
only be stopped by stopping the server (section 4).

**Crash isolation.** A hard crash of the child (a fault in native code, the process killed
for memory) leaves the server up; the parent sees a non-zero exit code, marks the job
failed and writes the marker. In the thread design a Python exception is caught by the
worker's wrapper (marker written, job state `failed`, server keeps serving), but a hard
crash takes the server with it and leaves an unmarked directory. None was seen in SP1's
runs or today's.

**Responsiveness.** With a child the server's GIL is free: idle latency (0.6-0.7 ms
kept-alive, 2-26 ms new connection) against 4-5 ms and 17-21 ms with the thread. Both are
far inside a 500 ms period.

**Recommendation: the thread**, behind a small runner interface (`start(form) -> job`,
`snapshot() -> job state`), so a process-based runner (shape 2 with option (a)) can replace
it later without touching the HTTP layer. The reason is the measurement above: the one
thing the phase file feared (a sluggish page for minutes, R7) did not happen, and the
thread keeps the cached pad in memory with no pickling problem. The price is no cancel
button: say in the page that a launch is stopped by stopping the server.

---

## 3. Server safety for a loopback-only tool (R11)

### 3.1 What `http.server` does by default on this Python (verified, `m07_safety_out.txt`)

Line numbers are for `Lib/http/server.py` and `Lib/socketserver.py` of CPython 3.12.11.

| default | where | observed | what to do |
|---|---|---|---|
| `HTTPServer.allow_reuse_address = 1` | server.py:132; socketserver.py:469-470 sets `SO_REUSEADDR` | **On Windows two default `ThreadingHTTPServer` bound the same 127.0.0.1 port with no error.** Socket matrix: reuse+reuse succeeds; plain or exclusive first: second refused (WinError 10048 or 10013) | `allow_reuse_address = False` and, on Windows, `SO_EXCLUSIVEADDRUSE` before `bind` (prototype: second server gets `OSError` WinError 10048). Without this "fail if the port is busy" does not work and another local process can share the port |
| `HTTPServer.server_bind` calls `socket.getfqdn(host)` | server.py:134-139 | `server_name` became `'kubernetes.docker.internal'` (0.3 ms here; a reverse lookup that can take seconds elsewhere) | override `server_bind`: call `socketserver.TCPServer.server_bind(self)`, set `server_name = "127.0.0.1"`, `server_port` |
| `address_family = AF_INET` | socketserver.py:440 | `("127.0.0.1", port)` binds IPv4 only; no dual stack (the dual-stack class exists only in `python -m http.server`'s own main, server.py:1259-1303) | keep; never pass `""`, `"0.0.0.0"` or `"::"`; the bind address is a constant, not an option |
| `log_message` writes a line per request to `sys.stderr` | server.py:575-599 | 12 lines for 7 requests | override: silent for polls; a single ASCII line (through `cli.say`) for a launch, a refusal, an error. A 500 ms poll would otherwise print 2 lines a second, and a console in selection mode blocks whoever writes to it |
| `Server: BaseHTTP/0.6 Python/3.12.11` | server.py:251, 256, 601-603 | on every response | `server_version = "launchsim"`, `sys_version = ""`, `version_string()` returning the bare name |
| `protocol_version = "HTTP/1.0"` | server.py:634 | every response closes the connection; a new connection and thread per request | fine as it is (section 3.3) |
| `default_request_version = "HTTP/0.9"` | server.py:265 | a malformed request line (`NONSENSE`) or a two-word `GET /x` gets **a body with no status line and no headers** | set `default_request_version = "HTTP/1.0"`: measured, both then get `HTTP/1.0 400 ...` and `HTTP/1.0 200 OK` with headers |
| `send_error` | server.py:440-491 | used by the stdlib itself before any app code for 400, 414 (request line over 65,536 bytes), 431 (over 100 headers), 501 (`Unsupported method ('PUT')`): an HTML page, `Content-Type: text/html;charset=utf-8`, the request's text echoed HTML-escaped | put the fixed headers in an `end_headers` override so these responses carry them too (measured: the stdlib's 501 then has `nosniff` etc.); API refusals are sent by the app's own JSON helper |
| no Host check, any `do_<METHOD>` attribute is a route | server.py:417-423 | `GET` with no Host header answered 200 | the guard of 3.2; define only `do_GET` and `do_POST`, and name no helper `do_*` |
| `handle_error` prints a traceback to stderr; the client gets an empty reply | socketserver.py:372-383 | - | wrap the dispatch in `try/except Exception`: JSON 500 with a fixed message, the traceback to stderr as ASCII |
| `StreamRequestHandler.timeout = None` | socketserver.py:803 | a client that connects and sends nothing parks a (daemon) thread for ever | `timeout = 30` on the handler class |
| `ThreadingHTTPServer.daemon_threads = True` | server.py:143 | handler threads never block exit | keep |
| `SimpleHTTPRequestHandler` serves the current directory with listings | server.py:659, 777 | not used | never subclass it; subclass `BaseHTTPRequestHandler`; the page comes from package data (`importlib.resources`, as `replay.py:1176` does), assets from an in-memory table |

### 3.2 The rules, and the prototype that exercises them

`m07_safety.py` implements them in about 120 lines (`AppServer`, `AppHandler`) and sends 38
raw-socket requests; all 38 gave the expected status.

| rule | implementation | checked by the prototype |
|---|---|---|
| Bind 127.0.0.1 only | `AppServer(("127.0.0.1", port), ...)`, IPv4, no reuse, exclusive on Windows | second server on the port: WinError 10048 |
| Host header | exactly one `Host`, lower-cased, equal to `127.0.0.1:<port>` or `localhost:<port>` (the bound port); else 403 | `evil.example:<port>`, `127.0.0.1` without port, `127.0.0.1:<port>.evil.example`, no Host (HTTP/1.0), two Host headers: all 403 |
| Origin | absent, or exactly `http://127.0.0.1:<port>` or `http://localhost:<port>`; else 403. `null` is refused. Applied to GET and POST | other site, same host with another port, `null`: 403 |
| `Sec-Fetch-Site` (defence in depth) | on POST, if present it must be `same-origin` | `cross-site`: 403 |
| POST content type | media type must be `application/json` (parameters such as `charset=utf-8` allowed); else 415. This is what turns a cross-origin POST into a preflighted request; a form or a "simple" `text/plain` POST never reaches the launch code | `text/plain`, `application/x-www-form-urlencoded`, none: 415 |
| No CORS | no `Access-Control-*` header anywhere; no `do_OPTIONS`, so a preflight gets the stdlib's 501 | no such header on any response; OPTIONS: 501 |
| Body size | exactly one numeric `Content-Length` (else 411); over 65,536 bytes: 413 without reading the body; `Transfer-Encoding` present: 400; then `rfile.read(n)` under the handler timeout | no length: 411; 10 MB announced, nothing sent: 413 at once; chunked: 400 |
| Body content | `json.loads(body.decode("utf-8"), parse_constant=<raise>)`; must be an object; unknown keys refused by the form layer | invalid JSON, an array, `NaN`: 400 |
| No file path from the client | a results directory is `<experiment>/<timestamp>`: the experiment must pass `results_io.check_name`'s rules (`NAME_PATTERN` results_io.py:186, `MAX_NAME_LEN` 187, no trailing dot, no device name: lines 205-226), the timestamp `^\d{8}T\d{6}Z(-\d{1,4})?$` (`make_run_dir`'s `-2 ... -1000` suffixes, results_io.py:375-382), and then **both are looked up by exact name in the server's own `iterdir()` listing**; the path used is the one from the listing, and it must resolve inside the results root | `../`, `%2e%2e`, `..%5c..%5cWindows`, `CON`, an upper-cased name, a trailing dot, an extra path segment: all 404; an existing directory: 200 |
| Run names | members of the directory's own run list (metrics.json), never joined to a path unchecked | - |
| No query strings on API routes | refuse a non-empty query with 400; a run selection travels as one path segment `run,run` (names cannot contain `,` or `/`) | `urllib.parse.parse_qs("runs=pad,silo_cold_s1_dry+2t")` gives `'silo_cold_s1_dry 2t'`: a raw `+` becomes a space. Real run names contain `+` and `.` (`silo_cold_s1_dry+8.1t`, experiments/silo_offload_2d.yaml:194-196). In a path segment `+` stays `+` |
| Absolute-form targets | a request target not starting with `/` is refused (400) | `GET http://evil.example/api/job`: 400 |
| Fixed headers on every response | in `end_headers`: `X-Content-Type-Options: nosniff`, `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, `Cross-Origin-Resource-Policy: same-origin`, `X-Frame-Options: DENY` | present on a 200 and on the stdlib's own 501 |
| JSON responses | `json.dumps(obj, allow_nan=False)` (ASCII by default), `Content-Type: application/json; charset=utf-8`, `Content-Length` | - |
| Text responses | `text/html; charset=utf-8` for the page, which stays ASCII and carries `<meta charset>` (R14) | - |
| GET has no side effect | only `POST /api/launches` starts anything or writes anything | - |

What these rules do not do: stop another program of the same user (or another user of the
machine) from calling the API on 127.0.0.1. Such a program can already run
`launchsim run` itself, so this is accepted for a single-user tool; a per-start token in
the URL would be the next step if that changes. Some browsers add a barrier of their own
for public pages that call loopback addresses; the rules above do not rely on it.

### 3.3 HTTP version

Keep `protocol_version = "HTTP/1.0"`. It needs no `Content-Length` discipline, an unread
request body of a refused POST cannot be read as the next request, and no idle connection
holds a thread. Its cost is the new connection per request: 17-21 ms median during a solve
against 4-5 ms kept-alive, both irrelevant at 2 polls a second. If A3 wants many small
requests, HTTP/1.1 is a one-line change with three obligations: every response through one
helper that always sets `Content-Length`; `Connection: close` on every refusal of a request
that has a body; the handler `timeout`.

### 3.4 Content-Security-Policy for the app page

Sent as a header by the app server on `GET /` only (not written into the template, so an
exported standalone page that `site/build.py` frames is not affected):

    Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline';
        style-src 'unsafe-inline'; img-src 'self' data:; font-src 'self';
        connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'

- `default-src 'none'` and no host source anywhere: no request can leave the machine (Q2).
  The replay template's Google Fonts links (`templates/replay.html:7-9`) would be blocked
  under this policy and fall back to the system font stacks; a scene template must not
  carry them.
- `'unsafe-inline'` for script and style is what a single-file template needs (replay.html
  has one inline `<style>` at line 10, one inline `<script>` at 198 and a JSON data block
  at 197). Hardening at no cost to the template: since the app page fetches its data, its
  script is static, so the server can send `script-src 'sha256-<hash of the script text>'`
  computed at start instead of `'unsafe-inline'`; injected inline handlers then cannot run.
  Either way the page must put server strings (run names, refusal messages that echo user
  input) into the DOM with `textContent`, not `innerHTML` (replay.html uses `innerHTML` in
  five places: lines 463, 492, 537, 556, 566).
- `frame-ancestors 'none'` with `X-Frame-Options: DENY`: another site cannot frame the app
  and trick a click on Launch.
- `img-src data:` only if the favicon is an inline data URI (R18); `font-src 'self'` only
  if fonts are vendored and served from an in-memory asset table.

### 3.5 Making the server testable

- A factory `make_server(port, results_root, runner, ...) -> AppServer` that binds and
  returns without serving; `port=0` picks a free port, read back from
  `server.server_address[1]` (the Host and Origin allow-lists are built from that).
- The handler reads its dependencies from `self.server` (results root, runner, page bytes),
  not from module globals, so several servers can live in one test process.
- Fixture: `threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02},
  daemon=True)`; teardown `server.shutdown()` then `server.server_close()`. Measured:
  7-50 ms with `poll_interval` 0.05; 0.2-0.9 s with the default 0.5 (one server 213 ms; two
  servers in a row 446-919 ms). `shutdown()` must be
  called from another thread than `serve_forever` (socketserver.py:247-255: it deadlocks
  otherwise).
- Client in tests: `http.client.HTTPConnection("127.0.0.1", port)` or raw sockets (needed
  for the Host and Origin cases). Never `localhost` (2 s per request here), and not
  `urllib`'s default opener (it reads the system proxy settings).
- The runner is injected: a fake runner that blocks on a `threading.Event` tests the busy
  refusal, the status sequence and a failed job without a solve; one real launch is a
  `@pytest.mark.slow` test (49-133 s today).
- The launch composition is a plain function (`run_launch(form, results_root, cache,
  progress)`), testable without HTTP.
- One lock around "check idle and start" so two POSTs in two handler threads cannot both
  start; the job state the GET handlers read is replaced whole (an immutable snapshot).
- Nothing in the simulator blocks concurrent reads from handler threads while the worker
  computes: no pyplot state (`plots.py:10, 126`), no `warnings` filters, no `chdir`, no
  printing outside `cli.py`; the only module-level caches are two `functools.cache`
  functions (`atmosphere.py:174, 180`).

---

## 4. Shutdown and interruption on Windows

### 4.1 What the run path leaves on disk

- `make_run_dir` creates `results/<experiment>/<timestamp>/` before any run
  (results_io.py:365; in `run_experiment` at line 834).
- `write_run` (results_io.py:687-707) writes in this order: `resolved_config.yaml` (694),
  `metrics.json` (695), each run's `timeseries.csv` and `events.csv` and its plots
  (696-705), `summary.md` last (706).
- `FAILED.txt` is written only by `run_experiment` and `run_sweep`, in
  `except BaseException` in the thread that ran (results_io.py:886-888). The pieces the app
  composes (`sim.run_resolved`, `planar_experiment_result`, `write_run`) never write it.

So an interrupted app launch leaves:

| when the worker stops | on disk |
|---|---|
| during the runs or the offload pass (most of a launch) | an **empty** directory |
| during `write_run` | `resolved_config.yaml`, usually `metrics.json`, some run folders and plots, possibly a truncated last file; no `summary.md` |
| in both cases | **no `FAILED.txt`**, unless the app writes one |

### 4.2 Measured (`m07_interrupt.py`; interrupt simulated with `_thread.interrupt_main()`)

The worker made a run directory with `make_run_dir` under the scratch folder and then
burned CPU for 8 s; the main thread sat in `serve_forever()`; the interrupt was set after
2 s.

| worker | KeyboardInterrupt reached `serve_forever` after | process exit | left on disk |
|---|---|---|---|
| daemon thread | 93 ms | at once | the directory, `entries=[]` |
| daemon thread, main thread calls `write_failure_marker(out_dir, exc)` in its `except` | 78 ms | at once | `FAILED.txt` (first line "This run raised before its results were complete; the files here are partial."; last line "KeyboardInterrupt") |
| non-daemon thread | 72 ms | **only after the worker finished** (8 s later; minutes for a real launch) | `summary.md` (the job ran to its end) |

A real console Ctrl+C was not sent (it would have reached the harness's other processes);
`interrupt_main()` sets the same pending-signal flag, so what is not exercised is only
Windows' console control thread. With a real Ctrl+C the main thread notices when `select`
returns, that is within `poll_interval` (0.5 s by default) plus one GIL switch.

### 4.3 Recommended behaviour

1. `serve_forever()` runs in the main thread; the worker is a **daemon** thread.
2. `command_app` catches `KeyboardInterrupt` itself: `cli.main` catches only `CliError` and
   `OSError` (cli.py:503-510), so otherwise Ctrl+C ends in a traceback. It then calls
   `server.server_close()` (not `shutdown()`, which would deadlock in the serving thread),
   prints one ASCII line and returns 0.
3. If a job is active and its directory exists, the main thread writes the marker before
   returning: `results_io.write_failure_marker(out_dir, exc)` with an exception whose text
   says what happened (for example `LaunchInterrupted("the app server was stopped while
   this launch was running: stage <stage>, <elapsed> s")`), so the directory reads like a
   CLI run stopped with Ctrl+C (which gets `FAILED.txt` through `except BaseException`).
   If the job is in its writing stage, wait for the worker for a few seconds first
   (`worker.join(timeout)`; writing took 2.6-5.5 s today) and write no marker if it
   finished.
4. The worker's own wrapper catches `BaseException` around the runs and the writing, writes
   the marker and sets the job state to `failed` with the exception's type and message. It
   does not re-raise (there is nobody to catch it in a thread).
5. Optional on Windows: `signal.signal(signal.SIGBREAK, signal.default_int_handler)` so
   Ctrl+Break behaves like Ctrl+C instead of killing the process with no clean-up.
6. Nothing can be done for a hard stop (the console window closed, the process killed, a
   power cut, a native crash): the directory keeps neither file. Hence the third label.

### 4.4 How the run browser labels a directory

| files in `results/<experiment>/<timestamp>/` | label | offered for replay |
|---|---|---|
| it is this server's active job | **running** (stage, elapsed) | no |
| `FAILED.txt` (with or without `summary.md`) | **failed**; show the marker's last line (the exception) | no |
| `summary.md`, no `FAILED.txt` | **complete**; then by kind: planar experiment (metrics.json with `runs`, model `planar_2d`: `replay.check_replay_run_dir`, replay.py:166) replayable; a sweep (top-level `summary.md`, no `metrics.json`) and a 1-D run listed as not replayable, with the reason | by kind |
| neither file, not the active job | **incomplete**: "no summary.md and no FAILED.txt: the run was interrupted before its results were written, or another process is still running it" ; show its age from the directory name (`TIMESTAMP_FORMAT`, results_io.py:161) | no |

The app never writes into a directory it did not create in this process and never deletes
one. In particular it does not "adopt" old incomplete directories at start: a
`launchsim run` in another terminal looks exactly the same until it finishes. This matches
the module's own rule: "a directory without summary.md is partial and never mistaken for a
good run" (results_io.py:59-62).

Today's `results/` tree has 15 directories, all with `summary.md`, none with `FAILED.txt`:
6 planar experiment directories (with metrics.json), 3 one-dimensional experiment
directories, and 6 sweep directories without a top-level metrics.json (3 one-dimensional,
3 planar). So the "by kind" column matters on day one.

---

## 5. Port, browser, console output

- **Port.** A fixed default, 8765, with `--port N` (`0` = pick a free port and print it). A
  fixed port keeps the page's origin stable (bookmarks, any per-origin browser storage).
- **Busy port: fail, do not fall back.** One `error:` line and exit code 1, for example
  `error: port 8765 on 127.0.0.1 is in use (another launchsim app?); stop it or pass
  --port N (0 picks a free one)`. A silent fall-back would leave the user's open tab
  talking to another server instance. This needs the bind fix of 3.1: with the stdlib
  default a second server binds the busy port without any error on Windows. Catch the
  `OSError` (WinError 10048) and raise `CliError` with the ASCII text; the raw OS message
  can be localized.
- **Browser.** Not opened by default; `--open` calls `webbrowser.open(url)` once the socket
  is bound (the listen backlog holds the first request until `serve_forever` starts). Off
  by default because tests, agents and repeated restarts must not spawn tabs, and the phase
  file's contract is "prints the URL and serves until interrupted".
- **`--results-root`.** `cli.results_root` needs an experiment path to find the repository
  (cli.py:285-289), which `app` does not have. The app needs its own rule, for example the
  repository found from the package (`cli.find_repo_root`, cli.py:182) or the current
  directory, and a clear `error:` when `experiments/silo_offload_2d.yaml` cannot be found.
- **What it prints** (ASCII, through `cli.say`):

      launchsim app: http://127.0.0.1:8765/   (this machine only)
        results root: D:\...\results
        code: git b69ff0c... (clean) as of server start; restart the server after a code change
        launches are exploratory, not findings
        Ctrl+C stops the server; a launch in progress is then marked FAILED.txt

  then nothing per request; one line per launch (`launch 3 started: results/app/<ts>`,
  `launch 3 done in 133 s` or `launch 3 failed: <type>: <message>`), one line per refused
  launch, and `stopped` at the end. Print `127.0.0.1`, not `localhost` (section 1.5), but
  accept `localhost:<port>` as a Host because a user may type it.

---

## 6. Endpoints (proposal; names for A0 to fix)

Eight routes. Every response carries the fixed headers of 3.2; JSON bodies are ASCII with
`Content-Type: application/json; charset=utf-8`. Errors are
`{"error": "<code>", "message": "<text>"}`.

| # | method and path | purpose | success | refusals |
|---|---|---|---|---|
| 1 | `GET /` | the app page (package template, ASCII, CSP header) | 200 `text/html; charset=utf-8` | - |
| 2 | `GET /api/form` | form defaults, presets, static caveats, server facts | 200 | - |
| 3 | `GET /api/results` | the results directories | 200 | - |
| 4 | `GET /api/results/<experiment>/<timestamp>` | one directory: state, kind, runs, default selection | 200 | 404 `not_found` |
| 5 | `GET /api/results/<experiment>/<timestamp>/scene` and `.../scene/<run>,<run>` | the scene payload for the default or a given run selection | 200 | 404; 409 `not_replayable` (running, failed, incomplete, a sweep, 1-D); 422 `bad_selection` (a run not in the directory, too many runs) |
| 6 | `GET /api/results/<experiment>/<timestamp>/report` | the headline and caveat text of one directory (what `summary.md` reports) | 200 | 404; 409 `not_complete` |
| 7 | `POST /api/launches` | start a launch | **202** with the job | 409 `busy`; 422 `refused`; 400 `bad_json` / `bad_request`; 403; 411; 413; 415 |
| 8 | `GET /api/job` | job status and progress | 200 (always) | - |

Common to all: 403 `host_not_allowed` / `origin_not_allowed`; 400 for a query string or an
absolute-form target; 404 for any other path; 501 from the stdlib for any other method
(including OPTIONS); 500 `internal` with a fixed message for an unexpected exception.
`GET /favicon.ico` is best avoided by an inline icon link in the page; otherwise answer
204.

Shapes (fields are indicative; A0 fixes them with the form and scene surveys):

    2  {"vehicle": "generic_f9_class_2d", "source_experiment": "silo_offload_2d",
        "defaults": {...}, "presets": [{"id": "silo_cold", "label": "...", "values": {...}}],
        "caveats": ["exploratory ...", "calibration +14.3% ...", "..."],
        "expected_s": {"plain": [lo, hi], "stage1_solve": [lo, hi]},
        "server": {"boot_id": "<random per start>", "git": {"hash": "...", "dirty": false}}}

    3  {"results": [{"experiment": "silo_offload_2d", "timestamp": "20261003T112934Z",
                     "state": "complete|failed|running|incomplete",
                     "kind": "experiment|sweep|unknown", "model": "planar_2d|vertical_1d|null",
                     "replayable": true, "label": null, "size_bytes": 74788864}]}
       newest first; built from the listing; a per-directory digest cached by path and mtime
       (metrics.json is 0.15 to 1.84 MB in today's tree, so it is not parsed on every call)

    4  {"experiment": "...", "timestamp": "...", "state": "...", "kind": "...", "model": "...",
        "replayable": true, "why_not": null, "baseline": "pad",
        "runs": [{"name": "pad", "role": "baseline", "status": "inserted"}, ...],
        "default_selection": ["pad", "silo_cold_s1"],
        "failure": null | {"last_line": "<the exception line of FAILED.txt>"},
        "git": {...}, "label": null}

    5  the scene payload of phase file section 5.3 (encoded bytes cached per directory
       and selection; refused with 409 while the directory is the running job's)

    6  {"headline": [...], "caveats": [...], "flags": [...], "exploratory": true, "git": {...}}

    7  request: {"form": {<the form's values, no path, no shared block>}}
       202: {"job": {<as 8>}}
       409: {"error": "busy", "message": "a launch is already running (stage ..., ... s)",
             "job": {...}}
       422: {"error": "refused", "where": "resolve|names|preflight",
             "message": "<the simulator's own ValueError text>"}
       The resolve, the name check and the preflight run inside the POST handler (0.01 s for
       the app's small dict; 0.13-0.52 s for the full committed experiment), so a refusal
       is answered at once and nothing is written; only then is the worker started.

    8  {"boot_id": "...", "job": null}
       {"boot_id": "...", "job": {"id": 3, "state": "running|done|failed",
          "stage": "variant", "stage_index": 2,
          "stages": ["preflight", "pad", "variant", "comparison and offload", "writing"],
          "pad_from_cache": true, "started_utc": "...", "elapsed_s": 41.2,
          "expected_s": [45, 150], "experiment": "app", "timestamp": "20261005T190313Z",
          "error": null | {"type": "ValueError", "message": "..."}}}
       The last job stays readable until the next launch, so a reloaded page still sees how
       it ended. `boot_id` lets a page that outlived a server restart notice it (job ids
       start again at 1). No traceback in a response; it is in FAILED.txt.

The five stage names cost nothing: the app's own composition calls the pieces one after
the other, exactly as the scratch job did (`mark()` in `m07_measure.py`). The only opaque
stage is "comparison and offload" (`planar_experiment_result`: 2 s without an offload,
74 s with one stage-1 solve today).

---

## 7. Where the phase file and the code at HEAD disagree, or the file is incomplete

1. Section 5.6, "bound to 127.0.0.1 and nothing else": with the standard library's
   defaults this is not enforced on Windows. `http.server.HTTPServer.allow_reuse_address =
   1` (CPython 3.12.11 `Lib/http/server.py:132`) sets `SO_REUSEADDR`
   (`Lib/socketserver.py:469-470`), and two default servers bound the same port without an
   error (`m07_safety_out.txt`). The app's server class must turn it off.
2. Section 5.6, "an exception leaves `FAILED.txt` (`write_failure_marker`); the run browser
   shows such a directory as failed": the marker is written only inside
   `results_io.run_experiment` / `run_sweep` (`except BaseException`, results_io.py:886-888),
   which the recommended composition does not call. `app.py` has to write it itself, and an
   interrupted or killed launch leaves a directory with neither file (measured:
   `entries=[]`). The browser needs a third state.
3. Section 5.6 and R11, "launches are POST only" as the protection against a web page: a
   cross-origin "simple" POST (a form, or `fetch` with `text/plain`) reaches a POST handler.
   The Content-Type and Origin checks of 3.2 are needed as well.
4. Section 5.6, the command "registered in `cli.py` like `animate` and `replay`" with
   `--results-root`: `cli.results_root` (cli.py:285-289) derives the default from an
   experiment path, which `app` does not take, and `cli.main` (cli.py:503-510) does not
   catch `KeyboardInterrupt`. Both need handling in `command_app`.
5. Section 5.6, "a searched planar run takes 7 to 25 s": today the pad baseline of
   `silo_offload_2d` took 18.4-46.3 s of wall time (18.1-45.2 s of CPU) on this machine
   under load, and never under 18 s. The progress line's expected range should be wide, or
   taken from the server's own earlier launches.
6. R7, "measure in A4 with a real stage-1 solve": done here (run E: 132.5 s, 1,325 polls,
   median 18.05 ms, p95 31.66 ms, max 97.32 ms). A4 only needs to confirm it in the real
   app.
7. Section 5.6, the child process "cannot share the cache": confirmed, with the reason
   (`RunResult` does not pickle: `prelude.py:521`), and with the refinement that a
   long-lived child can keep its own cache.

---

## 8. Design implications

See the structured summary returned with this report; the list there is the same as the
recommendations made in sections 1.6, 2, 3, 4.3, 4.4, 5 and 6.
