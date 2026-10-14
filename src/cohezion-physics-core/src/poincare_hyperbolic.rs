//! Native SIMD-accelerated 2048D Poincaré Hyperbolic Manifold Operations.
//! Provides sub-microsecond geodesic distance, conformal factors, Möbius addition,
//! and Rayon multi-threaded batch pairwise distance matrices.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use rayon::prelude::*;

const EPSILON: f64 = 1e-7;
const EPSILON_DENOM: f64 = 1e-14;

/// Computes the squared Euclidean norm using 8-way unrolled SIMD accumulation.
#[inline(always)]
pub fn squared_norm_simd(v: &[f64]) -> f64 {
    let chunks = v.chunks_exact(8);
    let remainder = chunks.remainder();
    let mut acc = [0.0; 8];
    for chunk in chunks {
        for i in 0..8 {
            acc[i] += chunk[i] * chunk[i];
        }
    }
    let sum_acc = acc[0] + acc[1] + acc[2] + acc[3] + acc[4] + acc[5] + acc[6] + acc[7];
    let sum_rem: f64 = remainder.iter().map(|&x| x * x).sum();
    sum_acc + sum_rem
}

/// Computes the Euclidean norm: ||v|| = sqrt(sum(v_i^2)).
#[inline(always)]
pub fn euclidean_norm(v: &[f64]) -> f64 {
    squared_norm_simd(v).sqrt()
}

/// Computes the squared Euclidean distance: ||u - v||^2 using 8-way unrolled SIMD accumulation.
#[inline(always)]
pub fn squared_distance_simd(u: &[f64], v: &[f64]) -> f64 {
    let chunks_u = u.chunks_exact(8);
    let chunks_v = v.chunks_exact(8);
    let rem_u = chunks_u.remainder();
    let rem_v = chunks_v.remainder();
    let mut acc = [0.0; 8];
    for (cu, cv) in chunks_u.zip(chunks_v) {
        for i in 0..8 {
            let diff = cu[i] - cv[i];
            acc[i] += diff * diff;
        }
    }
    let sum_acc = acc[0] + acc[1] + acc[2] + acc[3] + acc[4] + acc[5] + acc[6] + acc[7];
    let sum_rem: f64 = rem_u
        .iter()
        .zip(rem_v.iter())
        .map(|(&x, &y)| {
            let d = x - y;
            d * d
        })
        .sum();
    sum_acc + sum_rem
}

/// Computes the dot product: <u, v> = sum(u_i * v_i) using 8-way unrolled SIMD accumulation.
#[inline(always)]
pub fn dot_product_simd(u: &[f64], v: &[f64]) -> f64 {
    let chunks_u = u.chunks_exact(8);
    let chunks_v = v.chunks_exact(8);
    let rem_u = chunks_u.remainder();
    let rem_v = chunks_v.remainder();
    let mut acc = [0.0; 8];
    for (cu, cv) in chunks_u.zip(chunks_v) {
        for i in 0..8 {
            acc[i] += cu[i] * cv[i];
        }
    }
    let sum_acc = acc[0] + acc[1] + acc[2] + acc[3] + acc[4] + acc[5] + acc[6] + acc[7];
    let sum_rem: f64 = rem_u.iter().zip(rem_v.iter()).map(|(&x, &y)| x * y).sum();
    sum_acc + sum_rem
}

/// Computes conformal factor: lambda(x) = 2 / (1 - ||x||^2), clamped to ||x||^2 <= 1.0 - 1e-7.
#[inline(always)]
pub fn conformal_factor(v: &[f64]) -> f64 {
    let norm_sq = squared_norm_simd(v);
    let clamped_sq = norm_sq.min(1.0 - EPSILON);
    let denom = (1.0 - clamped_sq).max(EPSILON);
    2.0 / denom
}

/// Computes Poincaré hyperbolic distance between two vectors:
/// d_H(u, v) = arcosh(1 + 2 * ||u - v||^2 / ((1 - ||u||^2) * (1 - ||v||^2)))
#[inline(always)]
pub fn hyperbolic_distance(u: &[f64], v: &[f64]) -> Result<f64, String> {
    if u.len() != v.len() {
        return Err(format!(
            "Dimensional mismatch: u has {} dimensions, v has {}",
            u.len(),
            v.len()
        ));
    }
    if u.is_empty() {
        return Err("Vectors cannot be empty".to_string());
    }

    let diff_sq = squared_distance_simd(u, v);
    let u_sq = squared_norm_simd(u).min(1.0 - EPSILON);
    let v_sq = squared_norm_simd(v).min(1.0 - EPSILON);

    let denom = ((1.0 - u_sq) * (1.0 - v_sq)).max(EPSILON_DENOM);
    let arg = (1.0 + (2.0 * diff_sq / denom)).max(1.0);

    Ok(arg.acosh())
}

