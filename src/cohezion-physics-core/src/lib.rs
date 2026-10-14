use pyo3::prelude::*;
use numpy::PyReadwriteArray1;
use pyo3::types::PyModule;

mod vmodel_verifier;
use vmodel_verifier::{fast_kahn_topological_sort, verify_monad_laws_fast, verify_deterministic_bounds};

mod arc_dsl_vm;
use arc_dsl_vm::{
    py_bounding_box, py_crop, py_eval_arc_hypotheses, py_execute_arc_dsl,
    py_extract_connected_components, py_filter_color, py_gravity, py_recolor,
};

mod poincare_hyperbolic;
use poincare_hyperbolic::{
    fast_poincare_conformal_factor,
    fast_poincare_distance,
    fast_poincare_mobius_add,
    fast_poincare_pairwise_distances,
};

/// Evolves a 1D Cellular Automata grid by one step using the given Wolfram rule.
/// Uses basic auto-vectorization for SIMD execution on the loops.
#[pyfunction]
fn evolve_ca_simd(state: Vec<u8>, rule: u8) -> PyResult<Vec<u8>> {
    let n = state.len();
    if n == 0 {
        return Ok(state);
    }
    
    let mut next_state = vec![0u8; n];
    
    // Extracted rule bits
    let mut patterns = [0u8; 8];
    for i in 0..8 {
        patterns[i] = (rule >> i) & 1;
    }

    for i in 0..n {
        let left = state[(i + n - 1) % n] as usize;
        let center = state[i] as usize;
        let right = state[(i + 1) % n] as usize;
        
        let idx = (left << 2) | (center << 1) | right;
        next_state[i] = patterns[idx];
    }

    Ok(next_state)
}

/// Computes MHD forces using highly optimized Rust math.
/// Modifies the `vec` array in-place.
#[pyfunction]
fn apply_mhd_forces_simd(
    mut vec: PyReadwriteArray1<'_, f64>, 
    helicity: f64, 
    toroidal_moment: f64, 
    dt: f64
) -> PyResult<()> {
    let twist_angle = helicity * dt;
    let cos_theta = twist_angle.cos();
    let sin_theta = twist_angle.sin();
    
    let mut arr = vec.as_array_mut();
    
    if arr.len() >= 2 {
        let v0 = arr[0];
        let v1 = arr[1];
        arr[0] = v0 * cos_theta - v1 * sin_theta;
        arr[1] = v0 * sin_theta + v1 * cos_theta;
    }
    
    let current_norm: f64 = arr.iter().map(|&x| x * x).sum::<f64>().sqrt();
    
    if current_norm > 0.0 {
        let scale_factor = 1.0 + (toroidal_moment - current_norm) * 0.1 * dt;
        for el in arr.iter_mut() {
            *el *= scale_factor;
        }
    }

    Ok(())
}

