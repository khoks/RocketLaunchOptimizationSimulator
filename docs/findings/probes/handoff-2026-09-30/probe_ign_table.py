"""Probe: where the stage-1 thrust ramp starts and ends for the shipped 3 g / 100 m silo
(constant_accel, mouth at z = 0, 2 s linear ramp), as a function of t_ign_s and reference.
Closed forms: on the track z = -L + a t^2/2, v = a t (t on the push clock, 0..t_push);
before the push the vehicle is clamped at z = -L; after release a drag-free unlit coast
under g_eff (28.5 deg east), z = v_e dt - g dt^2/2, v = v_e - g dt (the recorded silo_cold
run gives 37.129 m / 71.81 m/s at +0.5 s, matching this to 0.01 m)."""
import math

G0 = 9.80665
A = 3.0 * G0
L = 100.0
G_EFF = 9.7720917
T_PUSH = math.sqrt(2 * L / A)
V_E = A * T_PUSH
T_RAMP = 2.0


def where(t_abs):
    if t_abs <= 0.0:
        return -L, 0.0, "clamped at shaft bottom (hold)"
    if t_abs <= T_PUSH:
        return -L + 0.5 * A * t_abs**2, A * t_abs, "on the track (push)"
    dt = t_abs - T_PUSH
    return V_E * dt - 0.5 * G_EFF * dt**2, V_E - G_EFF * dt, "free coast above mouth"


print(f"a = {A:.5f} m/s^2, L = {L} m, t_push = {T_PUSH:.6f} s, v_exit = {V_E:.5f} m/s")
print("| t_ign_s | reference | t_ign rel. push start | t_ign rel. release | ramp start z [m] / v [m/s] | where | ramp end (t+2 s) z / v | where |")
rows = [(-4.0, "push_start"), (-2.0, "push_start"), (0.0, "push_start"), (1.0, "push_start"),
        (2.0, "push_start"), (-4.607318, "release"), (-2.607318, "release"), (-2.0, "release"),
        (-1.0, "release"), (-0.5, "release"), (0.0, "release"), (0.5, "release"), (1.0, "release"),
        (2.0, "release"), (3.0, "release")]
for t_ign, ref in rows:
    t_abs = t_ign if ref == "push_start" else T_PUSH + t_ign
    z0, v0, w0 = where(t_abs)
    z1, v1, w1 = where(t_abs + T_RAMP)
    print(f"| {t_ign:+.3f} | {ref} | {t_abs:+.3f} | {t_abs - T_PUSH:+.3f} | {z0:8.2f} / {v0:6.2f} | {w0} | {z1:8.2f} / {v1:6.2f} | {w1} |")
# inverse: ignition at a given depth d below the mouth (on the track)
print("inverse (ramp start at depth d below the mouth, on the track):")
for d in (100, 90, 75, 50, 25, 10, 0):
    t_abs = math.sqrt(2 * (L - d) / A)
    print(f"  depth {d:5.1f} m -> t_ign_s = {t_abs:.4f} (push_start) = {t_abs - T_PUSH:+.4f} (release), v = {A*t_abs:.2f} m/s")
