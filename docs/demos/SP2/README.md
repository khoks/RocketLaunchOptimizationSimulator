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
| (part 2) | the commit of step A7, from which the demo launches are made; filled in by part 2 |

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

[a5-criterion2-launches.md](a5-criterion2-launches.md) is the record of step A5's
independent gate (copied here as the phase file's session log says): a driver launched every
preset and every setting of exit criterion 2 (exit speed, net acceleration, the five
ramp-start ways, a solved stage-1 offload, an imposed offload, a stage-2 solve with its pad
control, a structural penalty, the screening presets; 26 launches) into a scratch results
root, and re-read each directory: every one holds the form's values and is playable or
explained. Those launches were made on the working tree of commit ed0f4bb into a scratch
root, so none of them is in the repository and none is demo material.

## Demo launches (part 2)

PLACEHOLDER, filled in by part 2 after step A7's commit, from a clean tree, with the app
started on the repository's results folder so that the launches go to results/app/:

- the launches of demo steps 1, 4, 5, 6, 11 and 12 (silo_cold; the stage-1 solve compared
  with RQ1's silo_cold_s1 within exit criterion 3; the +8.1 t penalty; the ramp start by
  depth and by height by event; a screening preset; silo_failed), each with its directory,
  wall-clock time and the panel's headline;
- the API record of one launch and one refusal, with wall-clock times (the POST and its
  responses, the job's progress stages);
- the launch screenshots (the progress line during a solve, the completed launch and its
  scene, the +8.1 t penalty's result, the depth and height ramp starts, the video export
  control during a capture), light and dark;
- the once-with-a-real-browser check of exit criterion 17 (a page on another loopback port
  cannot start a launch);
- the commit the launches were made from, and the commit of their summaries
  (`SP2 step A7: app summaries`).

## Left for part 2 or step A8

- The scene page's data block and its Data line name only the run directory's git state
  (`git b3150c1754ee (clean)` for the gallery page and the video frames); the renderer's own
  version and git state are not in the page, unlike a replay page's meta (`"version":
  "0.1.0"`). The gallery entry says so and records them itself. Add the renderer's `version`
  and git state to the scene data block and Data line (src/launchsim/scene.py, outside this
  part's edit list) as replay's meta does (review round 1 of this step, honesty finding).
