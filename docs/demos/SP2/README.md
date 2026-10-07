# SP2 demo: the local app and the 2-D launch scene

The recorded demo of phase SP2 (docs/phases/SP2-launch-app-2d-scene.md, section 9). It shows
the local app (`uv run python -m launchsim app`): the launch form with its presets, derived
values and refusals, the run browser over the recorded directories, and the 2-D launch scene
of the pad and the silo side by side, with the model's caveats and the drawing's own next to
the picture. Part 1 of the record (this file, the QA table and the screenshots that need no
launch) was made at commit 931b19b with step A7's own uncommitted QA fixes in the working
tree; part 2 (the demo launches, their record and their screenshots) is made from the clean
tree after step A7's commit, so that the launches record a clean git state.

## What it shows, and what it is not

- Every run launched from the app is **exploratory and never a finding**: it is launched
  from the form, not from a committed experiment file, and is not pre-registered. Its
  directory under `results/app/<UTC timestamp>/` carries the label `exploratory` in
  metrics.json, a banner at the top of its summary.md (the only tracked file of an app run)
  with both git states (the code imported at server start and the working tree at launch),
  and one exploratory line in its replay, animation, scene and every video frame. Findings
  come only from committed experiment files run from a clean tree and live in
  docs/findings/.
- The scene replays the vehicle's path, thrust, mass and (while the engines run) attitude
  from the recorded time series. Everything else it draws is a display-only reconstruction
  and is named as such on the page (the approved design, docs/phases/inputs/2026-10-05-SP2-design.md,
  section 4.9): every shape and length; the held attitude when the engines are off; the
  altitude at the rocket's base; the spent stage and the fairing halves on drag-free coasts
  with their own computed impact time (no re-entry drag: not a landing prediction); the
  plume in the shaft and the carriage under lit engines (the model has a vented shaft and
  one impingement fraction that moves only track forces and drive energy); the carriage
  after release and where it brakes; a failed ignition's obstacle-free fall-back; one
  propellant level per stage, read empty at depletion; the pad's liftoff marker; the marker
  that replaces the rocket once it is under 3 px wide.
- The numbers shown beside the recorded directories are SP1's and Phase 2's
  (docs/findings/RQ1-fuel-offload-2d.md, RQ2 and RQ3), with the caveats those notes carry:
  the gate vehicle calibrates +14.3% high, no structural mass is charged for the push, the
  guidance is sweep-optimized and unthrottled, the drive is a prescribed acceleration in a
  vented shaft. The app shows them beside every number.
- Gallery, deck and manual material comes only from the two recorded directories
  (results/silo_offload_2d/20261003T112934Z and results/silo_screening_2d/20260930T175743Z),
  never from an app run (D-SP2-37).

## Commit

| commit | what |
|---|---|
| 931b19b | HEAD when part 1 was made (SP2 step A6v's tracker commit); the app, the scene and the video export as committed. The app served the working tree, which held step A7's QA fixes of src/launchsim/templates/scene.html (below) and nothing else that changes a drawing or a value |
| fb34b24 (fb34b2417c56) | HEAD when part 2 was made (step A7 part 1's tracker commit), the tree clean: the app served exactly this commit, and every demo launch directory under results/app/ records it as both its server-start and its launch-time git state (dirty false) |
| (pending) | the commit of the six app summaries, `SP2 step A7: app summaries` (D-SP2-37), made after this record was written; its hash is in the phase file's session log |

Step A7's QA fixes, each with a test in tests/test_scene_page.py. From the step's own QA: a
separated body that has stopped (its own impact, or the run's end) keeps a label (before,
its impact time made both label texts too wide for the view beside the marker, and the
marker went unlabelled from 447 to 505 s of pad beside silo_cold_s1); the close-up title's
word for the fairing halves follows the drawn motion ("opening" for the 1.5 s they turn out,
"leaving" while a half is still inside the drawing, "gone" once both have
left it while the framing is held; before, it said "opening" for a fixed 5 s); a label's
leader no longer passes through an earlier label's plate (seen in the cutoff screenshot
before the fix: the fairing label's leader crossed the spent stage's label text). From the
step's review (round 1): the halves' exit from the drawing is judged half by half, by each
half's outline, not by the box round both (that box spans the drawing diagonally long after
both halves have gone, so the title said "leaving" over an empty drawing for about 3.6 s
after each drop), and the word is taken from the drawing at the very time, not from a
sampled exit; at staging the close-up frames stage 2 whole, its base 46 px behind the
drawing's centre at the scale that draws it 121 px long, so stage 2's base and nose are in
the drawing at every time while the spent stage leaves at the bottom (before, it framed the
stage-1 engines at MECO and stage 2 lay outside the drawing for about 2.5 s of every coast,
under the gap caption); the close-up's caption plates have a see-through fill (0.72), so a
half sliding out behind the fairing caption, or the plume under it, stays in view; in the
overlay layout of a captured video frame the readout's first corner is the slot under the
close-up, where the flown path never is (it moved corner three times in the 75 s clip); the
other panel's marker gets no label plate while the ring key, which carries the same text,
lies within 128 px of its edge (the name was read twice a few dozen pixels apart). From the
step's review (round 2): after release the carriage's label keeps clear of the close-up inset
where the inset lies over the view (the overlay and column layouts; before, for about the
first second after release at 1280 x 900, the plate left of the rails ran under the inset and
read "fter release: drawn, not computed"; now it takes the right side on two lines where the
carriage is still at least 4 px tall (the scene route at 1280 x 900: silo_cold from 1.15 to
1.6 s, silo_cold_s1 at 1.2 s), and is dropped where it is not (the app page's frame at
1280 x 900, whose views are 414 and 374 px tall, never shows it after release; the close-up
names the carriage, "carriage: drawn", for about the first 0.5 s after release, while that
label lies inside its drawing)); and the other panel's label plate never lands within 128 px
of the ring key either (before, with the marker 236 px from the key, the plate landed 64 px
from it on the same line; now the plate takes a farther spot, or the key alone names the
marker). The state hook gained `closeup_stage2_base_px`, `closeup_halves_drawn`,
`others[].key_near` and `others[].label_rect` for the watchability checks of the QA table.

## Commands

The app, from the repository root, listing the repository's results folder read-only (no
launch was made in part 1; `--port 0` picks a free port, printed as http://127.0.0.1:<port>/):

    uv run python -m launchsim app --port 0 --results-root results

The standalone scene page for the gallery (the app serves the same page at
`/scene/<experiment>/<timestamp>/<runs>`):

    uv run python -m launchsim scene results/silo_offload_2d/20261003T112934Z --runs pad silo_cold_s1 --out site/examples/pad-vs-silo-offload-scene.html