/// Computes Möbius addition in the Poincaré ball:
/// u (+) v = ((1 + 2<u, v> + ||v||^2)u + (1 - ||u||^2)v) / (1 + 2<u, v> + ||u||^2 * ||v||^2)
pub fn mobius_addition(u: &[f64], v: &[f64]) -> Result<Vec<f64>, String> {
    if u.len() != v.len() {
        return Err(format!(
            "Dimensional mismatch in mobius_addition: u has {}, v has {}",
            u.len(),
            v.len()
        ));
    }
    let dim = u.len();
    if dim == 0 {
        return Ok(Vec::new());
    }

    let dot = dot_product_simd(u, v);
    let u_sq = squared_norm_simd(u);
    let v_sq = squared_norm_simd(v);

    let denom = (1.0 + 2.0 * dot + u_sq * v_sq).max(EPSILON);
    let alpha = 1.0 + 2.0 * dot + v_sq;
    let beta = 1.0 - u_sq;

    let mut out = vec![0.0; dim];
    for i in 0..dim {
        out[i] = (alpha * u[i] + beta * v[i]) / denom;
    }

    Ok(out)
}

/// Radial contraction projection mapping any vector into the open unit ball B^D.
pub fn project_to_poincare_disk(v: &[f64], max_norm: f64) -> Vec<f64> {
    let norm = euclidean_norm(v);
    let bound = max_norm.min(1.0 - EPSILON);
    if norm >= bound && norm > 0.0 {
        let scale = bound / (norm + 1e-15);
        v.iter().map(|&x| x * scale).collect()
    } else {
        v.to_vec()
    }
}

// =========================================================================
// PyO3 Module Export Functions
// =========================================================================

/// Fast PyO3 Poincaré geodesic distance with SIMD auto-vectorization.
#[pyfunction]
pub fn fast_poincare_distance(u: Vec<f64>, v: Vec<f64>) -> PyResult<f64> {
    hyperbolic_distance(&u, &v).map_err(|e| PyValueError::new_err(e))
}

/// Fast PyO3 Poincaré conformal metric factor: lambda(x) = 2 / (1 - ||x||^2).
#[pyfunction]
pub fn fast_poincare_conformal_factor(v: Vec<f64>) -> PyResult<f64> {
    if v.is_empty() {
        return Err(PyValueError::new_err("Vector cannot be empty"));
    }
    Ok(conformal_factor(&v))
}

/// Fast PyO3 Möbius vector addition in Poincaré ball.
#[pyfunction]
pub fn fast_poincare_mobius_add(u: Vec<f64>, v: Vec<f64>) -> PyResult<Vec<f64>> {
    mobius_addition(&u, &v).map_err(|e| PyValueError::new_err(e))
}

/// Fast PyO3 parallel pairwise hyperbolic distance matrix computed via Rayon across all CPU threads.
#[pyfunction]
pub fn fast_poincare_pairwise_distances(points: Vec<Vec<f64>>) -> PyResult<Vec<Vec<f64>>> {
    let n = points.len();
    if n == 0 {
        return Ok(Vec::new());
    }
    let dim = points[0].len();
    if dim == 0 {
        return Err(PyValueError::new_err("Point dimension cannot be 0"));
    }

    for (idx, p) in points.iter().enumerate() {
        if p.len() != dim {
            return Err(PyValueError::new_err(format!(
                "Ragged points array: point 0 has dimension {dim}, but point {idx} has {}",
                p.len()
            )));
        }
    }

    // Precompute squared norms in parallel
    let sq_norms: Vec<f64> = points.par_iter().map(|p| squared_norm_simd(p)).collect();

    // Compute N x N distance matrix in parallel over rows
    let matrix: Vec<Vec<f64>> = (0..n)
        .into_par_iter()
        .map(|i| {
            let mut row = vec![0.0; n];
            let u = &points[i];
            let u_sq = sq_norms[i].min(1.0 - EPSILON);

            for j in 0..n {
                if i == j {
                    row[j] = 0.0;
                } else {
                    let v = &points[j];
                    let v_sq = sq_norms[j].min(1.0 - EPSILON);
                    let diff_sq = squared_distance_simd(u, v);
                    let denom = ((1.0 - u_sq) * (1.0 - v_sq)).max(EPSILON_DENOM);
                    let arg = (1.0 + (2.0 * diff_sq / denom)).max(1.0);
                    row[j] = arg.acosh();
                }
            }
            row
        })
        .collect();

    Ok(matrix)
}
