use pyo3::prelude::*;
use numpy::PyReadwriteArray1;
use pyo3::types::PyModule;

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

/// A Python module implemented in Rust.
#[pymodule]
fn cohezion_physics_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(evolve_ca_simd, m)?)?;
    m.add_function(wrap_pyfunction!(apply_mhd_forces_simd, m)?)?;
    Ok(())
}