/// 64-bit Zobrist Hash for 2D cellular grid states.
/// Generates deterministic pseudo-random XOR keys from splitmix64.
#[pyfunction]
fn zobrist_hash_grid(grid: Vec<Vec<u8>>, seed: u64) -> PyResult<u64> {
    let h = grid.len();
    if h == 0 {
        return Ok(0);
    }
    let w = grid[0].len();
    if w == 0 {
        return Ok(0);
    }

    // Pre-validate rectangularity to prevent out-of-bounds indexing
    for r in 0..h {
        if grid[r].len() != w {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Ragged grid detected in zobrist_hash_grid: row {r} has length {}, expected {w}",
                grid[r].len()
            )));
        }
    }

    // Splitmix64 PRNG to generate table
    let mut hash: u64 = 0;
    for r in 0..h {
        for c in 0..w {
            let color = grid[r][c] as u64;
            if color > 0 {
                let cell_idx = (r * w + c) as u64;
                let mut state = seed.wrapping_add(cell_idx.wrapping_mul(0x9E3779B97F4A7C15)).wrapping_add(color.wrapping_mul(0xBF58476D1CE4E5B9));
                // 3 rounds of splitmix64
                state = (state ^ (state >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
                state = (state ^ (state >> 27)).wrapping_mul(0x94D049BB133111EB);
                let z_key = state ^ (state >> 31);
                hash ^= z_key;
            }
        }
    }
    Ok(hash)
}

/// D4 Dihedral group transformation on 2D grids (8 rotations & reflections).
/// k in 0..7: 0=identity, 1=rot90, 2=rot180, 3=rot270, 4=flip_h, 5=flip_v, 6=transpose, 7=anti-transpose.
#[pyfunction]
fn d4_transform(grid: Vec<Vec<u8>>, k: u8) -> PyResult<Vec<Vec<u8>>> {
    let h = grid.len();
    if h == 0 {
        return Ok(grid);
    }
    let w = grid[0].len();
    if w == 0 {
        return Ok(grid);
    }

    // Pre-validate rectangularity to prevent out-of-bounds indexing
    for r in 0..h {
        if grid[r].len() != w {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Ragged grid detected in d4_transform: row {r} has length {}, expected {w}",
                grid[r].len()
            )));
        }
    }

    let mode = k % 8;
    match mode {
        0 => Ok(grid),
        1 => {
            // rot90 clockwise: new height is w, new width is h
            let mut out = vec![vec![0u8; h]; w];
            for r in 0..h {
                for c in 0..w {
                    out[c][h - 1 - r] = grid[r][c];
                }
            }
            Ok(out)
        }
        2 => {
            // rot180
            let mut out = vec![vec![0u8; w]; h];
            for r in 0..h {
                for c in 0..w {
                    out[h - 1 - r][w - 1 - c] = grid[r][c];
                }
            }
            Ok(out)
        }
        3 => {
            // rot270 clockwise
            let mut out = vec![vec![0u8; h]; w];
            for r in 0..h {
                for c in 0..w {
                    out[w - 1 - c][r] = grid[r][c];
                }
            }
            Ok(out)
        }
        4 => {
            // flip horizontal (left-right)
            let mut out = vec![vec![0u8; w]; h];
            for r in 0..h {
                for c in 0..w {
                    out[r][w - 1 - c] = grid[r][c];
                }
            }
            Ok(out)
        }
        5 => {
            // flip vertical (up-down)
            let mut out = vec![vec![0u8; w]; h];
            for r in 0..h {
                for c in 0..w {
                    out[h - 1 - r][c] = grid[r][c];
                }
            }
            Ok(out)
        }
        6 => {
            // transpose (main diagonal)
            let mut out = vec![vec![0u8; h]; w];
            for r in 0..h {
                for c in 0..w {
                    out[c][r] = grid[r][c];
                }
            }
            Ok(out)
        }
        7 => {
            // anti-transpose
            let mut out = vec![vec![0u8; h]; w];
            for r in 0..h {
                for c in 0..w {
                    out[w - 1 - c][h - 1 - r] = grid[r][c];
                }
            }
            Ok(out)
        }
        _ => Ok(grid),
    }
}

/// Strict Mitotic Center-of-Mass (COM) conservation test in 3D.
/// Verifies whether the mass-weighted center of daughters d1 and d2 is within `threshold` um of parent.
/// Supports asymmetric cytokinesis via intensity/volume weights i1 and i2.
#[pyfunction]
#[pyo3(signature = (parent, d1, d2, threshold=3.5, i1=1.0, i2=1.0))]
fn verify_mitotic_com(
    parent: (f64, f64, f64),
    d1: (f64, f64, f64),
    d2: (f64, f64, f64),
    threshold: f64,
    i1: f64,
    i2: f64,
) -> PyResult<bool> {
    let total_mass = (i1 + i2).max(1e-6);
    let com_x = (i1 * d1.0 + i2 * d2.0) / total_mass;
    let com_y = (i1 * d1.1 + i2 * d2.1) / total_mass;
    let com_z = (i1 * d1.2 + i2 * d2.2) / total_mass;

    let dx = com_x - parent.0;
    let dy = com_y - parent.1;
    let dz = com_z - parent.2;

    let dist_sq = dx * dx + dy * dy + dz * dz;
    Ok(dist_sq <= threshold * threshold)
}

