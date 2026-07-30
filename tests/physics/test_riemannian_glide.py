"""Tests for RiemannianGlideTrajectory geodesic integration (#95).

The straight-line step x + dt*v is a geodesic only when the Christoffel symbols
vanish, which requires a CONSTANT metric -- not merely a diagonal one. The tests
below pin that distinction: a constant metric must stay straight, a diagonal but
position-dependent metric (hiho_metric) must curve.
"""

import math

import numpy as np

from cohezion.physics import RiemannianGlideTrajectory
from cohezion.physics.riemannian_metric import RiemannianMetric, hiho_metric


def _identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def test_step_changes_position():
    t = RiemannianGlideTrajectory(_identity(2), [0.0, 0.0], [1.0, 2.0])
    p = t.step(0.1)
    assert p == [0.1, 0.2]
    assert t.position == [0.1, 0.2]


def test_arc_length_positive():
    t = RiemannianGlideTrajectory(_identity(2), [0.0, 0.0], [1.0, 0.0])
    assert t.arc_length(n_steps=10, dt=0.01) > 0.0


def test_curvature_proxy_identity():
    t = RiemannianGlideTrajectory(_identity(3), [0.0, 0.0, 0.0], [1.0, 0.0, 0.0])
    assert t.curvature_proxy() == 1.0


def test_arc_length_element_euclidean():
    # 3-4-5 right triangle: |(3,4)| = 5 under the identity metric.
    t = RiemannianGlideTrajectory(_identity(2), [0.0, 0.0], [3.0, 4.0])
    assert math.isclose(t.arc_length_element(), 5.0)


# --- geodesic integration (F2/F2b) ---


def test_geodesic_curves_in_the_predicted_direction():
    """Direction-specific: catches a missing Gamma AND a wrong-sign Gamma.

    Under hiho_metric the well is centred at 0.5, so from [0.2, 0.2] moving
    along +x the trajectory is pulled toward the attractor: the transverse
    component (index 1) must GROW from its initial 0.2. A straight-line
    implementation leaves it at exactly 0.2; a sign-flipped Gamma decreases it.
    """
    x0, v0, dt, n = [0.2, 0.2], [1.0, 0.0], 0.01, 50
    t = RiemannianGlideTrajectory(_identity(2), list(x0), list(v0), metric=hiho_metric(2))
    for _ in range(n):
        t.step(dt)

    # transverse motion appeared out of nothing => Gamma is doing work
    assert t.position[1] > x0[1] + 1e-6, f"no transverse curve: {t.position}"
    # and the longitudinal component lags the straight-line prediction
    assert t.position[0] < x0[0] + n * dt * v0[0]


def test_geodesic_matches_solve_ivp_reference():
    """Cross-check the Euler path against RiemannianMetric.geodesic (RK45).

    A *wrong but nonzero* acceleration still passes a mere "did it move" test;
    it fails agreement with an independent high-accuracy integrator.
    """
    m = hiho_metric(2)
    x0, v0, dt, n = [0.2, 0.2], [1.0, 0.0], 0.001, 200  # t_end = 0.2

    t = RiemannianGlideTrajectory(_identity(2), list(x0), list(v0), metric=m)
    for _ in range(n):
        t.step(dt)

    _, traj = m.geodesic(np.array(x0), np.array(v0), t_span=(0.0, n * dt), n_steps=50)
    ref = traj[-1]

    # first-order Euler vs RK45 over a short span: a few percent of the
    # displacement is the honest tolerance.
    err = np.linalg.norm(np.array(t.position) - ref)
    scale = np.linalg.norm(ref - np.array(x0))
    assert err < 0.05 * scale, f"euler={t.position} rk45={ref} err={err}"


def test_velocity_delta_equals_dt_times_acceleration():
    """Catches the F2b no-op AND a wrong acceleration.

    'velocity changed' is not discriminating -- any bogus `a` passes it. Assert
    the delta equals dt * a with `a` computed independently from the metric.
    """
    m = hiho_metric(2)
    x0, v0, dt = [0.2, 0.3], [1.0, -0.5], 0.01
    expected_a = m.geodesic_acceleration(np.array(x0), np.array(v0))

    t = RiemannianGlideTrajectory(_identity(2), list(x0), list(v0), metric=m)
    t.step(dt)

    for i in range(2):
        assert math.isclose(t.velocity[i] - v0[i], dt * expected_a[i], rel_tol=1e-9, abs_tol=1e-12)


def test_constant_metric_stays_straight():
    """Guards the over-correction: curving whenever a metric is present.

    A constant (here diagonal, non-identity) metric has Gamma == 0 identically,
    so the geodesic IS the straight line.
    """
    m = RiemannianMetric(2, np.diag([1.0, 0.7]))
    x0, v0, dt, n = [0.2, 0.2], [1.0, 2.0], 0.01, 20
    t = RiemannianGlideTrajectory(_identity(2), list(x0), list(v0), metric=m)
    for _ in range(n):
        t.step(dt)

    for i in range(2):
        assert math.isclose(t.position[i], x0[i] + n * dt * v0[i], rel_tol=1e-12)
    assert t.velocity == v0  # zero acceleration => velocity untouched


def test_velocity_stays_pure_python_floats():
    """numpy scalars must not leak into the public list[float] state."""
    t = RiemannianGlideTrajectory(_identity(2), [0.2, 0.2], [1.0, 0.0], metric=hiho_metric(2))
    t.step(0.01)
    assert all(type(v) is float for v in t.velocity)


# --- metric evaluated at the current position (F2b) ---


def test_arc_length_element_uses_current_position():
    """The frozen `metric_tensor` field must not shadow a wired metric.

    hiho_metric weight is 1 + 2*exp(-|x-0.5|^2/sigma^2): 3.0 at the attractor
    (ds = sqrt(3)) and ~1.0 far away (ds = 1.0) for a unit velocity.
    """
    m = hiho_metric(2)
    at_well = RiemannianGlideTrajectory(_identity(2), [0.5, 0.5], [1.0, 0.0], metric=m)
    far = RiemannianGlideTrajectory(_identity(2), [5.0, 5.0], [1.0, 0.0], metric=m)

    assert math.isclose(at_well.arc_length_element(), math.sqrt(3.0), rel_tol=1e-9)
    assert math.isclose(far.arc_length_element(), 1.0, rel_tol=1e-6)


def test_arc_length_does_not_mutate_state():
    """arc_length() measures; it must not consume the trajectory."""
    x0, v0 = [0.2, 0.2], [1.0, 0.0]
    t = RiemannianGlideTrajectory(_identity(2), list(x0), list(v0), metric=hiho_metric(2))
    t.arc_length(n_steps=10, dt=0.01)
    assert t.position == x0
    assert t.velocity == v0


# --- curvature vs metric scale (F3) ---


def test_ricci_scalar_zero_for_constant_metric():
    """A constant metric is FLAT even when its scale proxy is nonzero."""
    m = RiemannianMetric(2, np.diag([1.0, 0.7]))
    t = RiemannianGlideTrajectory(_identity(2), [0.2, 0.2], [1.0, 0.0], metric=m)
    assert t.ricci_scalar() == 0.0
    assert t.curvature_proxy() == 0.85  # (1.0 + 0.7) / 2 -- a scale, not curvature


def test_ricci_scalar_zero_when_unwired():
    """list[list[float]] is position-independent => flat => R == 0 exactly."""
    t = RiemannianGlideTrajectory(_identity(3), [0.0, 0.0, 0.0], [1.0, 0.0, 0.0])
    assert t.ricci_scalar() == 0.0
