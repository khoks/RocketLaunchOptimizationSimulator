# SP2 demo: the API record of one launch and one refusal (exit criterion 14)

Server `http://127.0.0.1:58302/` started 2026-10-07T12:56:59.457Z UTC from the clean tree at fb34b2417c56 (its start lines are in README.md). The page was driven in headless Edge over the DevTools protocol; this is what its network log recorded for demo launch 1 and demo step 6, raw: request and response headers that bear on the server's guard, every body, and wall-clock times. Nothing is redacted (there are no secrets: everything is on 127.0.0.1); the only change to the bodies is that non-ASCII characters are written as `\uXXXX` escapes so this file is ASCII, and JSON bodies are re-indented. Every app launch is exploratory and not a finding; the numbers in these bodies are the app's and carry the caveats the results panel shows beside them.

## 1. Launch 1: the silo_cold preset (demo step 1)

The page's POST that started the launch, every GET /api/job poll until the job was done (one every 500 ms, the page's JOB_POLL_MS), then the two GET /api/results the page made (the run list refreshed when the directory was named, 0.55 s after the POST and while the job ran; and again at completion) and the GET /api/results/app/<timestamp> at completion (the new directory opened: its results panel and scene selection). Times are wall-clock UTC. Elapsed times are from the launch POST at 2026-10-07T12:59:46.577Z.

### 1.1 The launch request and its answer

#### POST /api/launches

