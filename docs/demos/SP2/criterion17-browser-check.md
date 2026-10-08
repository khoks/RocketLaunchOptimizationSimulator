# The real-browser check of exit criterion 17 (recorded at SP2's close)

Exit criterion 17: a page on another loopback port or another host cannot start a launch,
post a frame or make the server build a scene, checked by the guard table in the fast
suite and once with a real browser in the demo. The demo launches of step A7 part 2 did
not repeat the real-browser checks made at the A4b gate (launch posts) and the A5 gate (a
page opened from another site); see [README.md](README.md), "Not in this record". The
independent exit-criteria gate of step A8 found that gap, made the check with its own
harness on 2026-10-08 UTC (2026-10-07 local) at commit cb305a5 (clean tree), and named its
record as the fix. That record, `c17_requests.txt`, follows unchanged except for line
endings. The harness scripts named below stayed in the session's scratch folder, like
every gate script of SP2: the demo records commands, not scripts.

How it was made:

- `node c17_browser.mjs <folder>` started the app from the repository's virtual
  environment, `python -m launchsim app --port 0 --results-root <folder>/root`, in a
  scratch working folder. The scratch root held a copy of
  results/silo_screening_2d/20260930T175743Z (`setup_root.py`).
- The same script served hostile pages from another 127.0.0.1 port, which answers any
  Host. It also ran a DNS-rebinding proxy on a third port that forwarded same-origin
  requests unchanged.
- It opened the pages in headless Microsoft Edge 154 over the DevTools protocol with
  `--host-resolver-rules=MAP evil.example 127.0.0.1`, in these scenarios:
  - A: a page on another 127.0.0.1 port, against the app at 127.0.0.1.
  - A2: the same page, against the app addressed as localhost.
  - D: a page on localhost, against the app at 127.0.0.1.
  - B: a page on evil.example, against the app at 127.0.0.1.
  - B2: a page on evil.example, against the app addressed as evil.example, so the Host
    header names another host.
  - C: DNS rebinding, with the page's same-origin requests forwarded with
    Host evil.example.
  - N1 and N2: top-level navigation to the app with a view hash, from another port and
    from evil.example.
- Each page tried, against the app:
  - form POSTs (text/plain and urlencoded) and fetches (text/plain no-cors and
    application/json) to `/api/launches`;
  - an iframe GET of a scene, and an img GET and a fetch GET of `/api/results`;
  - video starts;
  - frame 0, cancel and finish against a video session that a trusted request had
    opened.
- Every request Edge sent is listed below with its status.
- `c17_raw.py <port> <out.json>` (run by the same script) sent the same requests by raw
  socket. The hostile Host, Origin and Sec-Fetch-Site values all got 403 with the guard's
  code. Positive controls with the app's own headers were accepted: 202 for the launch
  body, 200 for the frame, 201 for a video start.
- `c17_table.py` wrote this table from the two JSON records.

Result:

- No hostile request got a 2xx: 132 browser requests and 64 raw rows.
- `/api/job` stayed idle after every scenario.
- No video session was opened, and no frame was accepted.
- No scene was built by a refused request: the next trusted request for each scene was
  a cold build, and the one after it was a cache hit.
- The results root gained only the positive control's own directory, and the working
  folder stayed empty.
- The five guard tests of the fast suite passed.

---