The demo's exported scene page (the demo script of the phase file, section 9: pad beside
silo_cold of the screening directory), written here as
[pad-vs-silo-cold-scene.html](pad-vs-silo-cold-scene.html); the hyphenated name keeps it
clear of the `*_scene.html` ignore pattern, and `git status` lists it as untracked, not
ignored. In a browser the page plays from the file, with no server (exit criterion 15; its one
inline script is pinned by the page's policy and it loads nothing; checked with headless Edge
from a `file://` URL with `#qa=0,10` at `--window-size=1280,900`, re-run on the final export
below: the page filled its `#qa-state` element with 12,315 characters of state, the two
panels at both times, and its caveat list of 12 items). The Claude desktop app's browser pane renders a
local file as a static snapshot without JavaScript (phase file, section 9), so to look at it
there serve the folder on 127.0.0.1, for example
`uv run python -m http.server 8761 --bind 127.0.0.1 --directory docs/demos/SP2` and open
http://127.0.0.1:8761/pad-vs-silo-cold-scene.html:

    uv run python -m launchsim scene results/silo_screening_2d/20260930T175743Z --runs pad silo_cold --out docs/demos/SP2/pad-vs-silo-cold-scene.html

The QA state dumps (one per pair; the page writes `window.launchsimScene.stateAt(t)` for every
time of the `#qa=` hash into its `#qa-state` element, and headless Edge dumps the DOM):

    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new --disable-gpu --no-first-run --no-default-browser-check --disable-extensions --user-data-dir=<own folder> --window-size=1280,900 --virtual-time-budget=30000 --dump-dom "http://127.0.0.1:<port>/scene/silo_offload_2d/20261003T112934Z/pad,silo_cold_s1#qa=-2.607318,-2.0,...,536.300685"

The screenshots: headless Edge over the DevTools protocol (`--remote-debugging-port=0`, the
same flags as above without `--dump-dom`), driven by a node script that opens the app page,
clicks and types as a user would (the preset, the ramp-start field, the Advanced box, the
run browser's Open buttons, the scene's scrubber and next-event button), sets the viewport
(`Emulation.setDeviceMetricsOverride`, 1280 x 900 and 375 x 800) and the colour scheme
(`Emulation.setEmulatedMedia`, `prefers-color-scheme` light and dark), and captures each
view (`Page.captureScreenshot`). The scripts are the session's scratch files (plan.py,
dump.ps1, compare.py, probe.py, shots.mjs, export.mjs, and scan_plan.py and scan_check.py
for the watchability scan of the QA table); their method is described here so that the
record can be reproduced.

