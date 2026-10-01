"""Extract a compact replay dataset from one planar results directory for the viewer page.

Reads results/silo_screening_2d/20260930T175743Z (read-only) and writes replay_data.json
next to this script: per run a downsampled time series on the common clock t after
release (0.1 s steps over the first 40 s, 1 s after), the event list and the headline
metrics. Every value is copied or linearly resampled from the run's own files.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\DEV\ClaudeProjects\SpaceRocketOptimization")
RUN_DIR = ROOT / "results" / "silo_screening_2d" / "20260930T175743Z"
OUT = Path(__file__).with_name("replay_data.json")
RUNS = ["pad", "silo_cold", "silo_hot_ramp_on_track", "silo_instant"]
LABELS = {
    "pad": "Pad (baseline)",
    "silo_cold": "Silo, cold start",
    "silo_hot_ramp_on_track": "Silo, lit on the track",
    "silo_instant": "Silo, instant ignition (yardstick)",
}
EARLY_END_S, EARLY_DT_S, LATE_DT_S = 40.0, 0.1, 1.0

metrics = json.loads((RUN_DIR / "metrics.json").read_text(encoding="utf-8"))


def grid(t0: float, t1: float) -> np.ndarray:
    """Common-clock sample times [s after release]: fine early, coarse late."""
    early = np.arange(np.ceil(t0 / EARLY_DT_S) * EARLY_DT_S, min(EARLY_END_S, t1), EARLY_DT_S)
    late = np.arange(EARLY_END_S, t1, LATE_DT_S)
    return np.unique(np.concatenate([early, late, [t1]]))


out: dict = {
    "source": "results/silo_screening_2d/20260930T175743Z",
    "git": metrics["git"]["hash"],
    "baseline": metrics["baseline"],
    "runs": {},
}
for name in RUNS:
    ts = pd.read_csv(RUN_DIR / name / "timeseries.csv")
    ev = pd.read_csv(RUN_DIR / name / "events.csv")
    ts = ts.sort_values("t_rel_release_s").drop_duplicates("t_rel_release_s", keep="last")
    t = ts["t_rel_release_s"].to_numpy()
    tg = grid(float(t[0]), float(t[-1]))

    def col(c: str, scale: float = 1.0, nd: int = 3) -> list[float | None]:
        """Resample one column; samples next to an undefined source value (q and Mach
        inside the vented shaft, where no air drag is modelled) become None (JSON null)."""
        src = ts[c].to_numpy(dtype=float)
        defined = np.isfinite(src)
        y = np.interp(tg, t[defined], src[defined]) * scale
        j = np.clip(np.searchsorted(t, tg, side="right") - 1, 0, len(t) - 1)
        k = np.clip(j + 1, 0, len(t) - 1)
        bad = ~defined[j] | (~defined[k] & (tg > t[j]))
        return [None if b else round(float(v), nd) for v, b in zip(y, bad, strict=True)]

    phase_idx = np.clip(np.searchsorted(t, tg, side="right") - 1, 0, len(t) - 1)
    phases = ts["phase"].to_numpy()[phase_idx].tolist()
    t_release = float(ts["t_s"].iloc[0] - ts["t_rel_release_s"].iloc[0])
    events = [
        {"t": round(float(r.t_s) - t_release, 3), "name": str(r.event), "alt_m": round(float(r.alt_m), 1),
         "x_km": round(float(r.downrange_m) / 1000.0, 3), "v": round(float(r.speed_rel_mps), 2)}
        for r in ev.itertuples()
    ]
    m = metrics["runs"][name]
    comp = metrics["comparison"].get(name, {})
    out["runs"][name] = {
        "label": LABELS[name],
        "t": [round(float(v), 2) for v in tg],
        "alt_m": col("alt_m", 1.0, 1),
        "x_km": col("downrange_m", 1e-3, 3),
        "v": col("speed_rel_mps", 1.0, 2),
        "gamma_deg": col("gamma_rel_rad", 180.0 / np.pi, 2),
        "pitch_deg": col("pitch_rad", 180.0 / np.pi, 2),
        "m_t": col("m_kg", 1e-3, 3),
        "g_ax": col("felt_axial_g", 1.0, 3),
        "q_kpa": col("q_pa", 1e-3, 3),
        "mach": col("mach", 1.0, 3),
        "phase": phases,
        "events": events,
        "payload_kg": round(float(m["payload_kg"]), 1),
        "payload_delta_kg": None if not comp else round(float(comp.get("payload_delta_kg")), 1),
        "max_q_kpa": round(float(m["max_q_pa"]) / 1000.0, 2),
        "peak_g_flight": round(float(m["peak_felt_axial_g_flight"]), 2),
        "losses_mps": {k: round(float(m[k]), 1) for k in
                       ("gravity_loss_mps", "drag_loss_mps", "steering_loss_mps", "back_pressure_loss_mps")},
        "exit_speed_mps": None if name == "pad" else round(float(m.get("exit_speed_mps") or 0.0), 2),
        "felt_g_track": None if name == "pad" else round(float(m.get("felt_g_track_peak") or 0.0), 3),
    }
OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
print(OUT, OUT.stat().st_size, "bytes")
for name, r in out["runs"].items():
    print(name, len(r["t"]), "samples", r["t"][0], "->", r["t"][-1], "P*", r["payload_kg"], "dP*", r["payload_delta_kg"],
          "exit", r["exit_speed_mps"], "g_track", r["felt_g_track"], "events", [e["name"] for e in r["events"]])