/// Strict Mitotic Daughter Divergence test across frames t+1 and t+2.
/// Returns (divergence_distance, is_valid).
#[pyfunction]
fn verify_daughter_divergence(
    d1_t1: (f64, f64, f64),
    d2_t1: (f64, f64, f64),
    d1_t2: (f64, f64, f64),
    d2_t2: (f64, f64, f64),
    min_divergence: f64,
) -> PyResult<(f64, bool)> {
    let sister_dist_t1 = ((d1_t1.0 - d2_t1.0).powi(2) + (d1_t1.1 - d2_t1.1).powi(2) + (d1_t1.2 - d2_t1.2).powi(2)).sqrt();
    let sister_dist_t2 = ((d1_t2.0 - d2_t2.0).powi(2) + (d1_t2.1 - d2_t2.1).powi(2) + (d1_t2.2 - d2_t2.2).powi(2)).sqrt();

    let divergence = sister_dist_t2 - sister_dist_t1;
    let is_valid = divergence >= min_divergence;
    Ok((divergence, is_valid))
}

mod kaggriculture_sim;
use kaggriculture_sim::{PolicyParams, simulate_parallel_rollouts, AdversarialMarketParams, simulate_adversarial_rollouts};

mod biohub_tracker;
use biohub_tracker::{CellPoint, link_cells_3d};

/// Fast parallel Kaggriculture rollout simulator using Rayon across all CPU cores.
/// Returns (mean_coins, min_coins, max_coins, win_rate_vs_benchmark).
#[pyfunction]
#[pyo3(signature = (num_sims=10000, base_seed=42, slow_crop_freeze_day=27, dutch_auction_day=27, liquidation_day=28, fertilizer_liquidation_day=29))]
fn simulate_kaggriculture_rollouts(
    num_sims: usize,
    base_seed: u64,
    slow_crop_freeze_day: u32,
    dutch_auction_day: u32,
    liquidation_day: u32,
    fertilizer_liquidation_day: u32,
) -> PyResult<(f64, f64, f64, f64)> {
    let params = PolicyParams {
        slow_crop_freeze_day,
        dutch_auction_day,
        liquidation_day,
        fertilizer_liquidation_day,
        min_spot_price_sell: 5.0,
    };
    Ok(simulate_parallel_rollouts(num_sims, base_seed, &params))
}

/// Fast parallel Kaggriculture adversarial rollout simulator using Rayon.
/// Models predatory competitor dumping on predatory_dump_day with dump_crash_factor.
/// Returns (mean_coins, min_coins, max_coins, win_rate_vs_benchmark).
#[pyfunction]
#[pyo3(signature = (num_sims=10000, base_seed=42, slow_crop_freeze_day=25, dutch_auction_day=25, liquidation_day=27, fertilizer_liquidation_day=28, predatory_dump_day=26, dump_crash_factor=0.35))]
fn simulate_adversarial_kaggriculture_rollouts(
    num_sims: usize,
    base_seed: u64,
    slow_crop_freeze_day: u32,
    dutch_auction_day: u32,
    liquidation_day: u32,
    fertilizer_liquidation_day: u32,
    predatory_dump_day: u32,
    dump_crash_factor: f64,
) -> PyResult<(f64, f64, f64, f64)> {
    let params = AdversarialMarketParams {
        slow_crop_freeze_day,
        dutch_auction_day,
        liquidation_day,
        fertilizer_liquidation_day,
        min_spot_price_sell: 5.0,
        predatory_dump_day,
        dump_crash_factor,
    };
    Ok(simulate_adversarial_rollouts(num_sims, base_seed, &params))
}