```text
app port 57951; hostile ports {'plain': 58009, 'proxy': 58010}; run 2026-10-08T02:24:36.578Z to 2026-10-08T02:31:04.996Z

== browser scenario A: page on another 127.0.0.1 port -> app at 127.0.0.1 (page http://127.0.0.1:58009, target http://127.0.0.1:57951)
  2026-10-08T02:25:06.280Z POST    /api/launches [Document] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:07.767Z POST    /api/launches [Document] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=application/x-www-form-urlencoded -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:09.264Z POST    /api/launches [Fetch] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:09.272Z POST    /api/launches [Fetch] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=text/plain;charset=UTF-8 -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:09.281Z POST    /api/launches [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:09.283Z OPTIONS /api/launches [Other] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=None -> 501
  2026-10-08T02:25:09.298Z GET     /scene/silo_screening_2d/20260930T175743Z/pad,silo_failed [Document] Host=127.0.0.1:57951 Origin=None SFS=same-site CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:09.346Z GET     /api/results [Image] Host=127.0.0.1:57951 Origin=None SFS=same-site CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:09.353Z GET     /api/results [Fetch] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=None -> 403 | net::ERR_FAILED cors:MissingAllowOriginHeader
  2026-10-08T02:25:09.364Z POST    /api/videos [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:09.366Z OPTIONS /api/videos [Other] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=None -> 501
  2026-10-08T02:25:09.372Z POST    /api/videos [Fetch] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:09.385Z POST    /api/videos [Document] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:13.369Z POST    /api/videos/lVktZFpxj5ku8_Y4AxoW5Q/frames/0 [Fetch] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:13.378Z POST    /api/videos/lVktZFpxj5ku8_Y4AxoW5Q/frames/0 [Fetch] Host=None Origin=None SFS=None CT=image/png -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:13.385Z POST    /api/videos/lVktZFpxj5ku8_Y4AxoW5Q/frames/0 [Document] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:13.401Z OPTIONS /api/videos/lVktZFpxj5ku8_Y4AxoW5Q/frames/0 [Other] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=None -> 501
  2026-10-08T02:25:14.868Z POST    /api/videos/lVktZFpxj5ku8_Y4AxoW5Q/cancel [Fetch] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:14.875Z POST    /api/videos/lVktZFpxj5ku8_Y4AxoW5Q/cancel [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:14.877Z OPTIONS /api/videos/lVktZFpxj5ku8_Y4AxoW5Q/cancel [Other] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=None -> 501
  2026-10-08T02:25:14.883Z POST    /api/videos/lVktZFpxj5ku8_Y4AxoW5Q/finish [Fetch] Host=127.0.0.1:57951 Origin=http://127.0.0.1:58009 SFS=same-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  scene LRU check (pad,silo_failed): trusted first 2537.7 ms, second 7.4 ms
  session after the frame page: {'state': 'capturing', 'received': 0, 'bytes': 0}
== browser scenario A2: page on another 127.0.0.1 port -> app at localhost (allowed Host name) (page http://127.0.0.1:58009, target http://localhost:57951)
  2026-10-08T02:25:18.392Z POST    /api/launches [Document] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:19.869Z POST    /api/launches [Document] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=application/x-www-form-urlencoded -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:21.364Z POST    /api/launches [Fetch] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:21.373Z POST    /api/launches [Fetch] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=text/plain;charset=UTF-8 -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:21.379Z POST    /api/launches [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:21.382Z OPTIONS /api/launches [Other] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=None -> 501
  2026-10-08T02:25:21.397Z GET     /scene/silo_screening_2d/20260930T175743Z/pad,silo_hot_ramp_on_track [Document] Host=localhost:57951 Origin=None SFS=cross-site CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:21.440Z GET     /api/results [Image] Host=localhost:57951 Origin=None SFS=cross-site CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:21.448Z GET     /api/results [Fetch] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=None -> 403 | net::ERR_FAILED cors:MissingAllowOriginHeader
  2026-10-08T02:25:21.455Z POST    /api/videos [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:21.457Z OPTIONS /api/videos [Other] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=None -> 501
  2026-10-08T02:25:21.461Z POST    /api/videos [Fetch] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:21.475Z POST    /api/videos [Document] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:24.627Z POST    /api/videos/WlH6BkX3zEfxvUuwInRxAg/frames/0 [Fetch] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:24.635Z POST    /api/videos/WlH6BkX3zEfxvUuwInRxAg/frames/0 [Fetch] Host=None Origin=None SFS=None CT=image/png -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:24.655Z POST    /api/videos/WlH6BkX3zEfxvUuwInRxAg/frames/0 [Document] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:24.662Z OPTIONS /api/videos/WlH6BkX3zEfxvUuwInRxAg/frames/0 [Other] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=None -> 501
  2026-10-08T02:25:26.128Z POST    /api/videos/WlH6BkX3zEfxvUuwInRxAg/cancel [Fetch] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:26.142Z POST    /api/videos/WlH6BkX3zEfxvUuwInRxAg/cancel [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:26.144Z OPTIONS /api/videos/WlH6BkX3zEfxvUuwInRxAg/cancel [Other] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=None -> 501
  2026-10-08T02:25:26.153Z POST    /api/videos/WlH6BkX3zEfxvUuwInRxAg/finish [Fetch] Host=localhost:57951 Origin=http://127.0.0.1:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  scene LRU check (pad,silo_hot_ramp_on_track): trusted first 2699.2 ms, second 11.9 ms
  session after the frame page: {'state': 'capturing', 'received': 0, 'bytes': 0}
== browser scenario D: page on localhost:<other port> -> app at 127.0.0.1 (page http://localhost:58009, target http://127.0.0.1:57951)
  2026-10-08T02:25:30.160Z POST    /api/launches [Document] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:31.598Z POST    /api/launches [Document] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=application/x-www-form-urlencoded -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:33.096Z POST    /api/launches [Fetch] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:33.106Z POST    /api/launches [Fetch] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=text/plain;charset=UTF-8 -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:33.114Z POST    /api/launches [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:33.119Z OPTIONS /api/launches [Other] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=None -> 501
  2026-10-08T02:25:33.135Z GET     /scene/silo_screening_2d/20260930T175743Z/silo_cold,silo_cold_lag [Document] Host=127.0.0.1:57951 Origin=None SFS=cross-site CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:33.193Z GET     /api/results [Image] Host=127.0.0.1:57951 Origin=None SFS=cross-site CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:33.199Z GET     /api/results [Fetch] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=None -> 403 | net::ERR_FAILED cors:MissingAllowOriginHeader
  2026-10-08T02:25:33.208Z POST    /api/videos [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:33.210Z OPTIONS /api/videos [Other] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=None -> 501
  2026-10-08T02:25:33.215Z POST    /api/videos [Fetch] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:33.232Z POST    /api/videos [Document] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:36.571Z POST    /api/videos/mZLgs4foKOZDiJ_ROeuGjQ/frames/0 [Fetch] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:36.577Z POST    /api/videos/mZLgs4foKOZDiJ_ROeuGjQ/frames/0 [Fetch] Host=None Origin=None SFS=None CT=image/png -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:36.595Z POST    /api/videos/mZLgs4foKOZDiJ_ROeuGjQ/frames/0 [Document] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:36.619Z OPTIONS /api/videos/mZLgs4foKOZDiJ_ROeuGjQ/frames/0 [Other] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=None -> 501
  2026-10-08T02:25:38.079Z POST    /api/videos/mZLgs4foKOZDiJ_ROeuGjQ/cancel [Fetch] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:38.102Z POST    /api/videos/mZLgs4foKOZDiJ_ROeuGjQ/cancel [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:38.111Z OPTIONS /api/videos/mZLgs4foKOZDiJ_ROeuGjQ/cancel [Other] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=None -> 501
  2026-10-08T02:25:38.133Z POST    /api/videos/mZLgs4foKOZDiJ_ROeuGjQ/finish [Fetch] Host=127.0.0.1:57951 Origin=http://localhost:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  scene LRU check (silo_cold,silo_cold_lag): trusted first 3216.4 ms, second 17.4 ms
  session after the frame page: {'state': 'capturing', 'received': 0, 'bytes': 0}
== browser scenario B: page on evil.example (mapped to 127.0.0.1) -> app at 127.0.0.1 (page http://evil.example:58009, target http://127.0.0.1:57951)
  2026-10-08T02:25:43.265Z POST    /api/launches [Document] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:44.687Z POST    /api/launches [Document] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=application/x-www-form-urlencoded -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:46.197Z POST    /api/launches [Fetch] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:46.219Z POST    /api/launches [Fetch] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=text/plain;charset=UTF-8 -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:46.236Z POST    /api/launches [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:46.244Z OPTIONS /api/launches [Other] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=None -> 501
  2026-10-08T02:25:46.288Z GET     /scene/silo_screening_2d/20260930T175743Z/silo_cold,silo_failed [Document] Host=127.0.0.1:57951 Origin=None SFS=cross-site CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:46.475Z GET     /api/results [Image] Host=127.0.0.1:57951 Origin=None SFS=cross-site CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:46.508Z GET     /api/results [Fetch] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=None -> 403 | net::ERR_FAILED cors:MissingAllowOriginHeader
  2026-10-08T02:25:46.537Z POST    /api/videos [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:46.546Z OPTIONS /api/videos [Other] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=None -> 501
  2026-10-08T02:25:46.568Z POST    /api/videos [Fetch] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:46.599Z POST    /api/videos [Document] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:49.982Z POST    /api/videos/GVhQ4l8lip5Hj75Zmfo8zg/frames/0 [Fetch] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:49.992Z POST    /api/videos/GVhQ4l8lip5Hj75Zmfo8zg/frames/0 [Fetch] Host=None Origin=None SFS=None CT=image/png -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:50.029Z POST    /api/videos/GVhQ4l8lip5Hj75Zmfo8zg/frames/0 [Document] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:50.071Z OPTIONS /api/videos/GVhQ4l8lip5Hj75Zmfo8zg/frames/0 [Other] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=None -> 501
  2026-10-08T02:25:51.476Z POST    /api/videos/GVhQ4l8lip5Hj75Zmfo8zg/cancel [Fetch] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:51.520Z POST    /api/videos/GVhQ4l8lip5Hj75Zmfo8zg/cancel [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:51.524Z OPTIONS /api/videos/GVhQ4l8lip5Hj75Zmfo8zg/cancel [Other] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=None -> 501
  2026-10-08T02:25:51.547Z POST    /api/videos/GVhQ4l8lip5Hj75Zmfo8zg/finish [Fetch] Host=127.0.0.1:57951 Origin=http://evil.example:58009 SFS=cross-site CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  scene LRU check (silo_cold,silo_failed): trusted first 3387.9 ms, second 25.8 ms
  session after the frame page: {'state': 'capturing', 'received': 0, 'bytes': 0}
== browser scenario B2: page on evil.example -> app addressed as evil.example:<app port> (Host evil.example) (page http://evil.example:58009, target http://evil.example:57951)
  2026-10-08T02:25:55.960Z POST    /api/launches [Document] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:57.494Z POST    /api/launches [Document] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=application/x-www-form-urlencoded -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:58.928Z POST    /api/launches [Fetch] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:58.936Z POST    /api/launches [Fetch] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=text/plain;charset=UTF-8 -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:58.943Z POST    /api/launches [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:58.945Z OPTIONS /api/launches [Other] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=None -> 501
  2026-10-08T02:25:58.960Z GET     /scene/silo_screening_2d/20260930T175743Z/silo_cold,silo_instant [Document] Host=evil.example:57951 Origin=None SFS=None CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:25:59.015Z GET     /api/results [Image] Host=evil.example:57951 Origin=None SFS=None CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:59.025Z GET     /api/results [Fetch] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=None -> 403 | net::ERR_FAILED cors:MissingAllowOriginHeader
  2026-10-08T02:25:59.033Z POST    /api/videos [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:25:59.035Z OPTIONS /api/videos [Other] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=None -> 501
  2026-10-08T02:25:59.041Z POST    /api/videos [Fetch] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:25:59.055Z POST    /api/videos [Document] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:26:03.050Z POST    /api/videos/X2GuST-zuX_51hzvkuPInQ/frames/0 [Fetch] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:26:03.075Z POST    /api/videos/X2GuST-zuX_51hzvkuPInQ/frames/0 [Fetch] Host=None Origin=None SFS=None CT=image/png -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:26:03.095Z POST    /api/videos/X2GuST-zuX_51hzvkuPInQ/frames/0 [Document] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:26:03.114Z OPTIONS /api/videos/X2GuST-zuX_51hzvkuPInQ/frames/0 [Other] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=None -> 501
  2026-10-08T02:26:04.555Z POST    /api/videos/X2GuST-zuX_51hzvkuPInQ/cancel [Fetch] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  2026-10-08T02:26:04.562Z POST    /api/videos/X2GuST-zuX_51hzvkuPInQ/cancel [Fetch] Host=None Origin=None SFS=None CT=application/json -> - | net::ERR_FAILED cors:PreflightMissingAllowOriginHeader
  2026-10-08T02:26:04.564Z OPTIONS /api/videos/X2GuST-zuX_51hzvkuPInQ/cancel [Other] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=None -> 501
  2026-10-08T02:26:04.569Z POST    /api/videos/X2GuST-zuX_51hzvkuPInQ/finish [Fetch] Host=evil.example:57951 Origin=http://evil.example:58009 SFS=None CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin
  scene LRU check (silo_cold,silo_instant): trusted first 3859.9 ms, second 12.4 ms
  session after the frame page: {'state': 'capturing', 'received': 0, 'bytes': 0}
== browser scenario C: DNS rebinding: page on evil.example:<proxy>, same-origin requests forwarded unchanged to the app (Host evil.example:<proxy>) (page http://evil.example:58010, target (same origin, proxied))
  2026-10-08T02:26:09.559Z POST    /api/launches [Document] Host=evil.example:58010 Origin=http://evil.example:58010 SFS=None CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:26:09.575Z GET     /favicon.ico [Other] Host=evil.example:58010 Origin=None SFS=None CT=None -> 403
  2026-10-08T02:26:11.027Z POST    /api/launches [Document] Host=evil.example:58010 Origin=http://evil.example:58010 SFS=None CT=application/x-www-form-urlencoded -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:26:12.532Z POST    /api/launches [Fetch] Host=evil.example:58010 Origin=http://evil.example:58010 SFS=None CT=text/plain -> 403
  2026-10-08T02:26:12.543Z POST    /api/launches [Fetch] Host=evil.example:58010 Origin=http://evil.example:58010 SFS=None CT=text/plain;charset=UTF-8 -> 403
  2026-10-08T02:26:12.561Z POST    /api/launches [Fetch] Host=evil.example:58010 Origin=http://evil.example:58010 SFS=None CT=application/json -> 403
  2026-10-08T02:26:12.610Z GET     /scene/silo_screening_2d/20260930T175743Z/pad,silo_instant [Document] Host=evil.example:58010 Origin=None SFS=None CT=None -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:26:12.690Z GET     /api/results [Image] Host=evil.example:58010 Origin=None SFS=None CT=None -> 403
  2026-10-08T02:26:12.708Z GET     /api/results [Fetch] Host=evil.example:58010 Origin=None SFS=None CT=None -> 403
  2026-10-08T02:26:12.722Z POST    /api/videos [Fetch] Host=evil.example:58010 Origin=http://evil.example:58010 SFS=None CT=application/json -> 403
  2026-10-08T02:26:12.740Z POST    /api/videos [Fetch] Host=evil.example:58010 Origin=http://evil.example:58010 SFS=None CT=text/plain -> 403
  2026-10-08T02:26:12.770Z POST    /api/videos [Document] Host=evil.example:58010 Origin=http://evil.example:58010 SFS=None CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:26:15.893Z POST    /api/videos/8O09SmrCqq0cCGvxISKLzw/frames/0 [Fetch] Host=evil.example:58010 Origin=http://evil.example:58010 SFS=None CT=None -> 403
  2026-10-08T02:26:15.901Z POST    /api/videos/8O09SmrCqq0cCGvxISKLzw/frames/0 [Fetch] Host=evil.example:58010 Origin=http://evil.example:58010 SFS=None CT=image/png -> 403
  2026-10-08T02:26:15.911Z POST    /api/videos/8O09SmrCqq0cCGvxISKLzw/frames/0 [Document] Host=evil.example:58010 Origin=http://evil.example:58010 SFS=None CT=text/plain -> 403 | net::ERR_BLOCKED_BY_RESPONSE
  2026-10-08T02:26:15.931Z GET     /favicon.ico [Other] Host=evil.example:58010 Origin=None SFS=None CT=None -> 403
  2026-10-08T02:26:17.370Z POST    /api/videos/8O09SmrCqq0cCGvxISKLzw/cancel [Fetch] Host=evil.example:58010 Origin=http://evil.example:58010 SFS=None CT=text/plain -> 403
  2026-10-08T02:26:17.381Z POST    /api/videos/8O09SmrCqq0cCGvxISKLzw/cancel [Fetch] Host=evil.example:58010 Origin=http://evil.example:58010 SFS=None CT=application/json -> 403
  2026-10-08T02:26:17.393Z POST    /api/videos/8O09SmrCqq0cCGvxISKLzw/finish [Fetch] Host=evil.example:58010 Origin=http://evil.example:58010 SFS=None CT=text/plain -> 403
  scene LRU check (pad,silo_instant): trusted first 2801.4 ms, second 12.3 ms
  session after the frame page: {'state': 'capturing', 'received': 0, 'bytes': 0}
== browser scenario N1: top-level navigation from another 127.0.0.1 port to the app with a view hash (page http://127.0.0.1:58009, target http://127.0.0.1:57951/#dir=silo_screening_2d/20260930T175743Z&runs=pad,silo_hot_full&preset=silo_cold)
  2026-10-08T02:26:21.563Z GET     / [Document] Host=127.0.0.1:57951 Origin=None SFS=same-site CT=None -> 200
  2026-10-08T02:26:21.749Z GET     /api/form [Fetch] Host=127.0.0.1:57951 Origin=None SFS=same-origin CT=None -> 200
  2026-10-08T02:26:21.798Z GET     /api/job [Fetch] Host=127.0.0.1:57951 Origin=None SFS=same-origin CT=None -> 200
  2026-10-08T02:26:21.874Z GET     /api/results [Fetch] Host=127.0.0.1:57951 Origin=None SFS=same-origin CT=None -> 200
  scene LRU check (pad,silo_hot_full): trusted first 2652.7 ms, second 7.7 ms
== browser scenario N2: top-level navigation from evil.example to the app with a view hash (page http://evil.example:58009, target http://127.0.0.1:57951/#dir=silo_screening_2d/20260930T175743Z&runs=silo_cold,silo_hot_full&preset=silo_cold)
  2026-10-08T02:26:33.166Z GET     / [Document] Host=127.0.0.1:57951 Origin=None SFS=cross-site CT=None -> 200
  2026-10-08T02:26:33.309Z GET     /api/form [Fetch] Host=127.0.0.1:57951 Origin=None SFS=same-origin CT=None -> 200
  2026-10-08T02:26:33.349Z GET     /api/job [Fetch] Host=127.0.0.1:57951 Origin=None SFS=same-origin CT=None -> 200
  2026-10-08T02:26:33.397Z GET     /api/results [Fetch] Host=127.0.0.1:57951 Origin=None SFS=same-origin CT=None -> 200
  scene LRU check (silo_cold,silo_hot_full): trusted first 2658.9 ms, second 9.3 ms

== raw sockets (c17_raw.py)
  2026-10-08T02:26:45Z [launch] Host evil.example: POST /api/launches HTTP/1.1 ['Host: evil.example', 'Content-Type: application/json'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:45Z [launch] Host evil.example:<app port>: POST /api/launches HTTP/1.1 ['Host: evil.example:57951', 'Content-Type: application/json'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:45Z [launch] Host evil.example, Origin null: POST /api/launches HTTP/1.1 ['Host: evil.example', 'Origin: null', 'Content-Type: application/json'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:45Z [launch] Origin null: POST /api/launches HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: null', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:45Z [launch] Origin http://evil.example: POST /api/launches HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: http://evil.example', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:45Z [launch] Origin http://127.0.0.1:<other port>: POST /api/launches HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: http://127.0.0.1:57952', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:45Z [launch] Sec-Fetch-Site cross-site: POST /api/launches HTTP/1.1 ['Host: 127.0.0.1:57951', 'Sec-Fetch-Site: cross-site', 'Content-Type: application/json'] -> 403 cross_site (expected 403)
  2026-10-08T02:26:45Z [launch] Sec-Fetch-Site same-site: POST /api/launches HTTP/1.1 ['Host: 127.0.0.1:57951', 'Sec-Fetch-Site: same-site', 'Content-Type: application/json'] -> 403 cross_site (expected 403)
  2026-10-08T02:26:45Z [launch] Origin null + Sec-Fetch-Site cross-site: POST /api/launches HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: null', 'Sec-Fetch-Site: cross-site', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:45Z [launch] own Host, no Origin, text/plain: POST /api/launches HTTP/1.1 ['Host: 127.0.0.1:57951', 'Content-Type: text/plain'] -> 415 unsupported_media_type (expected 415)
  2026-10-08T02:26:45Z [launch] own Host, Origin null, text/plain: POST /api/launches HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: null', 'Content-Type: text/plain'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:45Z [scene] Host evil.example: GET /scene/silo_screening_2d/20260930T175743Z/pad,silo_hot_full_impinged HTTP/1.1 ['Host: evil.example'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:45Z [scene] Host evil.example:<app port>: GET /scene/silo_screening_2d/20260930T175743Z/pad,silo_hot_full_impinged HTTP/1.1 ['Host: evil.example:57951'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:45Z [scene] Host evil.example, Origin null: GET /scene/silo_screening_2d/20260930T175743Z/pad,silo_hot_full_impinged HTTP/1.1 ['Host: evil.example', 'Origin: null'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:45Z [scene] Origin null: GET /scene/silo_screening_2d/20260930T175743Z/pad,silo_hot_full_impinged HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: null'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:45Z [scene] Origin http://evil.example: GET /scene/silo_screening_2d/20260930T175743Z/pad,silo_hot_full_impinged HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: http://evil.example'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:45Z [scene] Origin http://127.0.0.1:<other port>: GET /scene/silo_screening_2d/20260930T175743Z/pad,silo_hot_full_impinged HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: http://127.0.0.1:57952'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:45Z [scene] Sec-Fetch-Site cross-site: GET /scene/silo_screening_2d/20260930T175743Z/pad,silo_hot_full_impinged HTTP/1.1 ['Host: 127.0.0.1:57951', 'Sec-Fetch-Site: cross-site'] -> 403 cross_site (expected 403)
  2026-10-08T02:26:45Z [scene] Sec-Fetch-Site same-site: GET /scene/silo_screening_2d/20260930T175743Z/pad,silo_hot_full_impinged HTTP/1.1 ['Host: 127.0.0.1:57951', 'Sec-Fetch-Site: same-site'] -> 403 cross_site (expected 403)
  2026-10-08T02:26:45Z [scene] Origin null + Sec-Fetch-Site cross-site: GET /scene/silo_screening_2d/20260930T175743Z/pad,silo_hot_full_impinged HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: null', 'Sec-Fetch-Site: cross-site'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:45Z [results] Host evil.example: GET /api/results HTTP/1.1 ['Host: evil.example'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:45Z [results] Host evil.example:<app port>: GET /api/results HTTP/1.1 ['Host: evil.example:57951'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:45Z [results] Host evil.example, Origin null: GET /api/results HTTP/1.1 ['Host: evil.example', 'Origin: null'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:45Z [results] Origin null: GET /api/results HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: null'] -> 403 origin_not_allowed (expected 403)
  [scene timing] pad,silo_hot_full_impinged: {'group': 'scene timing', 'case': 'pad,silo_hot_full_impinged', 'first_ms': 2322.1, 'second_ms': 11.2, 'status': [200, 200]}
  2026-10-08T02:26:48Z [video start] Host evil.example: POST /api/videos HTTP/1.1 ['Host: evil.example', 'Content-Type: application/json'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:48Z [video start] Host evil.example:<app port>: POST /api/videos HTTP/1.1 ['Host: evil.example:57951', 'Content-Type: application/json'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:48Z [video start] Host evil.example, Origin null: POST /api/videos HTTP/1.1 ['Host: evil.example', 'Origin: null', 'Content-Type: application/json'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:48Z [video start] Origin null: POST /api/videos HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: null', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:48Z [video start] Origin http://evil.example: POST /api/videos HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: http://evil.example', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:48Z [video start] Origin http://127.0.0.1:<other port>: POST /api/videos HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: http://127.0.0.1:57952', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:48Z [video start] Sec-Fetch-Site cross-site: POST /api/videos HTTP/1.1 ['Host: 127.0.0.1:57951', 'Sec-Fetch-Site: cross-site', 'Content-Type: application/json'] -> 403 cross_site (expected 403)
  2026-10-08T02:26:48Z [video start] Sec-Fetch-Site same-site: POST /api/videos HTTP/1.1 ['Host: 127.0.0.1:57951', 'Sec-Fetch-Site: same-site', 'Content-Type: application/json'] -> 403 cross_site (expected 403)
  2026-10-08T02:26:48Z [video start] Origin null + Sec-Fetch-Site cross-site: POST /api/videos HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: null', 'Sec-Fetch-Site: cross-site', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:48Z [frame] Host evil.example: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/frames/0 HTTP/1.1 ['Host: evil.example', 'Content-Type: image/png'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:48Z [frame] Host evil.example:<app port>: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/frames/0 HTTP/1.1 ['Host: evil.example:57951', 'Content-Type: image/png'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:48Z [frame] Host evil.example, Origin null: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/frames/0 HTTP/1.1 ['Host: evil.example', 'Origin: null', 'Content-Type: image/png'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:48Z [frame] Origin null: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/frames/0 HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: null', 'Content-Type: image/png'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:48Z [frame] Origin http://evil.example: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/frames/0 HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: http://evil.example', 'Content-Type: image/png'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:48Z [frame] Origin http://127.0.0.1:<other port>: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/frames/0 HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: http://127.0.0.1:57952', 'Content-Type: image/png'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:48Z [frame] Sec-Fetch-Site cross-site: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/frames/0 HTTP/1.1 ['Host: 127.0.0.1:57951', 'Sec-Fetch-Site: cross-site', 'Content-Type: image/png'] -> 403 cross_site (expected 403)
  2026-10-08T02:26:48Z [frame] Sec-Fetch-Site same-site: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/frames/0 HTTP/1.1 ['Host: 127.0.0.1:57951', 'Sec-Fetch-Site: same-site', 'Content-Type: image/png'] -> 403 cross_site (expected 403)
  2026-10-08T02:26:48Z [frame] Origin null + Sec-Fetch-Site cross-site: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/frames/0 HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: null', 'Sec-Fetch-Site: cross-site', 'Content-Type: image/png'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:48Z [cancel] Host evil.example: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/cancel HTTP/1.1 ['Host: evil.example', 'Content-Type: application/json'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:48Z [finish] Host evil.example: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/finish HTTP/1.1 ['Host: evil.example', 'Content-Type: application/json'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:48Z [cancel] Host evil.example:<app port>: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/cancel HTTP/1.1 ['Host: evil.example:57951', 'Content-Type: application/json'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:48Z [finish] Host evil.example:<app port>: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/finish HTTP/1.1 ['Host: evil.example:57951', 'Content-Type: application/json'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:48Z [cancel] Host evil.example, Origin null: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/cancel HTTP/1.1 ['Host: evil.example', 'Origin: null', 'Content-Type: application/json'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:48Z [finish] Host evil.example, Origin null: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/finish HTTP/1.1 ['Host: evil.example', 'Origin: null', 'Content-Type: application/json'] -> 403 host_not_allowed (expected 403)
  2026-10-08T02:26:48Z [cancel] Origin null: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/cancel HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: null', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:48Z [finish] Origin null: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/finish HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: null', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:48Z [cancel] Origin http://evil.example: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/cancel HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: http://evil.example', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:48Z [finish] Origin http://evil.example: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/finish HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: http://evil.example', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:48Z [cancel] Origin http://127.0.0.1:<other port>: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/cancel HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: http://127.0.0.1:57952', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:48Z [finish] Origin http://127.0.0.1:<other port>: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/finish HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: http://127.0.0.1:57952', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:48Z [cancel] Sec-Fetch-Site cross-site: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/cancel HTTP/1.1 ['Host: 127.0.0.1:57951', 'Sec-Fetch-Site: cross-site', 'Content-Type: application/json'] -> 403 cross_site (expected 403)
  2026-10-08T02:26:49Z [finish] Sec-Fetch-Site cross-site: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/finish HTTP/1.1 ['Host: 127.0.0.1:57951', 'Sec-Fetch-Site: cross-site', 'Content-Type: application/json'] -> 403 cross_site (expected 403)
  2026-10-08T02:26:49Z [cancel] Sec-Fetch-Site same-site: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/cancel HTTP/1.1 ['Host: 127.0.0.1:57951', 'Sec-Fetch-Site: same-site', 'Content-Type: application/json'] -> 403 cross_site (expected 403)
  2026-10-08T02:26:49Z [finish] Sec-Fetch-Site same-site: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/finish HTTP/1.1 ['Host: 127.0.0.1:57951', 'Sec-Fetch-Site: same-site', 'Content-Type: application/json'] -> 403 cross_site (expected 403)
  2026-10-08T02:26:49Z [cancel] Origin null + Sec-Fetch-Site cross-site: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/cancel HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: null', 'Sec-Fetch-Site: cross-site', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:49Z [finish] Origin null + Sec-Fetch-Site cross-site: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/finish HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: null', 'Sec-Fetch-Site: cross-site', 'Content-Type: application/json'] -> 403 origin_not_allowed (expected 403)
  2026-10-08T02:26:49Z [frame] positive control: own Host, no Origin: POST /api/videos/A6OPq01bUX1q8Bm2xnOLAg/frames/0 HTTP/1.1 ['Host: 127.0.0.1:57951', 'Content-Type: image/png'] -> 200  (expected 200)
  2026-10-08T02:26:49Z [control] GET /api/results with the app's own Host: GET /api/results HTTP/1.1 ['Host: 127.0.0.1:57951'] -> 200  (expected 200)
  2026-10-08T02:26:49Z [control] dry run with the app's own Host and Origin: POST /api/launches HTTP/1.1 ['Host: 127.0.0.1:57951', 'Origin: http://127.0.0.1:57951', 'Content-Type: application/json'] -> 200  (expected 200)

== checks
PASS pre: /api/job idle :: {"state":"idle","id":null}
PASS pre: the same body as a trusted dry run is a valid launch (200, refused null) :: status 200 refused null
PASS pre: a scene build is distinguishable by time (cold min > 5 x warm max) :: cold 4317.9 / 3461.5 ms, warm 59.3 / 7.8 ms
PASS A after the launch attempts: /api/job still idle (no job id, same boot id) :: state idle id null
PASS A: no video session was opened by the page (a trusted start then gets 201) :: status 201 {"video":{"id":"lVktZFpxj5ku8_Y4AxoW5Q","state":"capturing","format":"mp4","fps":20,"frames":10,"received":0,"width":960,"height":540,"bytes":0,"budget_bytes":5
PASS A: no frame was posted and the session was not ended by the page :: {"state":"capturing","received":0,"bytes":0}
PASS A after the frame attempts: /api/job still idle (no job id, same boot id) :: state idle id null
PASS A: the page did not make the server build its scene (trusted first request is a cold build) :: first 2537.7 ms vs second 7.4 ms (control cold 3461.5 ms)
PASS A2 after the launch attempts: /api/job still idle (no job id, same boot id) :: state idle id null
PASS A2: no video session was opened by the page (a trusted start then gets 201) :: status 201 {"video":{"id":"WlH6BkX3zEfxvUuwInRxAg","state":"capturing","format":"mp4","fps":20,"frames":10,"received":0,"width":960,"height":540,"bytes":0,"budget_bytes":5
PASS A2: no frame was posted and the session was not ended by the page :: {"state":"capturing","received":0,"bytes":0}
PASS A2 after the frame attempts: /api/job still idle (no job id, same boot id) :: state idle id null
PASS A2: the page did not make the server build its scene (trusted first request is a cold build) :: first 2699.2 ms vs second 11.9 ms (control cold 3461.5 ms)
PASS D after the launch attempts: /api/job still idle (no job id, same boot id) :: state idle id null
PASS D: no video session was opened by the page (a trusted start then gets 201) :: status 201 {"video":{"id":"mZLgs4foKOZDiJ_ROeuGjQ","state":"capturing","format":"mp4","fps":20,"frames":10,"received":0,"width":960,"height":540,"bytes":0,"budget_bytes":5
PASS D: no frame was posted and the session was not ended by the page :: {"state":"capturing","received":0,"bytes":0}
PASS D after the frame attempts: /api/job still idle (no job id, same boot id) :: state idle id null
PASS D: the page did not make the server build its scene (trusted first request is a cold build) :: first 3216.4 ms vs second 17.4 ms (control cold 3461.5 ms)
PASS B after the launch attempts: /api/job still idle (no job id, same boot id) :: state idle id null
PASS B: no video session was opened by the page (a trusted start then gets 201) :: status 201 {"video":{"id":"GVhQ4l8lip5Hj75Zmfo8zg","state":"capturing","format":"mp4","fps":20,"frames":10,"received":0,"width":960,"height":540,"bytes":0,"budget_bytes":5
PASS B: no frame was posted and the session was not ended by the page :: {"state":"capturing","received":0,"bytes":0}
PASS B after the frame attempts: /api/job still idle (no job id, same boot id) :: state idle id null
PASS B: the page did not make the server build its scene (trusted first request is a cold build) :: first 3387.9 ms vs second 25.8 ms (control cold 3461.5 ms)
PASS B2 after the launch attempts: /api/job still idle (no job id, same boot id) :: state idle id null
PASS B2: no video session was opened by the page (a trusted start then gets 201) :: status 201 {"video":{"id":"X2GuST-zuX_51hzvkuPInQ","state":"capturing","format":"mp4","fps":20,"frames":10,"received":0,"width":960,"height":540,"bytes":0,"budget_bytes":5
PASS B2: no frame was posted and the session was not ended by the page :: {"state":"capturing","received":0,"bytes":0}
PASS B2 after the frame attempts: /api/job still idle (no job id, same boot id) :: state idle id null
PASS B2: the page did not make the server build its scene (trusted first request is a cold build) :: first 3859.9 ms vs second 12.4 ms (control cold 3461.5 ms)
PASS C after the launch attempts: /api/job still idle (no job id, same boot id) :: state idle id null
PASS C: no video session was opened by the page (a trusted start then gets 201) :: status 201 {"video":{"id":"8O09SmrCqq0cCGvxISKLzw","state":"capturing","format":"mp4","fps":20,"frames":10,"received":0,"width":960,"height":540,"bytes":0,"budget_bytes":5
PASS C: no frame was posted and the session was not ended by the page :: {"state":"capturing","received":0,"bytes":0}
PASS C after the frame attempts: /api/job still idle (no job id, same boot id) :: state idle id null
PASS C: the page did not make the server build its scene (trusted first request is a cold build) :: first 2801.4 ms vs second 12.3 ms (control cold 3461.5 ms)
PASS N1: the app page opened by another site sent no POST and asked for no scene or panel :: 4 requests: GET / 200; GET /api/form 200; GET /api/job 200; GET /api/results 200
PASS N1: /api/job still idle (no job id, same boot id) :: state idle id null
PASS N1: the hash's scene was not built (trusted first request is a cold build) :: first 2652.7 ms vs second 7.7 ms
PASS N2: the app page opened by another site sent no POST and asked for no scene or panel :: 4 requests: GET / 200; GET /api/form 200; GET /api/job 200; GET /api/results 200
PASS N2: /api/job still idle (no job id, same boot id) :: state idle id null
PASS N2: the hash's scene was not built (trusted first request is a cold build) :: first 2658.9 ms vs second 9.3 ms
PASS no hostile request to the app (scenarios A-C) got a 2xx :: 0 of 132 browser requests: 
PASS rebinding proxy: every forwarded request answered 403 by the app :: POST /api/launches host=evil.example:58010 -> 403; GET /favicon.ico host=evil.example:58010 -> 403; POST /api/launches host=evil.example:58010 -> 403; POST /api/launches host=evil.example:58010 -> 403; POST /api/launches host=evil.example:58010 -> 403; POST /api/launches host=evil.example:58010 -> 4
PASS raw-socket script exit 0 :: exit 0
PASS positive control: the hostile pages' launch body, sent with the app's own headers, starts a launch (202) :: status 202 {"job":{"boot_id":"299ffbb625a9a3bb","id":1,"state":"running","stage":"preflight","stage_index":0,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-08T02:26:49Z","el
PASS results root: nothing changed but the positive control's one new directory :: {"addedTop":["app/","app/20261008T022650Z"],"removed":0,"changed":0}
PASS work folder (where MP4s go): nothing left by any session :: []
PASS raw: after the launch attempts: /api/job idle :: 200 state idle id None
PASS raw: scene: the refused requests built nothing (first trusted request is a cold build) :: first 2322.1 ms, second 11.2 ms
PASS raw: video start: no session was opened by the refused requests (a trusted start gets 201) :: 201
PASS raw: frame: no frame accepted and the session not ended :: state capturing received 0 bytes 0
PASS raw: frame positive control: the same PNG with the app's own headers is accepted :: 200 received 1
PASS raw: at the end: /api/job idle :: 200 state idle id None
PASS raw: every raw case gave its expected status :: 64 rows, 0 unexpected: []

browser requests recorded: 132; raw rows: 64
```