- request sent: 2026-10-07T12:59:46.577Z (CDP `wallTime` of `Network.requestWillBeSent`)
- response received: 2026-10-07T12:59:46.626Z; body complete: 2026-10-07T12:59:46.626Z (the driver's clock at `responseReceived` and `loadingFinished`)
- status: 202 Accepted

Request headers as `Network.requestWillBeSent` reports them (the renderer's: Content-Type and the empty Referer of the page's no-referrer policy; the network layer's additions, Host, Origin and the Sec-Fetch-* headers the server's guard reads, travel in `requestWillBeSentExtraInfo`, which this log did not subscribe to):

```
Referer: 
Content-Type: application/json
```

Request body:

```json
{
 "site": "silo",
 "stroke_m": 100,
 "push_by": "net_accel_g",
 "net_accel_g": 3,
 "carriage_mass_t": 0,
 "exhaust_impingement_fraction": 0,
 "ramp_by": "time_release",
 "t_ign_s": 0.5,
 "startup": "vehicle_default",
 "propellant": "full",
 "preset": "silo_cold"
}
```

Response headers:

```
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Cache-Control: no-store
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Content-Length: 498
Date: Wed, 07 Oct 2026 12:59:46 GMT
Content-Type: application/json; charset=utf-8
Server: launchsim
```

Response body:

```json
{
 "job": {
  "boot_id": "50675015f92e51ba",
  "id": 1,
  "state": "running",
  "stage": "preflight",
  "stage_index": 0,
  "stages": [
   "preflight",
   "pad",
   "variant",
   "comparison",
   "writing"
  ],
  "started_utc": "2026-10-07T12:59:46Z",
  "elapsed_s": 0.0,
  "expected_s": [
   16.0,
   100.0
  ],
  "longer_than_expected": false,
  "pad_cached": false,
  "description": "silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup",
  "preset": "silo_cold",
  "started_from_preset": "silo_cold",
  "preset_edited": false,
  "directory": null,
  "outcome": null
 }
}
```


### 1.2 The job polls

55 GET /api/job exchanges between 2026-10-07T12:59:47.124Z and 2026-10-07T13:00:15.070Z, each answered 200. Every response body, raw, one per row; the elapsed time is from the launch POST.

| # | sent (UTC) | +s | status | response body |
|---|---|---|---|---|
| 1 | 2026-10-07T12:59:47.124Z | 0.547 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":0.5,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 2 | 2026-10-07T12:59:47.641Z | 1.064 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":1.0,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 3 | 2026-10-07T12:59:48.181Z | 1.604 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":1.6,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 4 | 2026-10-07T12:59:48.699Z | 2.122 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":2.1,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 5 | 2026-10-07T12:59:49.212Z | 2.635 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":2.6,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 6 | 2026-10-07T12:59:49.724Z | 3.147 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":3.1,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 7 | 2026-10-07T12:59:50.242Z | 3.665 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":3.6,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 8 | 2026-10-07T12:59:50.759Z | 4.182 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":4.1,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 9 | 2026-10-07T12:59:51.262Z | 4.685 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":4.7,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 10 | 2026-10-07T12:59:51.773Z | 5.196 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":5.2,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 11 | 2026-10-07T12:59:52.286Z | 5.709 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":5.7,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 12 | 2026-10-07T12:59:52.806Z | 6.229 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":6.2,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 13 | 2026-10-07T12:59:53.335Z | 6.758 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":6.7,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 14 | 2026-10-07T12:59:53.858Z | 7.281 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":7.2,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 15 | 2026-10-07T12:59:54.377Z | 7.800 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":7.8,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 16 | 2026-10-07T12:59:54.883Z | 8.306 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":8.3,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 17 | 2026-10-07T12:59:55.411Z | 8.834 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":8.8,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 18 | 2026-10-07T12:59:55.922Z | 9.345 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":9.3,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 19 | 2026-10-07T12:59:56.435Z | 9.858 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":9.8,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 20 | 2026-10-07T12:59:56.951Z | 10.374 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":10.3,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 21 | 2026-10-07T12:59:57.479Z | 10.902 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":10.9,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 22 | 2026-10-07T12:59:58.000Z | 11.423 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":11.4,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 23 | 2026-10-07T12:59:58.520Z | 11.943 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"pad","stage_index":1,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":11.9,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 24 | 2026-10-07T12:59:59.034Z | 12.457 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":12.4,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 25 | 2026-10-07T12:59:59.543Z | 12.966 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":12.9,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 26 | 2026-10-07T13:00:00.058Z | 13.481 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":13.5,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 27 | 2026-10-07T13:00:00.616Z | 14.039 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":14.0,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 28 | 2026-10-07T13:00:01.133Z | 14.556 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":14.5,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 29 | 2026-10-07T13:00:01.638Z | 15.061 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":15.0,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 30 | 2026-10-07T13:00:02.157Z | 15.580 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":15.5,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 31 | 2026-10-07T13:00:02.675Z | 16.098 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":16.1,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 32 | 2026-10-07T13:00:03.191Z | 16.614 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":16.6,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 33 | 2026-10-07T13:00:03.706Z | 17.129 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":17.1,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 34 | 2026-10-07T13:00:04.222Z | 17.645 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":17.6,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 35 | 2026-10-07T13:00:04.728Z | 18.151 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":18.1,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 36 | 2026-10-07T13:00:05.244Z | 18.667 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":18.6,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 37 | 2026-10-07T13:00:05.755Z | 19.178 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":19.1,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 38 | 2026-10-07T13:00:06.262Z | 19.685 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":19.7,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 39 | 2026-10-07T13:00:06.772Z | 20.195 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":20.2,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 40 | 2026-10-07T13:00:07.295Z | 20.718 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":20.7,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 41 | 2026-10-07T13:00:07.813Z | 21.236 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":21.2,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 42 | 2026-10-07T13:00:08.336Z | 21.759 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":21.7,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 43 | 2026-10-07T13:00:08.880Z | 22.303 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":22.3,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 44 | 2026-10-07T13:00:09.401Z | 22.824 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":22.8,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 45 | 2026-10-07T13:00:09.915Z | 23.338 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":23.3,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 46 | 2026-10-07T13:00:10.431Z | 23.854 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":23.8,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 47 | 2026-10-07T13:00:10.935Z | 24.358 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":24.3,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 48 | 2026-10-07T13:00:11.458Z | 24.881 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":24.8,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 49 | 2026-10-07T13:00:11.983Z | 25.406 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":25.4,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 50 | 2026-10-07T13:00:12.497Z | 25.920 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"variant","stage_index":2,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":25.9,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 51 | 2026-10-07T13:00:13.002Z | 26.425 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"comparison","stage_index":3,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":26.4,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 52 | 2026-10-07T13:00:13.522Z | 26.945 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"comparison","stage_index":3,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":26.9,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 53 | 2026-10-07T13:00:14.039Z | 27.462 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"comparison","stage_index":3,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":27.4,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 54 | 2026-10-07T13:00:14.555Z | 27.978 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"running","stage":"writing","stage_index":4,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":28.0,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":null}` |
| 55 | 2026-10-07T13:00:15.070Z | 28.493 | 200 | `{"boot_id":"50675015f92e51ba","id":1,"state":"done","stage":"writing","stage_index":4,"stages":["preflight","pad","variant","comparison","writing"],"started_utc":"2026-10-07T12:59:46Z","elapsed_s":28.0,"expected_s":[16.0,100.0],"longer_than_expected":false,"pad_cached":false,"description":"silo 100 m deep, 3 g0 net; ramp start +0.5 s from release; the vehicle's own startup","preset":"silo_cold","started_from_preset":"silo_cold","preset_edited":false,"directory":{"experiment":"app","timestamp":"20261007T125946Z"},"outcome":{"kind":"complete","message":"complete: pad, silo_cold reached the target orbit; no flag, no failed verification and no result marked as a suspected bug (status bug_suspect) recorded; the screening check against the instant-start yardsticks (an assisted run may not beat the instant-start silo's gain at its release speed) was not made: it needs silo_instant and pad_instant in one directory, and this directory does not have both","notes":[],"reproduces":["silo_cold: same configuration as the committed silo_cold in experiments/silo_offload_2d.yaml at commit fb34b2417c56: a reproduction, not new evidence (the code may differ from the recorded run's)"],"field":null}}` |

### 1.3 The run list refreshed when the directory was named (during the run)

Sent 7 ms after the first job poll (section 1.2, row 1) named the directory; the job was still running (the body's app row has state `running` and the `running` object at its end names the directory).

#### GET /api/results

- request sent: 2026-10-07T12:59:47.131Z (CDP `wallTime` of `Network.requestWillBeSent`)
- response received: 2026-10-07T12:59:47.435Z; body complete: 2026-10-07T12:59:47.437Z (the driver's clock at `responseReceived` and `loadingFinished`)
- status: 200 OK

Request headers as `Network.requestWillBeSent` reports them (the renderer's: Content-Type and the empty Referer of the page's no-referrer policy; the network layer's additions, Host, Origin and the Sec-Fetch-* headers the server's guard reads, travel in `requestWillBeSentExtraInfo`, which this log did not subscribe to):

```
Referer: 
```

Response headers:

```
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Cache-Control: no-store
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Content-Length: 11578
Date: Wed, 07 Oct 2026 12:59:47 GMT
Content-Type: application/json; charset=utf-8
Server: launchsim
```

Response body:

```json
{
 "groups": [
  {
   "name": "app",
   "title": "App runs (exploratory)",
   "rows": [
    {
     "experiment": "app",
     "timestamp": "20261007T125946Z",
     "group": "app",
     "state": "running",
     "playable": false,
     "reason": "running",
     "line": null,
     "label": null,
     "git": {
      "hash": "unknown",
      "state": "unknown"
     },
     "server_start": null,
     "size_bytes": null,
     "size_is_lower_bound": false,
     "run_count": 0,
     "model": null,
     "kind": null,
     "outcome": null,
     "description": "launch in progress",
     "cited_in": []
    }
   ]
  },
  {
   "name": "recorded",
   "title": "Recorded experiments",
   "rows": [
    {
     "experiment": "silo_offload_2d_readme",
     "timestamp": "20261003T112956Z",
     "group": "recorded",
     "state": "complete",
     "playable": true,
     "reason": null,
     "line": null,
     "label": null,
     "git": {
      "hash": "b3150c1754ee",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 17635887,
     "size_is_lower_bound": false,
     "run_count": 5,
     "model": "planar_2d",
     "kind": "experiment",
     "outcome": {
      "kind": "complete",
      "message": "complete: pad, silo_cold reached the target orbit; no flag, no failed verification and no result marked as a suspected bug (status bug_suspect) recorded; the screening check against the instant-start yardsticks (an assisted run may not beat the instant-start silo's gain at its release speed) was not made: it needs silo_instant and pad_instant in one directory, and this directory does not have both"
     },
     "description": "silo_offload_2d_readme: 5 runs",
     "cited_in": [
      {
       "path": "docs/findings/RQ1-fuel-offload-2d.md",
       "title": "RQ1 (preliminary, 2-D): stage-1 propellant a silo push replaces at fixed payload"
      }
     ]
    },
    {
     "experiment": "silo_offload_2d",
     "timestamp": "20261003T112949Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "sweep",
     "line": null,
     "label": null,
     "git": {
      "hash": "b3150c1754ee",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 85489444,
     "size_is_lower_bound": false,
     "run_count": 20,
     "model": null,
     "kind": "sweep",
     "outcome": null,
     "description": "silo_offload_2d: a sweep of 20 points",
     "cited_in": [
      {
       "path": "docs/findings/RQ1-fuel-offload-2d.md",
       "title": "RQ1 (preliminary, 2-D): stage-1 propellant a silo push replaces at fixed payload"
      }
     ]
    },
    {
     "experiment": "silo_offload_2d",
     "timestamp": "20261003T112934Z",
     "group": "recorded",
     "state": "complete",
     "playable": true,
     "reason": null,
     "line": null,
     "label": null,
     "git": {
      "hash": "b3150c1754ee",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 74260469,
     "size_is_lower_bound": false,
     "run_count": 19,
     "model": "planar_2d",
     "kind": "experiment",
     "outcome": {
      "kind": "flagged",
      "message": "offload case silo_cold_s2: verification failed (+15.36 kg against 2.6 kg): the gross removal is a flagged lower bound and the net figure, which also subtracts a flagged pad control, is uncertain both ways"
     },
     "description": "silo_offload_2d: 19 runs",
     "cited_in": [
      {
       "path": "docs/findings/RQ1-fuel-offload-2d.md",
       "title": "RQ1 (preliminary, 2-D): stage-1 propellant a silo push replaces at fixed payload"
      }
     ]
    },
    {
     "experiment": "silo_bridge_2d_readme",
     "timestamp": "20260930T185034Z",
     "group": "recorded",
     "state": "complete",
     "playable": true,
     "reason": null,
     "line": null,
     "label": null,
     "git": {
      "hash": "7ad381f227a9",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 14318581,
     "size_is_lower_bound": false,
     "run_count": 4,
     "model": "planar_2d",
     "kind": "experiment",
     "outcome": {
      "kind": "complete",
      "message": "complete: pad, pad_instant, silo_instant, silo_cold reached the target orbit; no flag, no failed verification and no result marked as a suspected bug (status bug_suspect) recorded; the screening check against the instant-start yardsticks (an assisted run may not beat the instant-start silo's gain at its release speed) was not made: it needs silo_instant and pad_instant in one directory, and this directory does not have both"
     },
     "description": "silo_bridge_2d_readme: 4 runs",
     "cited_in": [
      {
       "path": "docs/findings/RQ2-ignition-timing-1d.md",
       "title": "RQ2 (preliminary, 1-D): hot or cold start on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ2-ignition-timing-2d.md",
       "title": "RQ2 (preliminary, 2-D): ignition timing on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-1d.md",
       "title": "RQ3 (preliminary, 1-D): vertical silo screening, concept A"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-2d.md",
       "title": "RQ3 (preliminary, 2-D): vertical silo screening on the planar model"
      },
      {
       "path": "docs/findings/RQ6-aero-2d-preliminary.md",
       "title": "RQ6 (preliminary, 2-D): unthrottled max-Q, q-alpha and drag deltas of the silo"
      }
     ]
    },
    {
     "experiment": "silo_screening_2d",
     "timestamp": "20260930T182453Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "sweep",
     "line": null,
     "label": null,
     "git": {
      "hash": "7ad381f227a9",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 101882858,
     "size_is_lower_bound": false,
     "run_count": 24,
     "model": null,
     "kind": "sweep",
     "outcome": null,
     "description": "silo_screening_2d: a sweep of 24 points",
     "cited_in": [
      {
       "path": "docs/findings/RQ2-ignition-timing-2d.md",
       "title": "RQ2 (preliminary, 2-D): ignition timing on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-2d.md",
       "title": "RQ3 (preliminary, 2-D): vertical silo screening on the planar model"
      },
      {
       "path": "docs/findings/RQ6-aero-2d-preliminary.md",
       "title": "RQ6 (preliminary, 2-D): unthrottled max-Q, q-alpha and drag deltas of the silo"
      }
     ]
    },
    {
     "experiment": "silo_screening_2d",
     "timestamp": "20260930T175743Z",
     "group": "recorded",
     "state": "complete",
     "playable": true,
     "reason": null,
     "line": null,
     "label": null,
     "git": {
      "hash": "7ad381f227a9",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 45946129,
     "size_is_lower_bound": false,
     "run_count": 12,
     "model": "planar_2d",
     "kind": "experiment",
     "outcome": {
      "kind": "not_in_orbit",
      "message": "silo_failed did not reach the target orbit: impact"
     },
     "description": "silo_screening_2d: 12 runs",
     "cited_in": [
      {
       "path": "docs/findings/RQ2-ignition-timing-1d.md",
       "title": "RQ2 (preliminary, 1-D): hot or cold start on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ2-ignition-timing-2d.md",
       "title": "RQ2 (preliminary, 2-D): ignition timing on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-2d.md",
       "title": "RQ3 (preliminary, 2-D): vertical silo screening on the planar model"
      },
      {
       "path": "docs/findings/RQ6-aero-2d-preliminary.md",
       "title": "RQ6 (preliminary, 2-D): unthrottled max-Q, q-alpha and drag deltas of the silo"
      }
     ]
    },
    {
     "experiment": "guidance_trigger_2d",
     "timestamp": "20260930T174950Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "sweep",
     "line": null,
     "label": null,
     "git": {
      "hash": "7ad381f227a9",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 35921990,
     "size_is_lower_bound": false,
     "run_count": 8,
     "model": null,
     "kind": "sweep",
     "outcome": null,
     "description": "guidance_trigger_2d: a sweep of 8 points",
     "cited_in": [
      {
       "path": "docs/findings/RQ3-silo-screening-1d.md",
       "title": "RQ3 (preliminary, 1-D): vertical silo screening, concept A"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-2d.md",
       "title": "RQ3 (preliminary, 2-D): vertical silo screening on the planar model"
      },
      {
       "path": "docs/findings/RQ6-aero-2d-preliminary.md",
       "title": "RQ6 (preliminary, 2-D): unthrottled max-Q, q-alpha and drag deltas of the silo"
      }
     ]
    },
    {
     "experiment": "calibration_f9_2d",
     "timestamp": "20260930T173928Z",
     "group": "recorded",
     "state": "complete",
     "playable": true,
     "reason": null,
     "line": null,
     "label": "calibration",
     "git": {
      "hash": "7ad381f227a9",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 16847862,
     "size_is_lower_bound": false,
     "run_count": 8,
     "model": "planar_2d",
     "kind": "experiment",
     "outcome": {
      "kind": "complete",
      "message": "complete: pad reached the target orbit; no flag, no failed verification and no result marked as a suspected bug (status bug_suspect) recorded"
     },
     "description": "calibration_f9_2d (calibration): 8 runs",
     "cited_in": [
      {
       "path": "docs/findings/CAL-f9-leo-2d.md",
       "title": "CAL: Falcon 9-class payload to LEO, planar 2-D model (calibration record)"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-2d.md",
       "title": "RQ3 (preliminary, 2-D): vertical silo screening on the planar model"
      }
     ]
    },
    {
     "experiment": "calibration_f9_2d",
     "timestamp": "20260930T100100Z",
     "group": "recorded",
     "state": "complete",
     "playable": true,
     "reason": null,
     "line": null,
     "label": "calibration",
     "git": {
      "hash": "c2849b72e01d",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 16841430,
     "size_is_lower_bound": false,
     "run_count": 8,
     "model": "planar_2d",
     "kind": "experiment",
     "outcome": {
      "kind": "complete",
      "message": "complete: pad reached the target orbit; no flag, no failed verification and no result marked as a suspected bug (status bug_suspect) recorded"
     },
     "description": "calibration_f9_2d (calibration): 8 runs",
     "cited_in": [
      {
       "path": "docs/findings/CAL-f9-leo-2d.md",
       "title": "CAL: Falcon 9-class payload to LEO, planar 2-D model (calibration record)"
      }
     ]
    },
    {
     "experiment": "silo_screening_1d",
     "timestamp": "20260929T105707Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "sweep",
     "line": null,
     "label": null,
     "git": {
      "hash": "98c752d58f52",
      "state": "dirty"
     },
     "server_start": null,
     "size_bytes": 16216571,
     "size_is_lower_bound": false,
     "run_count": 24,
     "model": null,
     "kind": "sweep",
     "outcome": null,
     "description": "silo_screening_1d: a sweep of 24 points",
     "cited_in": []
    },
    {
     "experiment": "silo_screening_1d",
     "timestamp": "20260929T105657Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "1-D",
     "line": null,
     "label": null,
     "git": {
      "hash": "98c752d58f52",
      "state": "dirty"
     },
     "server_start": null,
     "size_bytes": 5986383,
     "size_is_lower_bound": false,
     "run_count": 10,
     "model": "vertical_1d",
     "kind": "experiment",
     "outcome": null,
     "description": "silo_screening_1d: 10 runs, 1-D",
     "cited_in": []
    },
    {
     "experiment": "silo_screening_1d",
     "timestamp": "20260929T104510Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "sweep",
     "line": null,
     "label": null,
     "git": {
      "hash": "98c752d58f52",
      "state": "dirty"
     },
     "server_start": null,
     "size_bytes": 16216571,
     "size_is_lower_bound": false,
     "run_count": 24,
     "model": null,
     "kind": "sweep",
     "outcome": null,
     "description": "silo_screening_1d: a sweep of 24 points",
     "cited_in": []
    },
    {
     "experiment": "silo_screening_1d",
     "timestamp": "20260929T104503Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "1-D",
     "line": null,
     "label": null,
     "git": {
      "hash": "98c752d58f52",
      "state": "dirty"
     },
     "server_start": null,
     "size_bytes": 5986383,
     "size_is_lower_bound": false,
     "run_count": 10,
     "model": "vertical_1d",
     "kind": "experiment",
     "outcome": null,
     "description": "silo_screening_1d: 10 runs, 1-D",
     "cited_in": []
    },
    {
     "experiment": "silo_screening_1d",
     "timestamp": "20260929T103634Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "sweep",
     "line": null,
     "label": null,
     "git": {
      "hash": "98c752d58f52",
      "state": "dirty"
     },
     "server_start": null,
     "size_bytes": 16216571,
     "size_is_lower_bound": false,
     "run_count": 24,
     "model": null,
     "kind": "sweep",
     "outcome": null,
     "description": "silo_screening_1d: a sweep of 24 points",
     "cited_in": [
      {
       "path": "docs/findings/RQ2-ignition-timing-1d.md",
       "title": "RQ2 (preliminary, 1-D): hot or cold start on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-1d.md",
       "title": "RQ3 (preliminary, 1-D): vertical silo screening, concept A"
      }
     ]
    },
    {
     "experiment": "silo_screening_1d",
     "timestamp": "20260929T103623Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "1-D",
     "line": null,
     "label": null,
     "git": {
      "hash": "98c752d58f52",
      "state": "dirty"
     },
     "server_start": null,
     "size_bytes": 5986383,
     "size_is_lower_bound": false,
     "run_count": 10,
     "model": "vertical_1d",
     "kind": "experiment",
     "outcome": null,
     "description": "silo_screening_1d: 10 runs, 1-D",
     "cited_in": [
      {
       "path": "docs/findings/RQ2-ignition-timing-1d.md",
       "title": "RQ2 (preliminary, 1-D): hot or cold start on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ2-ignition-timing-2d.md",
       "title": "RQ2 (preliminary, 2-D): ignition timing on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-1d.md",
       "title": "RQ3 (preliminary, 1-D): vertical silo screening, concept A"
      }
     ]
    }
   ]
  }
 ],
 "not_listed": 1,
 "running": {
  "experiment": "app",
  "timestamp": "20261007T125946Z"
 }
}
```


### 1.4 After completion: the run list and the new directory

#### GET /api/results

- request sent: 2026-10-07T13:00:15.075Z (CDP `wallTime` of `Network.requestWillBeSent`)
- response received: 2026-10-07T13:00:15.126Z; body complete: 2026-10-07T13:00:15.127Z (the driver's clock at `responseReceived` and `loadingFinished`)
- status: 200 OK

Request headers as `Network.requestWillBeSent` reports them (the renderer's: Content-Type and the empty Referer of the page's no-referrer policy; the network layer's additions, Host, Origin and the Sec-Fetch-* headers the server's guard reads, travel in `requestWillBeSentExtraInfo`, which this log did not subscribe to):

```
Referer: 
```

Response headers:

```
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Cache-Control: no-store
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Content-Length: 12226
Date: Wed, 07 Oct 2026 13:00:15 GMT
Content-Type: application/json; charset=utf-8
Server: launchsim
```

Response body:

```json
{
 "groups": [
  {
   "name": "app",
   "title": "App runs (exploratory)",
   "rows": [
    {
     "experiment": "app",
     "timestamp": "20261007T125946Z",
     "group": "app",
     "state": "complete",
     "playable": true,
     "reason": null,
     "line": null,
     "label": "exploratory",
     "git": {
      "hash": "fb34b2417c56",
      "state": "clean"
     },
     "server_start": {
      "hash": "fb34b2417c56",
      "state": "clean"
     },
     "size_bytes": 7473093,
     "size_is_lower_bound": false,
     "run_count": 2,
     "model": "planar_2d",
     "kind": "experiment",
     "outcome": {
      "kind": "complete",
      "message": "complete: pad, silo_cold reached the target orbit; no flag, no failed verification and no result marked as a suspected bug (status bug_suspect) recorded; the screening check against the instant-start yardsticks (an assisted run may not beat the instant-start silo's gain at its release speed) was not made: it needs silo_instant and pad_instant in one directory, and this directory does not have both"
     },
     "description": "silo_cold: vertical silo 100 m deep, 3 g net push, exit 76.7 m/s; cold start: stage 1 lit T+0.5 s after release (2 s ramp); Payload capacity 27,553.2 kg, +1,498.8 kg against pad (an upper bound: unthrottled and unconstrained)",
     "cited_in": []
    }
   ]
  },
  {
   "name": "recorded",
   "title": "Recorded experiments",
   "rows": [
    {
     "experiment": "silo_offload_2d_readme",
     "timestamp": "20261003T112956Z",
     "group": "recorded",
     "state": "complete",
     "playable": true,
     "reason": null,
     "line": null,
     "label": null,
     "git": {
      "hash": "b3150c1754ee",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 17635887,
     "size_is_lower_bound": false,
     "run_count": 5,
     "model": "planar_2d",
     "kind": "experiment",
     "outcome": {
      "kind": "complete",
      "message": "complete: pad, silo_cold reached the target orbit; no flag, no failed verification and no result marked as a suspected bug (status bug_suspect) recorded; the screening check against the instant-start yardsticks (an assisted run may not beat the instant-start silo's gain at its release speed) was not made: it needs silo_instant and pad_instant in one directory, and this directory does not have both"
     },
     "description": "silo_offload_2d_readme: 5 runs",
     "cited_in": [
      {
       "path": "docs/findings/RQ1-fuel-offload-2d.md",
       "title": "RQ1 (preliminary, 2-D): stage-1 propellant a silo push replaces at fixed payload"
      }
     ]
    },
    {
     "experiment": "silo_offload_2d",
     "timestamp": "20261003T112949Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "sweep",
     "line": null,
     "label": null,
     "git": {
      "hash": "b3150c1754ee",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 85489444,
     "size_is_lower_bound": false,
     "run_count": 20,
     "model": null,
     "kind": "sweep",
     "outcome": null,
     "description": "silo_offload_2d: a sweep of 20 points",
     "cited_in": [
      {
       "path": "docs/findings/RQ1-fuel-offload-2d.md",
       "title": "RQ1 (preliminary, 2-D): stage-1 propellant a silo push replaces at fixed payload"
      }
     ]
    },
    {
     "experiment": "silo_offload_2d",
     "timestamp": "20261003T112934Z",
     "group": "recorded",
     "state": "complete",
     "playable": true,
     "reason": null,
     "line": null,
     "label": null,
     "git": {
      "hash": "b3150c1754ee",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 74260469,
     "size_is_lower_bound": false,
     "run_count": 19,
     "model": "planar_2d",
     "kind": "experiment",
     "outcome": {
      "kind": "flagged",
      "message": "offload case silo_cold_s2: verification failed (+15.36 kg against 2.6 kg): the gross removal is a flagged lower bound and the net figure, which also subtracts a flagged pad control, is uncertain both ways"
     },
     "description": "silo_offload_2d: 19 runs",
     "cited_in": [
      {
       "path": "docs/findings/RQ1-fuel-offload-2d.md",
       "title": "RQ1 (preliminary, 2-D): stage-1 propellant a silo push replaces at fixed payload"
      }
     ]
    },
    {
     "experiment": "silo_bridge_2d_readme",
     "timestamp": "20260930T185034Z",
     "group": "recorded",
     "state": "complete",
     "playable": true,
     "reason": null,
     "line": null,
     "label": null,
     "git": {
      "hash": "7ad381f227a9",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 14318581,
     "size_is_lower_bound": false,
     "run_count": 4,
     "model": "planar_2d",
     "kind": "experiment",
     "outcome": {
      "kind": "complete",
      "message": "complete: pad, pad_instant, silo_instant, silo_cold reached the target orbit; no flag, no failed verification and no result marked as a suspected bug (status bug_suspect) recorded; the screening check against the instant-start yardsticks (an assisted run may not beat the instant-start silo's gain at its release speed) was not made: it needs silo_instant and pad_instant in one directory, and this directory does not have both"
     },
     "description": "silo_bridge_2d_readme: 4 runs",
     "cited_in": [
      {
       "path": "docs/findings/RQ2-ignition-timing-1d.md",
       "title": "RQ2 (preliminary, 1-D): hot or cold start on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ2-ignition-timing-2d.md",
       "title": "RQ2 (preliminary, 2-D): ignition timing on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-1d.md",
       "title": "RQ3 (preliminary, 1-D): vertical silo screening, concept A"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-2d.md",
       "title": "RQ3 (preliminary, 2-D): vertical silo screening on the planar model"
      },
      {
       "path": "docs/findings/RQ6-aero-2d-preliminary.md",
       "title": "RQ6 (preliminary, 2-D): unthrottled max-Q, q-alpha and drag deltas of the silo"
      }
     ]
    },
    {
     "experiment": "silo_screening_2d",
     "timestamp": "20260930T182453Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "sweep",
     "line": null,
     "label": null,
     "git": {
      "hash": "7ad381f227a9",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 101882858,
     "size_is_lower_bound": false,
     "run_count": 24,
     "model": null,
     "kind": "sweep",
     "outcome": null,
     "description": "silo_screening_2d: a sweep of 24 points",
     "cited_in": [
      {
       "path": "docs/findings/RQ2-ignition-timing-2d.md",
       "title": "RQ2 (preliminary, 2-D): ignition timing on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-2d.md",
       "title": "RQ3 (preliminary, 2-D): vertical silo screening on the planar model"
      },
      {
       "path": "docs/findings/RQ6-aero-2d-preliminary.md",
       "title": "RQ6 (preliminary, 2-D): unthrottled max-Q, q-alpha and drag deltas of the silo"
      }
     ]
    },
    {
     "experiment": "silo_screening_2d",
     "timestamp": "20260930T175743Z",
     "group": "recorded",
     "state": "complete",
     "playable": true,
     "reason": null,
     "line": null,
     "label": null,
     "git": {
      "hash": "7ad381f227a9",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 45946129,
     "size_is_lower_bound": false,
     "run_count": 12,
     "model": "planar_2d",
     "kind": "experiment",
     "outcome": {
      "kind": "not_in_orbit",
      "message": "silo_failed did not reach the target orbit: impact"
     },
     "description": "silo_screening_2d: 12 runs",
     "cited_in": [
      {
       "path": "docs/findings/RQ2-ignition-timing-1d.md",
       "title": "RQ2 (preliminary, 1-D): hot or cold start on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ2-ignition-timing-2d.md",
       "title": "RQ2 (preliminary, 2-D): ignition timing on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-2d.md",
       "title": "RQ3 (preliminary, 2-D): vertical silo screening on the planar model"
      },
      {
       "path": "docs/findings/RQ6-aero-2d-preliminary.md",
       "title": "RQ6 (preliminary, 2-D): unthrottled max-Q, q-alpha and drag deltas of the silo"
      }
     ]
    },
    {
     "experiment": "guidance_trigger_2d",
     "timestamp": "20260930T174950Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "sweep",
     "line": null,
     "label": null,
     "git": {
      "hash": "7ad381f227a9",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 35921990,
     "size_is_lower_bound": false,
     "run_count": 8,
     "model": null,
     "kind": "sweep",
     "outcome": null,
     "description": "guidance_trigger_2d: a sweep of 8 points",
     "cited_in": [
      {
       "path": "docs/findings/RQ3-silo-screening-1d.md",
       "title": "RQ3 (preliminary, 1-D): vertical silo screening, concept A"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-2d.md",
       "title": "RQ3 (preliminary, 2-D): vertical silo screening on the planar model"
      },
      {
       "path": "docs/findings/RQ6-aero-2d-preliminary.md",
       "title": "RQ6 (preliminary, 2-D): unthrottled max-Q, q-alpha and drag deltas of the silo"
      }
     ]
    },
    {
     "experiment": "calibration_f9_2d",
     "timestamp": "20260930T173928Z",
     "group": "recorded",
     "state": "complete",
     "playable": true,
     "reason": null,
     "line": null,
     "label": "calibration",
     "git": {
      "hash": "7ad381f227a9",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 16847862,
     "size_is_lower_bound": false,
     "run_count": 8,
     "model": "planar_2d",
     "kind": "experiment",
     "outcome": {
      "kind": "complete",
      "message": "complete: pad reached the target orbit; no flag, no failed verification and no result marked as a suspected bug (status bug_suspect) recorded"
     },
     "description": "calibration_f9_2d (calibration): 8 runs",
     "cited_in": [
      {
       "path": "docs/findings/CAL-f9-leo-2d.md",
       "title": "CAL: Falcon 9-class payload to LEO, planar 2-D model (calibration record)"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-2d.md",
       "title": "RQ3 (preliminary, 2-D): vertical silo screening on the planar model"
      }
     ]
    },
    {
     "experiment": "calibration_f9_2d",
     "timestamp": "20260930T100100Z",
     "group": "recorded",
     "state": "complete",
     "playable": true,
     "reason": null,
     "line": null,
     "label": "calibration",
     "git": {
      "hash": "c2849b72e01d",
      "state": "clean"
     },
     "server_start": null,
     "size_bytes": 16841430,
     "size_is_lower_bound": false,
     "run_count": 8,
     "model": "planar_2d",
     "kind": "experiment",
     "outcome": {
      "kind": "complete",
      "message": "complete: pad reached the target orbit; no flag, no failed verification and no result marked as a suspected bug (status bug_suspect) recorded"
     },
     "description": "calibration_f9_2d (calibration): 8 runs",
     "cited_in": [
      {
       "path": "docs/findings/CAL-f9-leo-2d.md",
       "title": "CAL: Falcon 9-class payload to LEO, planar 2-D model (calibration record)"
      }
     ]
    },
    {
     "experiment": "silo_screening_1d",
     "timestamp": "20260929T105707Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "sweep",
     "line": null,
     "label": null,
     "git": {
      "hash": "98c752d58f52",
      "state": "dirty"
     },
     "server_start": null,
     "size_bytes": 16216571,
     "size_is_lower_bound": false,
     "run_count": 24,
     "model": null,
     "kind": "sweep",
     "outcome": null,
     "description": "silo_screening_1d: a sweep of 24 points",
     "cited_in": []
    },
    {
     "experiment": "silo_screening_1d",
     "timestamp": "20260929T105657Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "1-D",
     "line": null,
     "label": null,
     "git": {
      "hash": "98c752d58f52",
      "state": "dirty"
     },
     "server_start": null,
     "size_bytes": 5986383,
     "size_is_lower_bound": false,
     "run_count": 10,
     "model": "vertical_1d",
     "kind": "experiment",
     "outcome": null,
     "description": "silo_screening_1d: 10 runs, 1-D",
     "cited_in": []
    },
    {
     "experiment": "silo_screening_1d",
     "timestamp": "20260929T104510Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "sweep",
     "line": null,
     "label": null,
     "git": {
      "hash": "98c752d58f52",
      "state": "dirty"
     },
     "server_start": null,
     "size_bytes": 16216571,
     "size_is_lower_bound": false,
     "run_count": 24,
     "model": null,
     "kind": "sweep",
     "outcome": null,
     "description": "silo_screening_1d: a sweep of 24 points",
     "cited_in": []
    },
    {
     "experiment": "silo_screening_1d",
     "timestamp": "20260929T104503Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "1-D",
     "line": null,
     "label": null,
     "git": {
      "hash": "98c752d58f52",
      "state": "dirty"
     },
     "server_start": null,
     "size_bytes": 5986383,
     "size_is_lower_bound": false,
     "run_count": 10,
     "model": "vertical_1d",
     "kind": "experiment",
     "outcome": null,
     "description": "silo_screening_1d: 10 runs, 1-D",
     "cited_in": []
    },
    {
     "experiment": "silo_screening_1d",
     "timestamp": "20260929T103634Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "sweep",
     "line": null,
     "label": null,
     "git": {
      "hash": "98c752d58f52",
      "state": "dirty"
     },
     "server_start": null,
     "size_bytes": 16216571,
     "size_is_lower_bound": false,
     "run_count": 24,
     "model": null,
     "kind": "sweep",
     "outcome": null,
     "description": "silo_screening_1d: a sweep of 24 points",
     "cited_in": [
      {
       "path": "docs/findings/RQ2-ignition-timing-1d.md",
       "title": "RQ2 (preliminary, 1-D): hot or cold start on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-1d.md",
       "title": "RQ3 (preliminary, 1-D): vertical silo screening, concept A"
      }
     ]
    },
    {
     "experiment": "silo_screening_1d",
     "timestamp": "20260929T103623Z",
     "group": "recorded",
     "state": "complete",
     "playable": false,
     "reason": "1-D",
     "line": null,
     "label": null,
     "git": {
      "hash": "98c752d58f52",
      "state": "dirty"
     },
     "server_start": null,
     "size_bytes": 5986383,
     "size_is_lower_bound": false,
     "run_count": 10,
     "model": "vertical_1d",
     "kind": "experiment",
     "outcome": null,
     "description": "silo_screening_1d: 10 runs, 1-D",
     "cited_in": [
      {
       "path": "docs/findings/RQ2-ignition-timing-1d.md",
       "title": "RQ2 (preliminary, 1-D): hot or cold start on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ2-ignition-timing-2d.md",
       "title": "RQ2 (preliminary, 2-D): ignition timing on a vertical silo push"
      },
      {
       "path": "docs/findings/RQ3-silo-screening-1d.md",
       "title": "RQ3 (preliminary, 1-D): vertical silo screening, concept A"
      }
     ]
    }
   ]
  }
 ],
 "not_listed": 1,
 "running": null
}
```


#### GET /api/results/app/20261007T125946Z

- request sent: 2026-10-07T13:00:15.076Z (CDP `wallTime` of `Network.requestWillBeSent`)
- response received: 2026-10-07T13:00:15.231Z; body complete: 2026-10-07T13:00:15.231Z (the driver's clock at `responseReceived` and `loadingFinished`)
- status: 200 OK

Request headers as `Network.requestWillBeSent` reports them (the renderer's: Content-Type and the empty Referer of the page's no-referrer policy; the network layer's additions, Host, Origin and the Sec-Fetch-* headers the server's guard reads, travel in `requestWillBeSentExtraInfo`, which this log did not subscribe to):

```
Referer: 
```

Response headers:

```
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Cache-Control: no-store
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Content-Length: 11089
Date: Wed, 07 Oct 2026 13:00:15 GMT
Content-Type: application/json; charset=utf-8
Server: launchsim
```

Response body:

```json
{
 "row": {
  "experiment": "app",
  "timestamp": "20261007T125946Z",
  "group": "app",
  "state": "complete",
  "playable": true,
  "reason": null,
  "line": null,
  "label": "exploratory",
  "git": {
   "hash": "fb34b2417c56",
   "state": "clean"
  },
  "server_start": {
   "hash": "fb34b2417c56",
   "state": "clean"
  },
  "size_bytes": 7473093,
  "size_is_lower_bound": false,
  "run_count": 2,
  "model": "planar_2d",
  "kind": "experiment",
  "outcome": {
   "kind": "complete",
   "message": "complete: pad, silo_cold reached the target orbit; no flag, no failed verification and no result marked as a suspected bug (status bug_suspect) recorded; the screening check against the instant-start yardsticks (an assisted run may not beat the instant-start silo's gain at its release speed) was not made: it needs silo_instant and pad_instant in one directory, and this directory does not have both"
  },
  "description": "silo_cold: vertical silo 100 m deep, 3 g net push, exit 76.7 m/s; cold start: stage 1 lit T+0.5 s after release (2 s ramp); Payload capacity 27,553.2 kg, +1,498.8 kg against pad (an upper bound: unthrottled and unconstrained)"
 },
 "baseline": "pad",
 "runs": [
  {
   "name": "pad",
   "label": "pad (baseline)",
   "role": "run",
   "offload_kind": null,
   "note": "",
   "status": "inserted",
   "has_rows": true,
   "yardstick": false,
   "assisted": false,
   "headline": {
    "kind": "payload_capacity",
    "payload_kg": 26054.4,
    "delta_kg": null,
    "against": null,
    "upper_bound": false,
    "yardstick": false,
    "flagged": false,
    "text": "Payload capacity 26,054.4 kg"
   },
   "push": null,
   "flight": {
    "liftoff_mass_kg": 572354.3962434949,
    "meco_after_release_s": 151.3284375445184,
    "max_q_pa": 37191.382881367266,
    "max_q_time_s": 65.75150361445013,
    "peak_felt_axial_g_flight": 5.1954747362886655,
    "peak_q_alpha": 74.73085706871856,
    "payload_kg": 26054.396243494975,
    "status": "inserted",
    "ignition": "stage 1 lit T\u22122.0 s before release, held down on the pad (2 s ramp)",
    "max_q_vs_pad": null,
    "pad_max_q_pa": null,
    "max_q_against": null,
    "max_q_text": "max-Q 37.2 kPa"
   },
   "flags": [],
   "verification": null
  },
  {
   "name": "silo_cold",
   "label": "silo_cold",
   "role": "run",
   "offload_kind": null,
   "note": "",
   "status": "inserted",
   "has_rows": true,
   "yardstick": false,
   "assisted": true,
   "headline": {
    "kind": "payload_capacity",
    "payload_kg": 27553.2,
    "delta_kg": 1498.8,
    "against": "pad",
    "upper_bound": true,
    "yardstick": false,
    "flagged": false,
    "text": "Payload capacity 27,553.2 kg, +1,498.8 kg against pad (an upper bound: unthrottled and unconstrained)"
   },
   "push": {
    "exit_speed_mps": 76.70717046013367,
    "net_accel_g": 3.0,
    "stroke_m": 100.0,
    "push_time_s": 2.6073181789953286,
    "felt_g_peak": 3.9964760359053533,
    "interface_force_peak_N": 22490479.616787788,
    "electrical_energy_J": 4498095923.357558,
    "electrical_energy_kWh": 1249.471089821544,
    "drive_energy_J": 2249047961.678779,
    "peak_drive_power_W": 1725181053.6951025,
    "braking_distance_m": 60.00000000000004,
    "facility_length_m": 160.00000000000006,
    "carriage_mass_kg": 0.0,
    "text": "vertical silo 100 m deep, 3 g net push, exit 76.7 m/s",
    "model": "constant_accel"
   },
   "flight": {
    "liftoff_mass_kg": 573853.2271141901,
    "meco_after_release_s": 153.82843754451855,
    "max_q_pa": 31237.64473870668,
    "max_q_time_s": 57.60962050637106,
    "peak_felt_axial_g_flight": 5.14794305073181,
    "peak_q_alpha": 129.91601484723176,
    "payload_kg": 27553.227114190096,
    "status": "inserted",
    "ignition": "cold start: stage 1 lit T+0.5 s after release (2 s ramp)",
    "max_q_vs_pad": "below",
    "pad_max_q_pa": 37191.382881367266,
    "max_q_against": "pad",
    "max_q_text": "max-Q 31.2 kPa, below the pad's (37.2 kPa)"
   },
   "flags": [],
   "verification": null
  }
 ],
 "default_pair": [
  "pad",
  "silo_cold"
 ],
 "panel": {
  "tag": {
   "kind": "exploratory",
   "text": "Exploratory app run: not a finding",
   "git": {
    "hash": "fb34b2417c56",
    "state": "clean"
   },
   "server_start": {
    "hash": "fb34b2417c56",
    "state": "clean"
   },
   "launch_tree": "clean",
   "label": "exploratory"
  },
  "shown": "silo_cold",
  "pair": [
   "pad",
   "silo_cold"
  ],
  "headline": {
   "kind": "payload_capacity",
   "payload_kg": 27553.2,
   "delta_kg": 1498.8,
   "against": "pad",
   "upper_bound": true,
   "yardstick": false,
   "flagged": false,
   "text": "Payload capacity 27,553.2 kg, +1,498.8 kg against pad (an upper bound: unthrottled and unconstrained)"
  },
  "sp1_headline": null,
  "reproduces": [
   "silo_cold: same configuration as the committed silo_cold in experiments/silo_offload_2d.yaml at commit fb34b2417c56: a reproduction, not new evidence (the code may differ from the recorded run's)"
  ],
  "sp1_comparison": {
   "case": "silo_cold_s1",
   "directory": "results/silo_offload_2d/20261003T112934Z",
   "reproduces": false,
   "differs": [
    "offload: none, a full load (SP1's silo_cold_s1: solve stage1)"
   ],
   "offload_kg": null,
   "text": "not SP1's silo_cold_s1: 1 setting differs from it, so this figure is not SP1's headline (results/silo_offload_2d/20261003T112934Z)"
  },
  "push": {
   "exit_speed_mps": 76.70717046013367,
   "net_accel_g": 3.0,
   "stroke_m": 100.0,
   "push_time_s": 2.6073181789953286,
   "felt_g_peak": 3.9964760359053533,
   "interface_force_peak_N": 22490479.616787788,
   "electrical_energy_J": 4498095923.357558,
   "electrical_energy_kWh": 1249.471089821544,
   "drive_energy_J": 2249047961.678779,
   "peak_drive_power_W": 1725181053.6951025,
   "braking_distance_m": 60.00000000000004,
   "facility_length_m": 160.00000000000006,
   "carriage_mass_kg": 0.0,
   "text": "vertical silo 100 m deep, 3 g net push, exit 76.7 m/s",
   "model": "constant_accel"
  },
  "flight": {
   "liftoff_mass_kg": 573853.2271141901,
   "meco_after_release_s": 153.82843754451855,
   "max_q_pa": 31237.64473870668,
   "max_q_time_s": 57.60962050637106,
   "peak_felt_axial_g_flight": 5.14794305073181,
   "peak_q_alpha": 129.91601484723176,
   "payload_kg": 27553.227114190096,
   "status": "inserted",
   "ignition": "cold start: stage 1 lit T+0.5 s after release (2 s ramp)",
   "max_q_vs_pad": "below",
   "pad_max_q_pa": 37191.382881367266,
   "max_q_against": "pad",
   "max_q_text": "max-Q 31.2 kPa, below the pad's (37.2 kPa)"
  },
  "flags": [],
  "verification": null,
  "outcome": {
   "kind": "complete",
   "message": "complete: pad, silo_cold reached the target orbit; no flag, no failed verification and no result marked as a suspected bug (status bug_suspect) recorded; the screening check against the instant-start yardsticks (an assisted run may not beat the instant-start silo's gain at its release speed) was not made: it needs silo_instant and pad_instant in one directory, and this directory does not have both",
   "notes": []
  },
  "caveats": [
   "EXPLORATORY app run, not a finding: launched from the local app's form, not from a committed experiment file, and not pre-registered.",
   "Planar 2-D point-mass model over a rotating spherical Earth, with drag and back-pressure. Guidance is sweep-optimized, not optimal control, and the engines never throttle.",
   "The vehicle (generic_f9_class_2d) calibrates +14.3% high: its calibration run carries 26,054 kg against the published 22,800 kg, outside the \u00b110% gate, a documented miss (docs/findings/CAL-f9-leo-2d). Read these numbers as differences between runs.",
   "No structural mass is charged for the assist load case: silo_cold (573.9 t at push start) feels up to 4.0 g during the push.",
   "The drive is a prescribed 3 g push with no force or power limit, the carriage is massless, the shaft has no air drag and the pitch kick has no aerodynamic penalty. Under this drive the release speed and the payload do not depend on the carriage mass or the shaft drag: the massless carriage biases the drive energy and peak power low, and the missing shaft drag biases the drive energy, peak power and interface force low. The free kick favours silo_cold, whose peak q-alpha is above the baseline pad's (129.9 against 74.7 Pa rad).",
   "The payload change of silo_cold (q-alpha above the baseline) is an upper bound (unthrottled and unconstrained): a max-Q or q-alpha limit, or the angle-of-attack aerodynamics the model leaves out, would reduce it."
  ],
  "offload_caveats": [],
  "built_for": [
   "pad",
   "silo_cold"
  ],
  "error": null,
  "display_only": [
   "Every shape and length: the model has a reference area and a point mass; the vehicle's shape and the widths and sizes of the shaft, rings, carriage, rails, mount and clamps come from configs/display, and the other proportions from the page's drawing constants (the plume's length, 35% of the drawn stack at full vacuum thrust scaled by the thrust fraction, and its width; the tank margins; the fairing outline and the payload stub; the trench width; the clamp spacing; the ring depth), not from the model (the shaft depth and the rail length are the run's own stroke and braking distance, the shaft drawn on down to the carriage's bottom at push start). alt_m is drawn at the rocket's base.",
   "The body attitude: the model has a thrust direction, not a body axis. While the engines are off outside the hold and the track (an unpowered coast, a fall-back) the drawn attitude is held at the last screen angle the model defines (thrust on, in the hold, on the track); the instant steps at the kick and at stage-2 ignition are the model's and are shown as recorded.",
   "The spent stage and the fairing halves: a drag-free two-body coast from the recorded separation state, listed under the event list with each body's own computed impact time, speed and downrange, drag-free (no re-entry drag, so not a landing prediction); the model has no spent stage. Each spent stage shown carries its own measured gap from the vehicle's recorded staging-coast rows (staging_coast_gap_m: the largest screen distance, the coast evaluated at the row times). Measured on 2026-10-05 over the 55 run folders with a staging coast in the six complete planar directories under results/: 0.197 and 0.089 m for pad and silo_cold of results/silo_screening_2d/20260930T175743Z over their 11 s coasts, 0.608 m at most (silo_cold_s1__pad of results/silo_offload_2d_readme/20261003T112956Z, staging at 62.8 km in denser air; 0.416 m for pad__aero_bound of the screening directory and for the aref_fairing calibration case, both with the larger reference area), below one pixel at that camera scale (hundreds of metres per pixel), so the gap drawn then is a drawing choice; the gap grows with the drag the coast ignores, so a run that stages lower sits further from it and nothing bounds it for a run not yet flown. Both fairing halves follow one path; a body still in flight when the run ends is drawn stopped there.",
   "The plume inside the shaft and the carriage beneath lit engines: the model has a vented shaft and one impingement fraction that moves only track forces and drive energy; no back-pressure, heating or exhaust on the carriage.",
   "The carriage after release and where it brakes: the model gives a braking distance only. A failed ignition falls back along the obstacle-free path: the model has no contact with the carriage, the mouth or the shaft.",
   "One propellant level per stage: a level drawn as a height takes volume fraction equal to mass fraction and one tank per stage; tanks read empty at depletion, since no residual or reserve is modelled.",
   "The pad's liftoff marker (the model logs release; a pad whose hold is not extended lifts off at release) and the ramp-end marker of a run whose ramp ends in or at the end of the hold (a pad, or a hot start held before the push: the ignition time plus the ramp length; the planner samples the hold in closed form, so no row is logged) are synthesised from the metrics; the marker that replaces the rocket when its body is under the pixel threshold is a position only."
  ]
 },
 "panel_error": null
}
```


## 2. Refusal: a ramp-start depth of 150 m on the 100 m stroke (demo step 6)

The page checks every edit with a dry run: POST /api/launches with `dry_run: true`. The server answers 200 with `refused` naming the field and the one-line message the page puts under it; nothing is launched or written. The dry runs of this session in order: the preset's own check on load, the check after the ramp-start way was set to depth (the field's default from silo_hot_ramp_on_track's ramp start), and the check after 150 was typed, which is the refusal. Launch was then disabled, and the click on it sent nothing (no POST followed; the job and the results folder were unchanged).

### 2.1 Dry run 1: the preset's own check

#### POST /api/launches

- request sent: 2026-10-07T13:10:22.854Z (CDP `wallTime` of `Network.requestWillBeSent`)
- response received: 2026-10-07T13:10:22.862Z; body complete: 2026-10-07T13:10:22.862Z (the driver's clock at `responseReceived` and `loadingFinished`)
- status: 200 OK

Request headers as `Network.requestWillBeSent` reports them (the renderer's: Content-Type and the empty Referer of the page's no-referrer policy; the network layer's additions, Host, Origin and the Sec-Fetch-* headers the server's guard reads, travel in `requestWillBeSentExtraInfo`, which this log did not subscribe to):

```
Referer: 
Content-Type: application/json
```

Request body:

```json
{
 "site": "silo",
 "stroke_m": 100,
 "push_by": "net_accel_g",
 "net_accel_g": 3,
 "carriage_mass_t": 0,
 "exhaust_impingement_fraction": 0,
 "ramp_by": "time_release",
 "t_ign_s": 0.5,
 "startup": "vehicle_default",
 "propellant": "full",
 "preset": "silo_cold",
 "dry_run": true
}
```

Response headers:

```
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Cache-Control: no-store
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Content-Length: 1666
Date: Wed, 07 Oct 2026 13:10:22 GMT
Content-Type: application/json; charset=utf-8
Server: launchsim
```

Response body:

```json
{
 "dry_run": true,
 "refused": null,
 "derived": {
  "variant": "silo_cold",
  "runs": [
   "pad",
   "silo_cold"
  ],
  "push": {
   "typed": "net_accel_g",
   "stroke_m": 100.0,
   "net_accel_g": 3.0,
   "exit_speed_mps": 76.70717046013364,
   "push_time_s": 2.6073181789953295,
   "felt_g": 3.9964760359053533,
   "braking_distance_m": 59.99999999999999,
   "facility_length_m": 160.0,
   "drag_free_apex_m": 301.0609279002213,
   "g_eff_mps2": 9.772091717511234
  },
  "ramp_start": {
   "trigger": "time",
   "requested": null,
   "estimate": false,
   "time_after_release_s": 0.5,
   "time_from_push_start_s": 3.1073181789953295,
   "depth_m": null,
   "speed_mps": 71.82112460137802,
   "height_m": 37.13207376537792
  },
  "fails": false,
  "expected_s": [
   8.0,
   50.0
  ],
  "expected_items": [
   [
    "variant silo_cold",
    8.0,
    50.0
   ]
  ],
  "expected_note": "estimated from run times measured on this machine during development: the upper ends widened from runs under load (other jobs running) and the lower ends set below the fastest runs measured (12 s for one searched run), so a launch can end anywhere in its range; the silo_cold_s1 preset took 90 s in one launch and 102 to 155 s in others with a cached pad, inside its range; a stage-1 lag startup multiplies its runs by 1 + 1 s / tau (2-3x a ramp run, measured at tau 1 s and 0.5 s); a stage-2 or both pad control or solve is not measured and is given a stage-1 solve's range, which holds SP1's pre-registered budget of 90 to 110 s for each; one searched run (the pad or a variant) has taken from 12 s to 46 s here, so this is a range, not a promise",
  "reproduces": [
   "silo_cold: same configuration as the committed silo_cold in experiments/silo_offload_2d.yaml at commit fb34b2417c56: a reproduction, not new evidence (the code may differ from the recorded run's)"
  ]
 }
}
```


### 2.2 Dry run 2: after the way was set to depth

#### POST /api/launches

- request sent: 2026-10-07T13:10:23.923Z (CDP `wallTime` of `Network.requestWillBeSent`)
- response received: 2026-10-07T13:10:23.934Z; body complete: 2026-10-07T13:10:23.934Z (the driver's clock at `responseReceived` and `loadingFinished`)
- status: 200 OK

Request headers as `Network.requestWillBeSent` reports them (the renderer's: Content-Type and the empty Referer of the page's no-referrer policy; the network layer's additions, Host, Origin and the Sec-Fetch-* headers the server's guard reads, travel in `requestWillBeSentExtraInfo`, which this log did not subscribe to):

```
Referer: 
Content-Type: application/json
```

Request body:

```json
{
 "site": "silo",
 "stroke_m": 100,
 "push_by": "net_accel_g",
 "net_accel_g": 3,
 "carriage_mass_t": 0,
 "exhaust_impingement_fraction": 0,
 "ramp_by": "depth",
 "at_depth_m": 94.57444092026729,
 "startup": "vehicle_default",
 "propellant": "full",
 "preset": "silo_cold",
 "dry_run": true
}
```

Response headers:

```
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Cache-Control: no-store
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Content-Length: 1484
Date: Wed, 07 Oct 2026 13:10:23 GMT
Content-Type: application/json; charset=utf-8
Server: launchsim
```

Response body:

```json
{
 "dry_run": true,
 "refused": null,
 "derived": {
  "variant": "silo",
  "runs": [
   "pad",
   "silo"
  ],
  "push": {
   "typed": "net_accel_g",
   "stroke_m": 100.0,
   "net_accel_g": 3.0,
   "exit_speed_mps": 76.70717046013364,
   "push_time_s": 2.6073181789953295,
   "felt_g": 3.9964760359053533,
   "braking_distance_m": 59.99999999999999,
   "facility_length_m": 160.0,
   "drag_free_apex_m": 301.0609279002213,
   "g_eff_mps2": 9.772091717511234
  },
  "ramp_start": {
   "trigger": "depth",
   "requested": 94.57444092026729,
   "estimate": false,
   "time_after_release_s": -1.9999999999999998,
   "time_from_push_start_s": 0.6073181789953297,
   "depth_m": 94.57444092026729,
   "speed_mps": 17.86727046013365,
   "height_m": null
  },
  "fails": false,
  "expected_s": [
   8.0,
   50.0
  ],
  "expected_items": [
   [
    "variant silo",
    8.0,
    50.0
   ]
  ],
  "expected_note": "estimated from run times measured on this machine during development: the upper ends widened from runs under load (other jobs running) and the lower ends set below the fastest runs measured (12 s for one searched run), so a launch can end anywhere in its range; the silo_cold_s1 preset took 90 s in one launch and 102 to 155 s in others with a cached pad, inside its range; a stage-1 lag startup multiplies its runs by 1 + 1 s / tau (2-3x a ramp run, measured at tau 1 s and 0.5 s); a stage-2 or both pad control or solve is not measured and is given a stage-1 solve's range, which holds SP1's pre-registered budget of 90 to 110 s for each; one searched run (the pad or a variant) has taken from 12 s to 46 s here, so this is a range, not a promise",
  "reproduces": []
 }
}
```


### 2.3 Dry run 3: the refusal

#### POST /api/launches

- request sent: 2026-10-07T13:10:24.470Z (CDP `wallTime` of `Network.requestWillBeSent`)
- response received: 2026-10-07T13:10:24.473Z; body complete: 2026-10-07T13:10:24.474Z (the driver's clock at `responseReceived` and `loadingFinished`)
- status: 200 OK

Request headers as `Network.requestWillBeSent` reports them (the renderer's: Content-Type and the empty Referer of the page's no-referrer policy; the network layer's additions, Host, Origin and the Sec-Fetch-* headers the server's guard reads, travel in `requestWillBeSentExtraInfo`, which this log did not subscribe to):

```
Referer: 
Content-Type: application/json
```

Request body:

```json
{
 "site": "silo",
 "stroke_m": 100,
 "push_by": "net_accel_g",
 "net_accel_g": 3,
 "carriage_mass_t": 0,
 "exhaust_impingement_fraction": 0,
 "ramp_by": "depth",
 "at_depth_m": 150,
 "startup": "vehicle_default",
 "propellant": "full",
 "preset": "silo_cold",
 "dry_run": true
}
```

Response headers:

```
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Cache-Control: no-store
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Content-Length: 152
Date: Wed, 07 Oct 2026 13:10:24 GMT
Content-Type: application/json; charset=utf-8
Server: launchsim
```

Response body:

```json
{
 "dry_run": true,
 "refused": {
  "field": "at_depth_m",
  "message": "ignition stage1: at_depth_m 150 m is deeper than the track (stroke_m 100 m)"
 },
 "derived": null
}
```