/// Fast 3D Cell Tracking with spatial gating, mitotic COM invariant verification, and noise persistence pruning.
/// Takes frames of detections: Vec<Vec<(z, y, x, prob, intensity)>>
/// Returns:
/// 1. tracks_summary: Vec<(track_id, start_frame, end_frame, parent_id)>
/// 2. trajectory_points: Vec<(track_id, frame, z, y, x)>
#[pyfunction]
#[pyo3(signature = (frames_detections, max_link_dist=7.0, min_track_len=2, max_mitosis_com_dist=3.5, min_daughter_divergence=3.5))]
fn fast_track_cells_3d(
    frames_detections: Vec<Vec<(f64, f64, f64, f64, f64)>>,
    max_link_dist: f64,
    min_track_len: usize,
    max_mitosis_com_dist: f64,
    min_daughter_divergence: f64,
) -> PyResult<(Vec<(usize, usize, usize, usize)>, Vec<(usize, usize, f64, f64, f64)>)> {
    let mut frames_points: Vec<Vec<CellPoint>> = Vec::with_capacity(frames_detections.len());
    let mut point_id = 1;
    for (f_idx, frame) in frames_detections.iter().enumerate() {
        let mut pts = Vec::with_capacity(frame.len());
        for item in frame {
            pts.push(CellPoint {
                id: point_id,
                frame: f_idx,
                z: item.0,
                y: item.1,
                x: item.2,
                prob: item.3,
                intensity: item.4,
            });
            point_id += 1;
        }
        frames_points.push(pts);
    }

    let (tracks, flat_pts) = link_cells_3d(
        &frames_points,
        max_link_dist,
        min_track_len,
        max_mitosis_com_dist,
        min_daughter_divergence,
    );

    let summary = tracks
        .into_iter()
        .map(|tr| (tr.track_id, tr.start_frame, tr.end_frame, tr.parent_id))
        .collect();

    Ok((summary, flat_pts))
}

/// A Python module implemented in Rust.
#[pymodule]
fn cohezion_physics_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(evolve_ca_simd, m)?)?;
    m.add_function(wrap_pyfunction!(apply_mhd_forces_simd, m)?)?;
    m.add_function(wrap_pyfunction!(zobrist_hash_grid, m)?)?;
    m.add_function(wrap_pyfunction!(d4_transform, m)?)?;
    m.add_function(wrap_pyfunction!(verify_mitotic_com, m)?)?;
    m.add_function(wrap_pyfunction!(verify_daughter_divergence, m)?)?;
    m.add_function(wrap_pyfunction!(simulate_kaggriculture_rollouts, m)?)?;
    m.add_function(wrap_pyfunction!(simulate_adversarial_kaggriculture_rollouts, m)?)?;
    m.add_function(wrap_pyfunction!(fast_track_cells_3d, m)?)?;
    m.add_function(wrap_pyfunction!(fast_kahn_topological_sort, m)?)?;
    m.add_function(wrap_pyfunction!(verify_monad_laws_fast, m)?)?;
    m.add_function(wrap_pyfunction!(verify_deterministic_bounds, m)?)?;
    // ARC DSL VM & Hypothesis Evaluator
    m.add_function(wrap_pyfunction!(py_eval_arc_hypotheses, m)?)?;
    m.add_function(wrap_pyfunction!(py_extract_connected_components, m)?)?;
    m.add_function(wrap_pyfunction!(py_recolor, m)?)?;
    m.add_function(wrap_pyfunction!(py_filter_color, m)?)?;
    m.add_function(wrap_pyfunction!(py_gravity, m)?)?;
    m.add_function(wrap_pyfunction!(py_crop, m)?)?;
    m.add_function(wrap_pyfunction!(py_bounding_box, m)?)?;
    m.add_function(wrap_pyfunction!(py_execute_arc_dsl, m)?)?;
    // SIMD & Rayon 2048D Poincare Hyperbolic Manifold
    m.add_function(wrap_pyfunction!(fast_poincare_distance, m)?)?;
    m.add_function(wrap_pyfunction!(fast_poincare_conformal_factor, m)?)?;
    m.add_function(wrap_pyfunction!(fast_poincare_mobius_add, m)?)?;
    m.add_function(wrap_pyfunction!(fast_poincare_pairwise_distances, m)?)?;
    Ok(())
}