The video, through the app page's Save video control (headless Edge over the DevTools
protocol, real clicks): the directory opened with pad beside silo_cold_s1, 24 fps, 1,280 px.
At 24 fps the natural length (86.4 s) is 2,072 frames, over the app's 1,800-frame cap, so
the page scaled the clip to 75.0 s (the same scene at 1.15x the player's default rate) and
said so; 1,800 frames were posted in 31 s and the file finished at 32 s (the export was
repeated after the last fix of each review round, from an app restarted on the final
template: the round-1 clip showed the carriage label cut by the close-up inset at T+1 s);
the app wrote
`silo_offload_2d_20261003T112934Z_pad-vs-silo_cold_s1_scene.mp4` (6,095,536 bytes, h264
1280 x 720, 24 fps) into its working directory (a scratch folder, never a results tree).
The gallery set was made from it with ffmpeg 8.1:

    ffmpeg -i silo_offload_2d_20261003T112934Z_pad-vs-silo_cold_s1_scene.mp4 -c:v libx264 -preset slow -crf 22 -pix_fmt yuv420p -movflags +faststart -an site/examples/media/pad-vs-silo-offload-scene.mp4
    ffmpeg -i silo_offload_2d_20261003T112934Z_pad-vs-silo_cold_s1_scene.mp4 -vf "fps=8,scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=64:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle" site/examples/media/pad-vs-silo-offload-scene.gif
    ffmpeg -i site/examples/media/pad-vs-silo-offload-scene.mp4 -vf "select=eq(n\,1799)" -frames:v 1 -q:v 2 -update 1 site/examples/media/pad-vs-silo-offload-scene_poster.jpg

Sizes: MP4 5,046,951 bytes (crf 22; 1,800 frames, 75.0 s, 1280 x 720, 24 fps; on the
step's first export crf 27 gave 3.38 MB and crf 24 4.32 MB, and crf 22 was kept: 5.05 MB,
the largest MP4 in the gallery and, after its own GIF, its largest file; the earlier sets'
MP4s are 0.6 to 1.1 MB and their GIFs 0.7 to 2.7 MB); GIF 6,073,414 bytes (6.07 MB; the whole clip, 600 frames at 8 fps, 720 x 405, 64
colours: on the first export, at 12 fps, 960 px and 128 colours it came to 17.3 MB, and
960 px at 10 fps with 64 colours to 12.0 MB, because the camera pans and zooms continuously
so every frame changes); poster 170,879 bytes (the last frame, frame 1,799 of the 1,800,
selected by number: a seek by time from the end, `-sseof -0.1`, lands two frames early at
24 fps, and the step's first poster was frame 1,798, 0.14 s before the pad's cutoff). Two
frames of the gallery MP4 (frames 300 and 1500) and the poster were extracted and read: each carries the footer's display-only line ("The vehicle's path, thrust and mass
are replayed from the recorded time series. The spent stage, fairing halves, carriage after
release and unpowered attitude are display-only reconstructions and are not model output."),
the data line (the directory, git b3150c1754ee, clean), the three model lines (planar 2-D
model and sweep-optimized guidance; unthrottled, no sized structural mass for the 4.0 g
push load; the +14.3% calibration miss and "A model replay, not a design result.") and
silo_cold_s1's structure note.

## Screenshots (part 1: no launch needed)

Under [shots/](shots/), named `<step>-<state>-<theme>.png`, 1280 x 900 unless said
otherwise, light and dark for each state (38 files, each under 130 kB). The step numbers are
those of the demo script (phase file, section 9). The scene screenshots show the app page
scrolled to its scene card (the framed scene page).

| screenshot (light and dark) | what it shows |
|---|---|
| 01-first-open-silo-cold-preset | The app's first open: the header with the address and the "Exploratory runs, not findings" badge, the form filled with the silo_cold preset (silo 100 m deep, 3 g0 net, ramp start +0.5 s from release) and the Launch button with its expected duration |
| 01-first-open-silo-cold-derived | The same open, scrolled to the derived values the server computed from the form (exit speed 76.71 m/s, push 2.61 s, felt 4.00 g0, braking 60 m, facility 160 m, the ramp start restated as time, depth, speed and height) and the note that this form reproduces the committed silo_cold |
| 01-first-open-375 | The first open at 375 x 800: the page fits a phone width without sideways scroll |
| 07-refusal-depth-over-stroke | Step 7: the ramp start stated by depth with 150 m typed into a 100 m stroke; the one-line refusal under the field, Launch disabled, nothing written |
| 04-advanced-stage2-solve | The advanced stage-2 form: Advanced on, "Solve the largest offload" along stage 2, the pad control locked on with its reason, and the reading that a stage-2 solve is net of its pad control, a property of the vehicle model |
| 08-run-browser-recorded | Step 8: the run browser with the 15 recorded experiment directories, each with its git state, size and the findings it is cited in, the sweeps listed without a scene ("no scene: sweep") and the calibration directories listed with their Open button (playable, labelled calibration), and the heading "App runs (exploratory) (0)" over the line "None yet." |
| 08-offload-pad-vs-silo-cold-s1-push | results/silo_offload_2d/20261003T112934Z opened with pad beside silo_cold_s1 at T-1.30 s: the pad held down with its engines lit, the silo's rocket on the carriage in the shaft with its engines off, the stage-1 gauge at 89.96% with the never-loaded band |
| 08-offload-pad-vs-silo-cold-s1-release | T+0.00 s: release at the mouth (76.7 m/s) beside the pad's liftoff; the carriage drawn after release |
| 08-offload-pad-vs-silo-cold-s1-kick-start | T+0.50 s: stage-1 ignition and the kick's start, the model's pitch step (4.13 deg off vertical) in the close-up |
| 08-offload-pad-vs-silo-cold-s1-kick | T+4.00 s: the pitch kick with the plume at full thrust |
| 08-offload-pad-vs-silo-cold-s1-meco | T+138.53 s: silo_cold_s1's MECO and staging while the pad is still in its gravity turn; the stage-1 gauge empty |
| 08-offload-pad-vs-silo-cold-s1-staging | T+140.00 s: the staging coast, the spent stage falling away in the close-up (the gap drawn, not computed) and on its dashed display-only coast in the view |
| 08-offload-pad-vs-silo-cold-s1-stage2-ignition | T+149.53 s: stage-2 ignition after the 11 s coast |
| 08-offload-pad-vs-silo-cold-s1-fairing | T+184.25 s: the fairing drop, the halves opening in the close-up ("fairing halves opening"), the halves' marker and label in the view |
| 08-offload-pad-vs-silo-cold-s1-cutoff | T+523.50 s: silo_cold_s1 in orbit ("Ended T+523.50 s: in orbit") while the pad still burns; the spent stage and the fairing labelled with their drag-free impact times |
| 08-offload-pad-vs-pad-control-start | pad beside pad__offload_stage1 (the stage-1 pad control, labelled "pad control" with its no_offload verdict), both held down with full tanks |
| 08-offload-pad-vs-pad-control-meco | The same pair at T+151.33 s, both at MECO and staging |
| 09-screening-silo-failed-apex | results/silo_screening_2d/20260930T175743Z with silo_failed at its apex (T+7.84 s, 300.6 m) beside the pad, the carriage and rails as outlines with the no-contact caution plate |
| 09-screening-silo-failed-impact | silo_failed at its impact (T+15.69 s, 76.6 m/s): the panel frozen under "Ended T+15.69 s: impact" |

Every screenshot was looked at in both themes: the layouts hold, the text is legible, and
the values match the recorded runs' events and metrics.

## The QA table

[qa-table.md](qa-table.md): exit criteria 5 and 6 checked through the app's scene route for
pad, silo_cold, silo_hot_ramp_on_track, silo_failed and silo_cold_s1, each in a panel beside
another run, at every recorded event of both runs, the mid-push row of each pushed run and
times between. 1,994 rows (one per run, time and field: altitude, downrange, thrust on,
stage, plume fraction, rebuilt mass, drawn attitude and close-up attitude where the model
defines one, the painted base against the screen transform, the tank start fills on the
first row, the stage-1 tank and the stage-2 load at the stage-1 propellant event), all
passing; the companion pad panels (135 states, 1,218 checks) pass too. Worst residuals:
altitude 0.046 of its tolerance, downrange 0.066, drawn attitude 0.0005 deg, plume 0.0003,
mass 0.049 kg, painted base 0.065 px, tank start fill 2e-7. No deviations. The table's last section (added at review round 1 of the
step and re-run at round 2, after the last template fix) is the watchability scan: 3,396
panel states of the same runs every 2 s and every 0.25 s through the push, the kick, the
separations and the halves' leaving, dumped at the screenshots' viewport (1280 x 900 over the
DevTools protocol, the views 605 px wide; round 1's `--dump-dom` viewport had laid the views
out smaller, 584.5 x 421 px, and missed the carriage label's overlap with the close-up),
checked for the close-up vehicle's length (criterion 16, at least 120 px), its base and nose
inside the drawing, the halves' title word against the drawing, a stopped body's label, the
other panel's marker named once, plates inside the view and apart, and the caption plate
inside the drawing: no failing check.

## Exit criterion 2: every launch kind, recorded at step A5's gate

[criterion2-launches.md](criterion2-launches.md) is the record of step A5's
independent gate (copied here as the phase file's session log says; part 1 had it under the
name a5-criterion2-launches.md, renamed in part 2 with a fuller header): a driver launched every
preset and every setting of exit criterion 2 (exit speed, net acceleration, the five
ramp-start ways, a solved stage-1 offload, an imposed offload, a stage-2 solve with its pad
control, a structural penalty, the screening presets; 26 launches) into a scratch results
root, and re-read each directory: every one holds the form's values and is playable or
explained. Those launches were made by the gate's driver on the working tree at HEAD 7f36e8d
(step A4b's tracker commit) with step A5's changes uncommitted, the tree step A5 then
committed as ed0f4bb; every directory records git 7f36e8dffdb0, dirty (not a clean tree).
They went into a scratch root outside the repository, so none of their directories is in
the repository and none is demo material.

## Demo launches (part 2)

Made on 2026-10-07 from the clean tree at fb34b24 (fb34b2417c56), after step A7 part 1's
tracker commit, with the app started on the repository's own results folder (no
`--results-root`), so that these six launches, and only these, went to `results/app/`
(D-SP2-03, 04, 37: their summary.md files are tracked and public; every other launch of the
phase went to a scratch root). Every one of them is an **exploratory app run, not a
finding**: each number below is the app's, read from the directory's metrics.json or from
the page, and carries the caveats the results panel shows beside it (the +14.3% calibration
miss, no structural mass for the push, sweep-optimized and unthrottled guidance, the
prescribed drive in a vented shaft). The demo script (the phase file's section 9) was run
as the operator's list of nine steps, in the order of the table, through the app page in a
real browser (headless Edge over the DevTools protocol, real mouse clicks on Launch, the
confirmation, Open, Refresh, Save video, the scene's Play and next-event buttons, real key
presses on the selects and typed values in the fields; the page was opened on each preset
by its own `#preset=` link; see "Commands (part 2)" below). The step numbers in the tables
below are the operator's list; they map onto the phase file's section 9 as 1 = step 1;
2 = steps 2, 3 and 10; 3 = step 4; 4 = step 5; 5a and 5b = step 6; 6 = step 7; 7 = step 12;
8 = steps 8 and 9; 9 = step 13 (step 11's presets are in the criterion-2 record; step 14 was
made at the A4b and A5 gates).

### The server

Start lines (stdout, 12:57:01 UTC; the start command is under "Commands (part 2)"):

    launchsim app: http://127.0.0.1:58302/   (this machine only)
      results root: D:\DEV\ClaudeProjects\SpaceRocketOptimization\results
      code: git fb34b2417c56 (clean) as of server start; a launch is refused after a code change: restart the app
      launches are exploratory, not findings
      Ctrl+C stops the server; a running launch is stopped and marked FAILED
      video: ffmpeg C:\Users\rahul\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe; MP4 files go to <the session's scratch folder>\a7b\work

(`<the session's scratch folder>`, here and under "The video export", stands for the
server's working directory under the session's scratch files, a local path on this machine;
the video-control screenshots print it in full: see "Screenshots (part 2)".)

GET /api/form confirmed the same: `results_root {path: results, tracked: true}`, server
start `fb34b2417c56, clean, code_check true`, video available at 20 fps and 1280 px by
default. Stopped with Ctrl+Break (CTRL_BREAK_EVENT to the server's own process group) at
13:15:49 UTC, after the last export, with no launch running; it printed, 0.3 s later,

    launchsim app: stopping; a launch that is writing gets up to 10 s to finish (further Ctrl+C is ignored)
    launchsim app: stopped

and exited 0 in 0.42 s, nothing on stderr, no FAILED.txt anywhere.

### The launches

Wall time is from the click on Launch to the job's done state as the page's own poll
(GET /api/job every 500 ms) first reported it. The stage times are the job card's own
("Preflight DONE 1 s", and so on). Every directory records `git fb34b2417c56`, `dirty: false`,
`launch_dirty: false`, server start `fb34b2417c56 (clean)`, `label: exploratory`, and its
summary.md opens with the exploratory banner; none has a FAILED.txt.

| step | preset or settings | directory (results/) | click (UTC) | wall | stages (job card) | outcome (job card) | key number, with its source |
|---|---|---|---|---|---|---|---|
| 1 | preset `silo_cold` (silo 100 m, 3 g0 net, ramp start +0.5 s from release, the vehicle's own startup) | app/20261007T125946Z | 12:59:46.1 | 28.9 s (expected 16 s to 1 min 40 s) | preflight 1 s, pad baseline 12 s, variant 14 s, comparison 2 s, writing 0 s | Complete: "pad, silo_cold reached the target orbit; no flag ..." | payload capacity 27,553.227 kg, +1,498.831 kg against the pad's 26,054.396 kg (metrics.json runs.silo_cold.payload_kg, runs.pad.payload_kg: the same values as the recorded silo_cold and pad of silo_offload_2d/20261003T112934Z); max-Q 31.2 kPa, below the pad's 37.2 kPa (the panel) |
| 3 | preset `silo_cold_s1` (the same silo, "solve the largest offload" along stage 1, the pad control and the paired pad) | app/20261007T130614Z | 13:06:13.8 | 70.4 s (expected 49 s to 5 min 20 s with the pad cached) | preflight 1 s, pad baseline cached, variant 14 s, comparison and offload 55 s, writing 1 s | Complete; "Pad cached: the baseline was not flown again." | offload 41,262.908 kg at P_ref 26,054.396 kg (offload.cases[silo_cold_s1].offload_kg = 41262.90803733282, offload.reference_payload_kg = 26054.396243494975): 10.04% of the stage-1 load, 7.96% of all; pad control no_offload (consistency pass); paired pad 24,652.4 kg, 1,402.0 kg short of P_ref; max-Q 38.4 kPa, above the pad's 37.2 kPa; MECO T+138.5 s against the pad's T+151.3 s |
| 4 | preset `silo_cold_s1_dry+8.1t` (the solve with an assumed +8.1 t of stage-1 dry mass) | app/20261007T130817Z | 13:08:16.8 | 54.5 s (expected 41 s to 4 min 30 s) | preflight, pad cached, variant 15 s, comparison 38 s, writing 1 s | Complete; pad cached | what is left of the offload: 1,980.477 kg (1.98 t, 0.48% of the stage-1 load, 0.38% of all) with stage1_dry_mass_added_kg 8100 and assumed_penalty true (offload.cases[silo_cold_s1_dry+8.1t]); RQ1's penalty row says 1.98 t; max-Q 30.4 kPa, below the pad's |
| 5a | `silo_cold` edited: ramp start stated by depth, 50 m below the mouth (the select set by two ArrowDown presses, 50 typed; the page said "Edited from silo_cold ...") | app/20261007T130924Z | 13:09:24.0 | 16.5 s (expected 8 s to 50 s) | preflight, pad cached, variant 14 s, comparison 1 s, writing | Complete; the silo run carries the neutral name `silo` (its settings equal no committed variant) | requested depth 50 m; achieved: stage 1 lit on the track at T-0.764 s, 50.00 m below the mouth at 54.24 m/s (metrics.json runs.silo: ramp_start_requested_depth_m 50, ramp_start_depth_m 50, ramp_start_t_rel_release_s -0.7636658, ramp_start_speed_mps 54.2402; events.csv ignition at alt_m -50); payload capacity 27,780.899 kg, +1,726.5 kg against the pad |
| 5b | `silo_cold` edited: ramp start stated by height by event, 40 m above the mouth (four ArrowDown presses, 40 typed) | app/20261007T130950Z | 13:09:50.3 | 18.1 s (expected 8 s to 50 s) | preflight, pad cached, variant 16 s, comparison 1 s, writing | Complete; run `silo` | requested height 40 m; achieved: the coast after release reached 40 m at T+0.540 s and stage 1 lit there at 71.42 m/s (ramp_start_requested_height_m 40, ramp_start_height_m 40, ramp_start_t_rel_release_s +0.5400939, ramp_start_trigger height_event; events.csv ignition_height and ignition at alt_m 40); payload capacity 27,544.980 kg, +1,490.6 kg against the pad |
| 6 | refusal: `silo_cold` with the ramp start stated by depth and 150 typed into the 100 m stroke | none | 13:10:24.1 (typed) | - | - | the dry run (POST /api/launches, dry_run true, at 13:10:24.470 UTC) answered 200 with `refused: {field: at_depth_m, message: "ignition stage1: at_depth_m 150 m is deeper than the track (stroke_m 100 m)"}`; the page put that line under the field, marked it invalid, and disabled Launch ("The server refused this form (see the marked field)."); the click on Launch at 13:10:24.836 sent no request | results/app/ listed 5 directories before and 5 after; GET /api/job before and after: job 5, done (launch 5b), unchanged |
| 7 | preset `silo_failed` (stage 1 never lights) | app/20261007T131031Z | 13:10:30.8 | 0.8 s (expected 1 s to 5 s with the pad cached: the variant ends in an impact 18.3 s after push start) | preflight, pad cached, variant, comparison, writing (all within 0.8 s) | "Complete, not in orbit: silo_failed did not reach the target orbit: impact" | apex 300.65 m at T+7.84 s after release; impact at T+15.69 s at 76.60 m/s (metrics.json runs.silo_failed: apex_alt_m, apex_t_s, impact_t_s, impact_speed_mps; status impact); no payload capacity, payload change, screening estimate or loss budget (the panel) |

Operator steps 2, 8 and 9 need no launch: 2 is launch 1's scene, 8 the run browser over
the recorded directories, 9 the video export of launch 3's directory.
The pad was flown once, in launch 1 (12 s); every later launch reported `pad_cached: true`
from its first poll and its job card said so (exit criterion 9).

The scene opened by itself after every launch (the frame's src set to the new directory's
scene within 0.7 s of the done state: launch 1's `Scene: app/20261007T125946Z, pad beside
silo_cold.`), paused at its first row (T-2.61 s, the push start) with the Play button: the
app's frame carries no `autoplay` flag, so the embedded scene starts on a click, which is
what the "first 30 s at 1x" below did.

### Exit criterion 3: the solve against RQ1's headline

Launch 3's metrics.json, `offload.cases[silo_cold_s1]`: `offload_kg 41262.90803733282`,
`reference_payload_kg 26054.396243494975`, `payload_kg 26054.396243494975`, `status ok`,
`run_status inserted`, `m_res_kg 3.42e-05`, 42 evaluations, no flag; `runs.pad.payload_kg
26054.396243494975`, `runs.silo_cold.payload_kg 27553.227114190096`.

| quantity | this launch (app/20261007T130614Z) | RQ1 (docs/findings/RQ1-fuel-offload-2d.md, from results/silo_offload_2d/20261003T112934Z) | difference | within 0.002 kg |
|---|---|---|---|---|
| stage-1 offload x* | 41,262.908 037 kg | 41,262.908 kg (the note's rounding; the directory's metrics.json holds 41262.90803733282) | +0.000 037 kg against the note's figure; 0 against the directory's | yes |
| P_ref | 26,054.396 243 kg | 26,054.396 kg (26054.396243494975 in the directory) | +0.000 243 kg against the note's figure; 0 against the directory's | yes |

The two directories agree to every printed digit: the same configuration (the preset is the
committed silo_cold_s1 fragment, as the panel's "Reproduction" lines say) on code that
differs from the recorded run's only outside the planar model (the recorded run is at
b3150c1; the output-capture and digest pins of every step since kept the numbers), so this is
a reproduction of SP1's figure, not new evidence, and the panel says so. The A4 gate had
measured the same equality through `run_launch` without HTTP (session log).

### Launch 1's scene: the first 30 s at 1x, then to orbit (step 2)

With the scene opened by itself at T-2.61 s: Speed set to 1x (ArrowDown presses on the
Speed select), Play clicked, the clock sampled once a second for 31.5 wall seconds: T-2.61 s
to T+28.72 s, the clock's subtitle "after release, playing at 1.00x", a measured rate of
1.000x (32 samples); then Play clicked again to pause, and the scrubber moved to each time
below for its screenshots (the state hook of the frame, `launchsimScene.stateAt`, read at
each). Both runs on one clock: the pad (`pad`) and the silo (`silo_cold`) of
app/20261007T125946Z.

| time | what the page showed (both panels; from the state hook and the screenshot) |
|---|---|
| T-2.0 s | pad: Held down, engines 0% (its stage-1 ignition is at T-2.00 s, the row just starting), altitude 0; silo_cold: Assist push, engines off, 94.6 m deep on the carriage at 17.9 m/s, felt 4.00 g, drive 22.49 MN; both stage-1 gauges at 100% |
| T+0 s | pad: release and liftoff, full thrust; silo_cold: release at the mouth at 76.7 m/s, "Coasting before ignition", the carriage drawn after release |
| T+0.5 s | silo_cold: stage-1 ignition and the kick's start where the form put it, 37.1 m above the mouth at 71.8 m/s (the model's pitch step, "pitch kick: 2.36 deg off vertical" in the close-up; no plume yet: the 2 s ramp has just begun (engines 0.0%); it is at full length by T+2.5 s); the pad 0.4 m up |
| T+2.5 s | silo_cold: full thrust (the ramp's end) at 168.7 m, 64.5 m/s, the plume at full length; the pad at 11.4 m |
| T+8 s | silo_cold: the pitch kick, 579.1 m up, 85.1 m/s; the pad still in its vertical rise at 120.1 m, 30.8 m/s; the scale bar 200 m |
| T+60 s | both in their gravity turn (pad 8,977.6 m, 387.2 m/s, after its kick's end; silo_cold 11.89 km, 439.5 m/s, past its max-Q of 31.24 kPa, marked on its path); the camera zoomed out, the scale bar 2,000 m, both vehicles position markers |
| T+151 s | the pad 0.3 s before its MECO (69.1 km; its max-Q 37.19 kPa marked), the close-up "zooming in for staging"; silo_cold at 72.4 km still burning |
| T+158 s | both in their staging coast: the pad since T+151.33 s, silo_cold since T+153.83 s; the spent stage falling away in each close-up ("Gap drawn, not computed: the stages stay within 0.20 m (pad) / 0.09 m (silo_cold) during the 11 s coast"), on its dashed display-only coast in the view, labelled "spent stage 1: drawn, display only"; the scale bar 50 km |
| T+190 s | both on stage 2 under linear-tangent steering (pad 105.0 km, silo_cold 107.9 km); neither fairing has dropped yet in this pair (silo_cold's drop is at T+193.82 s, the pad's at T+196.81 s), so the fairing state of the script's step 3 is the next row |
| T+193.82 s | silo_cold's fairing drop (the next-event button): "fairing halves opening" in its close-up, the halves' marker and label in the view; the pad's close-up "zooming in for the fairing" 3 s before its own drop |
| T+536 s | the pad 0.3 s before its cutoff (T+536.30 s), silo_cold 2.8 s before its own (T+538.80 s): both at 200.0 km, the HUDs reading 7,352.9 m/s (pad, 0.3 s before its cutoff) and 7,276.8 m/s (silo_cold, 2.8 s before its own), both stage-2 gauges near empty (0.08% and 0.75%), the spent stages and fairings labelled with their display-only drag-free impact times |
| T+538.80 s | the scene's end: "Ended T+536.30 s: in orbit; view frozen at its end" on the pad, "Ended T+538.80 s: in orbit" on silo_cold, both HUDs 200.00 km, 7,362.7 m/s, q 0.00 kPa; the scale bar 500 km |

### Step 3's page while the solve ran, and after it

During the comparison-and-offload stage (at 14.9 s after the click: "Comparison and offload
NOW 1 s (expected 41 s to 4 min 30 s)", the pad chip "Pad baseline, cached DONE", Launch
disabled with "A launch is running: one at a time, and it cannot be cancelled. The form, the
run list and the scene stay usable."), the run browser's "Refresh the list" button was
clicked: the list reloaded in 0.1 s with "App runs (exploratory) (2)": "Running now: launch
in progress app/20261007T130614Z; running; size not known yet; git unknown (unknown); just
now; running: no scene yet" above launch 1's row, and the 15 recorded directories under it.
At completion the new scene opened by itself (the player had not been touched: a refresh of
the list is not a scene choice) with pad beside silo_cold_s1: silo_cold_s1's stage-1 gauge
starts at 89.96% with the hatched never-loaded band and the line "S1 89.96% at start,
41.26 t not loaded"; at its MECO (T+138.53 s, the next-event button) its gauge is empty while
the pad, at 57.0 km, is still in its gravity turn with 8.4% of stage 1 left (the pad's MECO
is at T+151.33 s). The results panel: "Propellant removed at the pad's payload (P_ref =
26,054.4 kg): 41.26 t, 10.04% of the stage-1 load, 7.96% of all", the folded "SP1's
headline" block ("This launch reproduces only its silo_cold_s1 figure (x* 41.26 t): a
reproduction, not new evidence. The penalty rows, the +/-10% range, the screening ratio and
the README-loads bridge come from SP1's runs, not from this launch."), the three offload runs
(the pad control, the case, the paired pad), the push block, the flight block with "Max-Q
38.4 kPa, above the pad's (37.2 kPa)" and "MECO after release T+138.5 s", and the caveat
block "Read before quoting: the caveats of the runs shown" beside them (the exploratory
line, the planar model, the +14.3% calibration miss, "No structural mass is charged for the
assist load case: silo_cold_s1 (531.1 t at push start, 41.26 t less propellant) feels up to
4.0 g during the push", the prescribed drive, the offload-block reading, the 7 recorded
caveats and the 7 display-only items folded).

### The video export (step 9)

Launch 3's directory opened from the run browser by its Open button (1.8 s), the pickers at
their default pair, pad beside silo_cold_s1; "Save video (MP4)" with the control's defaults,
20 fps and 1280 x 720 px; the page's length line: "Natural length 86.4 s at 20 fps: 1727
frames of 1280 x 720 px, from the first row to the end." (within the 1,800-frame cap, so
the clip is not scaled and runs at the player's default rate). Save video clicked at
13:14:40.3 UTC:

- POST /api/videos answered 201 with the session (fps 20, 1,727 frames, 1280 x 720, file
  name `app_20261007T130614Z_pad-vs-silo_cold_s1_scene.mp4`) and the four footer lines the
  frames carry: the exploratory line; "Planar 2-D model (rotating spherical Earth, ICAO
  atmosphere, drag); sweep-optimized guidance, not optimal control."; "Unthrottled (no max-Q
  or g limit); no sized structural mass for the 4.0 g push load."; "Gate vehicle calibrates
  +14.3% high on payload (docs/findings/CAL-f9-leo-2d). A model replay, not a design
  result.";
- the frame counter: "Saving frame 12 of 1727; elapsed 1 s, 106 ms per frame." at 1.4 s,
  "Saving frame 709 of 1727; elapsed 13 s, 18 ms per frame." at 12.8 s (the screenshot,
  Cancel showing), "Saving frame 1726 of 1727; elapsed 30 s, 17 ms per frame." at 30.0 s;
  1,727 frame POSTs (indices 0 to 1726 in order, every one answered 200) between
  13:14:41.515 and 13:15:10.293 UTC, 279,175,163 bytes of PNG frames posted;
- "All 1727 frames posted in 30 s; the encoder is finishing the file" at 30.2 s; done at
  30.8 s: "Video saved: app_20261007T130614Z_pad-vs-silo_cold_s1_scene.mp4." with the path
  shown, `<the session's scratch folder>\a7b\work\app_20261007T130614Z_pad-vs-silo_cold_s1_scene.mp4`,
  and a "Copy the path" button; the server's record afterwards: state done, received 1727,
  elapsed_s 29.906;
- ffprobe: h264, yuv420p, 1280 x 720, 20/1 fps, 1,727 frames, 86.35 s, 6,014,906 bytes,
  557 kb/s;
- the file stayed in the server's working directory (a scratch folder) and is not in the
  repository (nor would git take it: `*_scene.mp4` is ignored). Two of its frames were
  extracted with ffmpeg by frame number (the clip's frame times come from the create
  request's `times`): frame 52 (T-1.307 s, the push: silo_cold_s1 75.1 m deep on the
  carriage at 38.3 m/s, felt 4.00 g, its stage-1 gauge 89.96% with the hatched band and
  "41.26 t not loaded"; the pad held down with its engines at 34.7% of full vacuum thrust)
  and frame 1198 (T+184.294 s, the first frame after silo_cold_s1's fairing drop at
  T+184.25 s: "fairing halves opening" in its close-up, "fairing halves: drawn, display
  only" in the view; the pad at 100.19 km still under its fairing); both carry the footer
  with the data line "results/app/20261007T130614Z, experiment app, 20261007T130614Z, git
  fb34b2417c56 (clean)" and silo_cold_s1's structure line. They are in shots/ (re-saved
  with PNG optimisation, no pixel changed, to keep each under 400 kB).

### The API record (exit criterion 14)

[api-record.md](api-record.md): launch 1's POST /api/launches with its 202 answer, every
one of its 55 GET /api/job polls with the raw response body and the time since the POST,
the two GET /api/results the page made (when the directory was named, and at completion)
and the GET /api/results/app/20261007T125946Z at completion; and the refusal of step 6 as the three dry runs of that page (the preset's own
check, the check after the way was set to depth, and the refusal) with their 200 answers.
Wall-clock UTC on every exchange, from the DevTools protocol's network events (`wallTime`
of the request, the driver's clock at the response and the body). Nothing redacted;
non-ASCII characters in bodies are written as `\uXXXX` escapes.

### Not in this record

The once-with-a-real-browser check of exit criterion 17 (a page on another loopback port
cannot start a launch) was made at the A4b gate (two cross-origin browser posts started
nothing) and the A5 gate (a page opened from another site reads no hash and acts only after
the user's first trusted event), as the phase file's session log records; it was not
repeated for this demo. The screening presets of the script's step 11 (`silo_sled_22t`,
`silo_hot_full`) were not launched from the clean tree; they are in the criterion-2 driver
record above (launches 12 to 14 there), made into a scratch root.

### Screenshots (part 2)

Under [shots/](shots/), named `<step>-<state>-<theme>.png`, 1280 x 900, light and dark
for each state (83 files, each under 200 kB) plus the two video frames (1280 x 720, one
each). The step numbers are those of the operator's list (1 to 9 above), not the phase
file's. Every one was looked at in both themes. The video-control screenshots
(01-silo-cold-scene-opened, 03-solve-done-panel-caveats, 09-video-before-start,
09-video-running-frame-counter and 09-video-done-path) show the server's working directory
as its real local path, in the Save-video note and in the "Saved:" line, which the text
above abbreviates to `<the session's scratch folder>`; the files are as captured, nothing
masked.

| screenshot (light and dark) | what it shows |
|---|---|
| 01-silo-cold-running-variant | Launch 1 at 13 s: the job card with "Variant NOW 1 s (expected 8 s to 50 s)" after "Preflight DONE 1 s" and "Pad baseline DONE 12 s", the directory already named, Launch disabled with its reason |
| 01-silo-cold-done | The completed launch 1: "took 28 s", every stage DONE with its time, "Outcome: Complete" with its line, the exploratory tag and the headline "Payload capacity 27,553.2 kg, +1,498.8 kg against pad (an upper bound: unthrottled and unconstrained)", the "Reproduction" line naming the committed silo_cold |
| 01-silo-cold-scene-opened | The scene card right after launch 1: "Scene: app/20261007T125946Z, pad beside silo_cold." with the pickers, the Save video control and the frame at its first row |
| 02-first30s-t-2.0-push | T-2.00 s at 1x: the pad held down (engines 0.0%, its ignition row starting), the silo's rocket rising unlit on the carriage 94.6 m deep at 17.9 m/s, felt 4.00 g |
| 02-first30s-t+0-release | T+0.00 s: release at the mouth at 76.7 m/s beside the pad's liftoff; the carriage drawn after release |
| 02-first30s-t+0.5-ramp-start | T+0.50 s: the ramp starting where the form put it, stage-1 ignition at 37.1 m, the kick's start in the close-up |
| 02-first30s-t+2.5-plume | T+2.50 s: full thrust at the ramp's end, the plume grown to full length, 168.7 m up |
| 02-first30s-t+8-kick | T+8.00 s: the pitch kick at 579 m, 85 m/s; the pad at 120 m |
| 02-orbit-t+60-zoomed-out | T+60 s: the camera zoomed out on both gravity turns, the scale bar, silo_cold's max-Q marker |
| 02-orbit-t+151-pad-staging | T+151 s: the pad 0.3 s before MECO, both close-ups "zooming in for staging" |
| 02-orbit-t+158-silo-staging | T+158 s: both staging coasts, stage 1 falling away in each close-up with its "drawn, not computed" gap note and on its dashed coast in the view, labelled display only |
| 02-orbit-t+190-fairing | T+190 s: both on stage 2 before either fairing drop (see the table above) |
| 02-orbit-fairing-drop-silo-cold | T+193.82 s: silo_cold's fairing drop, the halves opening in the close-up, labelled in the view |
| 02-orbit-t+536-cutoff-hud | T+536 s: both at 200 km just before their cutoffs, the HUD readouts, the separated bodies with their display-only impact times |
| 02-orbit-end-cutoff-hud | T+538.80 s, the scene's end: both panels ended in orbit, the pad's view frozen at its end |
| 03-solve-running-comparison | Launch 3 at 15 s: "Comparison and offload NOW 1 s (expected 41 s to 4 min 30 s)", "Pad baseline, cached DONE", "Pad cached: the baseline was not flown again.", Launch disabled with its reason |
| 03-solve-running-browser-usable | The run browser refreshed while launch 3 ran: "Running now: launch in progress" listed as an app run with "running: no scene yet", launch 1 below it with Open, the recorded directories under them |
| 03-solve-done-tank-part-full | Launch 3's scene at T-1.30 s: silo_cold_s1's stage-1 gauge at 89.96% with the hatched never-loaded band ("41.26 t not loaded") beside the pad's full tanks; the offload line under the panel header |
| 03-solve-done-meco | T+138.53 s: silo_cold_s1's MECO and staging, its stage-1 gauge empty, while the pad still burns at 57 km with 8.4% of stage 1 left |
| 03-solve-done-panel | The results panel of launch 3: the exploratory tag, the propellant-saved headline, SP1's headline block folded, the Reproduction lines, the three offload runs, the push block, the flight block's start |
| 03-solve-done-panel-flight | The same panel scrolled to the flight block: "Max-Q 38.4 kPa, above the pad's (37.2 kPa)", "MECO after release T+138.5 s", liftoff mass 531.1 t, payload 26,054.4 kg |
| 03-solve-done-panel-caveats | The same panel's caveat block "Read before quoting: the caveats of the runs shown" beside the Scene card's pickers and the Save video control |
| 03-solve-done-job-pad-cached | Launch 3's job card: "took 70 s", "Pad baseline, cached DONE", "Comparison and offload DONE 55 s", "Pad cached: the baseline was not flown again.", the outcome and the headline |
| 04-penalty-8.1t-done | Launch 4's job card: pad cached, "Comparison and offload DONE 38 s", the headline "1.98 t, 0.48% of the stage-1 load, 0.38% of all with an assumed +8.1 t of stage-1 dry mass" |
| 04-penalty-8.1t-panel | Launch 4's results panel: the headline, "Against SP1's silo_cold_s1: not SP1's silo_cold_s1: 2 settings differ from it, so this figure is not SP1's headline" with the folded list of what differs, the offload runs, "Max-Q 30.4 kPa, below the pad's" |
| 04-penalty-8.1t-tank | Launch 4's scene at T-1.30 s: the stage-1 gauge at 99.52% (1.98 t not loaded) on the heavier stack |
| 05-ramp-depth-50m-ignition | Launch 5a's scene at T-0.76 s: stage-1 ignition in the shaft, 50 m below the mouth on the push (the ignition marker in the shaft; engines lit on the carriage) |
| 05-ramp-depth-50m-panel | Launch 5a's results panel: "stage 1 lit on the track, T-0.8 s before release (2 s ramp)", payload 27,780.9 kg; the form's derived line "Ramp start T-0.764 s after release; 1.844 s from push start; 50.00 m below the mouth; 54.24 m/s on the push" beside it |
| 05-ramp-height-40m-ignition | Launch 5b's scene at T+0.54 s: ignition_height, the ignition marker 40 m above the mouth on the coast, the kick's start |
| 05-ramp-height-40m-panel | Launch 5b's results panel: "cold start: stage 1 lit T+0.5 s after release (2 s ramp)" (the event at T+0.540 s), payload 27,545.0 kg |
| 06-refusal-depth-150m | Step 6: 150 typed into "Ramp start depth below the mouth" of a 100 m stroke, the field marked, the one-line refusal under it, Launch disabled ("The server refused this form (see the marked field)."), launch 5b's done job card unchanged |
| 07-silo-failed-done | Launch 7's job card: "took 0 s", pad cached, "Outcome: Complete, not in orbit: silo_failed did not reach the target orbit: impact" |
| 07-silo-failed-apex | Launch 7's scene at the apex (T+7.84 s, 300.6 m): the fall-back, the carriage and rails as outlines, the no-contact caution plate |
| 07-silo-failed-impact | T+15.69 s: "Ended T+15.69 s: impact", 76.6 m/s, the panel frozen under the exploratory banner |
| 08-browser-offload-pad-vs-silo-cold-s1-push | results/silo_offload_2d/20261003T112934Z opened by its Open button, the pickers at pad and silo_cold_s1: T-1.30 s, the offloaded tank at 89.96% beside the pad's full tanks |
| 08-browser-offload-pad-vs-silo-cold-s1-end-orbit | The same pair at its end (T+536.30 s): silo_cold_s1 ended in orbit at T+523.50 s, the pad at its cutoff, both at 200 km with the same payload |
| 08-browser-offload-pad-vs-pad-control-start | pad beside pad__offload_stage1 chosen on the right picker: "pad control (stage1): pad's own offload at P_ref = 26,054.4 kg: none found (status no_offload, consistency pass ...)", both held down with full tanks (S1 99.84% at T-1.00 s, the hold-down burn) |
| 08-browser-screening-silo-failed-apex | results/silo_screening_2d/20260930T175743Z opened by its Open button, silo_failed chosen on the right picker: the apex at T+7.84 s |
| 08-browser-screening-silo-failed-impact | The same at the impact, T+15.69 s |
| 09-video-before-start | The Save video control before the click: 20 fps and 1280 x 720 px (the defaults), the length line, the note on where the file goes |
| 09-video-running-frame-counter (light only) | "Saving frame 709 of 1727; elapsed 13 s, 18 ms per frame." with Cancel showing and the selects locked; light only, because switching the theme while frames are captured would change the clip's own frames |
| 09-video-done-path | "Saved:" with the file's path and the "Copy the path" button, the Save video button back |
| 09-video-frame-push (one file) | Frame 52 of the exported MP4 (T-1.31 s): the push, with the caveat footer |
| 09-video-frame-fairing-drop (one file) | Frame 1198 (T+184.29 s): silo_cold_s1's fairing halves opening, with the caveat footer |

### Commands (part 2)

The server, from the repository's own virtual environment, its working directory a scratch
folder of the session (so that the exported MP4 lands there and not in the repository); the
repository is found from the installed package, and the results root defaults to the
repository's results folder:

    D:\DEV\ClaudeProjects\SpaceRocketOptimization\.venv\Scripts\python.exe -m launchsim app --port 0

(`uv run python -m launchsim app --port 0` runs the same interpreter; the direct call was
used so that Ctrl+Break reaches the server itself and not uv's wrapper, TODO.md KI-037.) It
was started by a small supervisor script (subprocess.Popen with CREATE_NEW_PROCESS_GROUP,
stdout and stderr mirrored to files with a UTC stamp per line) that sent CTRL_BREAK_EVENT
when a stop file appeared and recorded the exit code.

The page, in headless Edge over the DevTools protocol (the same flags as part 1:
`--headless=new --disable-gpu --no-first-run --no-default-browser-check --hide-scrollbars
--remote-debugging-port=0 --user-data-dir=<own folder>`), driven by node scripts on the A5
gate's CDP helper (`cdp_lib.mjs`): one script per step (s1 for launch 1 and its scene, s2b
for the two exact-event shots, s3 to s7 for the launches and the refusal, s8 for the run
browser, s9 for the video), each opening the page on its preset's `#preset=` link, clicking
the form's title as the first trusted event, then Launch and the confirmation by
`Input.dispatchMouseEvent`, setting selects by `Input.dispatchKeyEvent` ArrowDown presses
and fields by `Input.insertText` after a click, polling GET /api/job and the page every
0.4 s, and capturing each state with `Emulation.setDeviceMetricsOverride` 1280 x 900,
`Emulation.setEmulatedMedia` prefers-color-scheme light then dark, `Page.captureScreenshot`.
The wire log (every request and response with `Network.requestWillBeSent`'s `wallTime` and
`Network.getResponseBody`) is the source of api-record.md. The video frames:

    ffprobe -v error -show_entries format=duration,size,bit_rate:stream=codec_name,width,height,r_frame_rate,nb_frames,pix_fmt app_20261007T130614Z_pad-vs-silo_cold_s1_scene.mp4
    ffmpeg -i app_20261007T130614Z_pad-vs-silo_cold_s1_scene.mp4 -vf "select=eq(n\,52)" -frames:v 1 -update 1 09-video-frame-push.png
    ffmpeg -i app_20261007T130614Z_pad-vs-silo_cold_s1_scene.mp4 -vf "select=eq(n\,1198)" -frames:v 1 -update 1 09-video-frame-fairing-drop.png

The scripts and the raw records (the job snapshots, the state-hook values of every
screenshot, the wire logs, the server's stamped output) are the session's scratch files;
their method is described here so that the record can be reproduced.

## Left for step A8

- The scene page's data block and its Data line name only the run directory's git state
  (`git b3150c1754ee (clean)` for the gallery page and the video frames; `git fb34b2417c56
  (clean)` for the demo launches above, where the two states happen to coincide); the
  renderer's own version and git state are not in the page, unlike a replay page's meta
  (`"version": "0.1.0"`). The gallery entry says so and records them itself. Add the
  renderer's `version` and git state to the scene data block and Data line
  (src/launchsim/scene.py, outside part 1's and part 2's edit lists) as replay's meta does
  (review round 1 of this step, honesty finding). Part 2 changed no code.
