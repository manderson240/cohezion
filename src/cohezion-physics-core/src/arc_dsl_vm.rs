//! Ultra-fast Discrete Grid Transformation Virtual Machine and Hypothesis Evaluator
//! for ARC-AGI-2 and ARC-AGI-3.
//!
//! Provides zero-cost discrete operations and Rayon-parallelized candidate evaluation.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use rayon::prelude::*;
use std::collections::VecDeque;

/// Discrete 2D ARC Grid representation with a flat row-major buffer.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct ArcGrid {
    pub width: usize,
    pub height: usize,
    pub data: Vec<u8>,
}

impl ArcGrid {
    /// Creates a new grid filled with a default color.
    #[inline]
    pub fn new(width: usize, height: usize, fill: u8) -> Self {
        Self {
            width,
            height,
            data: vec![fill; width * height],
        }
    }

    /// Constructs an ArcGrid from a 2D vector, validating rectangularity.
    pub fn from_vec2d(grid: &[Vec<u8>]) -> Option<Self> {
        let height = grid.len();
        if height == 0 {
            return Some(Self {
                width: 0,
                height: 0,
                data: Vec::new(),
            });
        }
        let width = grid[0].len();
        for row in grid {
            if row.len() != width {
                return None;
            }
        }
        let mut data = Vec::with_capacity(width * height);
        for row in grid {
            data.extend_from_slice(row);
        }
        Some(Self {
            width,
            height,
            data,
        })
    }

    /// Converts back to a 2D vector.
    pub fn to_vec2d(&self) -> Vec<Vec<u8>> {
        if self.height == 0 || self.width == 0 {
            return Vec::new();
        }
        let mut out = Vec::with_capacity(self.height);
        for r in 0..self.height {
            let start = r * self.width;
            let end = start + self.width;
            out.push(self.data[start..end].to_vec());
        }
        out
    }

    /// Safe element access (returns 0 if out of bounds).
    #[inline(always)]
    pub fn get(&self, r: usize, c: usize) -> u8 {
        if r < self.height && c < self.width {
            self.data[r * self.width + c]
        } else {
            0
        }
    }

    /// Safe element mutation (ignored if out of bounds).
    #[inline(always)]
    pub fn set(&mut self, r: usize, c: usize, val: u8) {
        if r < self.height && c < self.width {
            self.data[r * self.width + c] = val;
        }
    }
}

// =========================================================================
// Primitive Transformations
// =========================================================================

/// Crops a subgrid bounded by [r1..=r2, c1..=c2] inclusive.
pub fn crop(grid: &ArcGrid, r1: usize, c1: usize, r2: usize, c2: usize) -> ArcGrid {
    if grid.width == 0
        || grid.height == 0
        || r1 > r2
        || c1 > c2
        || r1 >= grid.height
        || c1 >= grid.width
    {
        return ArcGrid::new(0, 0, 0);
    }
    let r2 = r2.min(grid.height - 1);
    let c2 = c2.min(grid.width - 1);
    let h = r2 - r1 + 1;
    let w = c2 - c1 + 1;
    let mut out = ArcGrid::new(w, h, 0);
    for r in 0..h {
        for c in 0..w {
            out.set(r, c, grid.get(r1 + r, c1 + c));
        }
    }
    out
}

/// Recolors all cells matching `from_color` to `to_color`.
pub fn recolor(grid: &ArcGrid, from_color: u8, to_color: u8) -> ArcGrid {
    let mut out = grid.clone();
    for cell in &mut out.data {
        if *cell == from_color {
            *cell = to_color;
        }
    }
    out
}

/// Retains only cells matching `color`, zeroing all other cells.
pub fn filter_color(grid: &ArcGrid, color: u8) -> ArcGrid {
    let mut out = grid.clone();
    for cell in &mut out.data {
        if *cell != color {
            *cell = 0;
        }
    }
    out
}

/// Drops non-zero cells in `direction`:
/// 0 = Down, 1 = Up, 2 = Left, 3 = Right.
pub fn gravity(grid: &ArcGrid, direction: u8) -> ArcGrid {
    if grid.width == 0 || grid.height == 0 {
        return grid.clone();
    }
    let mut out = ArcGrid::new(grid.width, grid.height, 0);
    let dir = direction % 4;
    match dir {
        0 => {
            // Down: non-zero cells drop to bottom
            for c in 0..grid.width {
                let mut vals = Vec::with_capacity(grid.height);
                for r in 0..grid.height {
                    let v = grid.get(r, c);
                    if v != 0 {
                        vals.push(v);
                    }
                }
                let count = vals.len();
                for (i, &v) in vals.iter().enumerate() {
                    let r = grid.height - count + i;
                    out.set(r, c, v);
                }
            }
        }
        1 => {
            // Up: non-zero cells rise to top
            for c in 0..grid.width {
                let mut vals = Vec::with_capacity(grid.height);
                for r in 0..grid.height {
                    let v = grid.get(r, c);
                    if v != 0 {
                        vals.push(v);
                    }
                }
                for (r, &v) in vals.iter().enumerate() {
                    out.set(r, c, v);
                }
            }
        }
        2 => {
            // Left: non-zero cells slide to left
            for r in 0..grid.height {
                let mut vals = Vec::with_capacity(grid.width);
                for c in 0..grid.width {
                    let v = grid.get(r, c);
                    if v != 0 {
                        vals.push(v);
                    }
                }
                for (c, &v) in vals.iter().enumerate() {
                    out.set(r, c, v);
                }
            }
        }
        3 => {
            // Right: non-zero cells slide to right
            for r in 0..grid.height {
                let mut vals = Vec::with_capacity(grid.width);
                for c in 0..grid.width {
                    let v = grid.get(r, c);
                    if v != 0 {
                        vals.push(v);
                    }
                }
                let count = vals.len();
                for (i, &v) in vals.iter().enumerate() {
                    let c = grid.width - count + i;
                    out.set(r, c, v);
                }
            }
        }
        _ => unreachable!(),
    }
    out
}

/// 4-connectivity flood fill object extraction:
/// Extracts monochromatic non-zero connected components into individual full-canvas grids.
pub fn connected_components(grid: &ArcGrid) -> Vec<ArcGrid> {
    if grid.width == 0 || grid.height == 0 {
        return Vec::new();
    }
    let mut visited = vec![false; grid.width * grid.height];
    let mut components = Vec::new();
    let dirs: [(isize, isize); 4] = [(-1, 0), (1, 0), (0, -1), (0, 1)];

    for r in 0..grid.height {
        for c in 0..grid.width {
            let idx = r * grid.width + c;
            let color = grid.data[idx];
            if color == 0 || visited[idx] {
                continue;
            }

            let mut comp = ArcGrid::new(grid.width, grid.height, 0);
            let mut queue = VecDeque::new();
            queue.push_back((r, c));
            visited[idx] = true;

            while let Some((curr_r, curr_c)) = queue.pop_front() {
                comp.set(curr_r, curr_c, color);

                for &(dr, dc) in &dirs {
                    let nr = curr_r as isize + dr;
                    let nc = curr_c as isize + dc;
                    if nr >= 0
                        && nr < grid.height as isize
                        && nc >= 0
                        && nc < grid.width as isize
                    {
                        let n_r = nr as usize;
                        let n_c = nc as usize;
                        let n_idx = n_r * grid.width + n_c;
                        if !visited[n_idx] && grid.data[n_idx] == color {
                            visited[n_idx] = true;
                            queue.push_back((n_r, n_c));
                        }
                    }
                }
            }
            components.push(comp);
        }
    }
    components
}

/// Returns bounding box (min_r, min_c, max_r, max_c) for all non-zero cells.
/// Returns (0, 0, 0, 0) if all cells are zero.
pub fn bounding_box(grid: &ArcGrid) -> (usize, usize, usize, usize) {
    let mut min_r = usize::MAX;
    let mut min_c = usize::MAX;
    let mut max_r = 0;
    let mut max_c = 0;
    let mut found = false;

    for r in 0..grid.height {
        for c in 0..grid.width {
            if grid.get(r, c) != 0 {
                found = true;
                if r < min_r {
                    min_r = r;
                }
                if r > max_r {
                    max_r = r;
                }
                if c < min_c {
                    min_c = c;
                }
                if c > max_c {
                    max_c = c;
                }
            }
        }
    }

    if found {
        (min_r, min_c, max_r, max_c)
    } else {
        (0, 0, 0, 0)
    }
}

// =========================================================================
// Spatial Rotations and Reflections
// =========================================================================

pub fn rot90(grid: &ArcGrid) -> ArcGrid {
    if grid.width == 0 || grid.height == 0 {
        return grid.clone();
    }
    let mut out = ArcGrid::new(grid.height, grid.width, 0);
    for r in 0..grid.height {
        for c in 0..grid.width {
            out.set(c, grid.height - 1 - r, grid.get(r, c));
        }
    }
    out
}

pub fn rot180(grid: &ArcGrid) -> ArcGrid {
    if grid.width == 0 || grid.height == 0 {
        return grid.clone();
    }
    let mut out = ArcGrid::new(grid.width, grid.height, 0);
    for r in 0..grid.height {
        for c in 0..grid.width {
            out.set(grid.height - 1 - r, grid.width - 1 - c, grid.get(r, c));
        }
    }
    out
}

pub fn rot270(grid: &ArcGrid) -> ArcGrid {
    if grid.width == 0 || grid.height == 0 {
        return grid.clone();
    }
    let mut out = ArcGrid::new(grid.height, grid.width, 0);
    for r in 0..grid.height {
        for c in 0..grid.width {
            out.set(grid.width - 1 - c, r, grid.get(r, c));
        }
    }
    out
}

pub fn flip_h(grid: &ArcGrid) -> ArcGrid {
    if grid.width == 0 || grid.height == 0 {
        return grid.clone();
    }
    let mut out = ArcGrid::new(grid.width, grid.height, 0);
    for r in 0..grid.height {
        for c in 0..grid.width {
            out.set(r, grid.width - 1 - c, grid.get(r, c));
        }
    }
    out
}

pub fn flip_v(grid: &ArcGrid) -> ArcGrid {
    if grid.width == 0 || grid.height == 0 {
        return grid.clone();
    }
    let mut out = ArcGrid::new(grid.width, grid.height, 0);
    for r in 0..grid.height {
        for c in 0..grid.width {
            out.set(grid.height - 1 - r, c, grid.get(r, c));
        }
    }
    out
}

pub fn transpose(grid: &ArcGrid) -> ArcGrid {
    if grid.width == 0 || grid.height == 0 {
        return grid.clone();
    }
    let mut out = ArcGrid::new(grid.height, grid.width, 0);
    for r in 0..grid.height {
        for c in 0..grid.width {
            out.set(c, r, grid.get(r, c));
        }
    }
    out
}

// =========================================================================
// Bytecode VM & Hypothesis Evaluator
// =========================================================================

/// Safely executes a bytecode sequence on an input grid.
///
/// Opcodes:
/// - 0: NOOP
/// - 1: IDENTITY
/// - 2: RECOLOR [from_color, to_color]
/// - 3: FILTER_COLOR [color]
/// - 4: GRAVITY [direction]
/// - 5: CROP [r1, c1, r2, c2]
/// - 6: CROP_TO_BOUNDING_BOX
/// - 7: ROT90
/// - 8: ROT180
/// - 9: ROT270
/// - 10: FLIP_H
/// - 11: FLIP_V
/// - 12: TRANSPOSE
/// - 13: EXTRACT_LARGEST_COMPONENT
/// - 14: EXTRACT_SMALLEST_COMPONENT
pub fn execute_program(mut grid: ArcGrid, bytecode: &[u8]) -> ArcGrid {
    let mut pc = 0;
    let len = bytecode.len();
    let max_instructions = 100;
    let mut count = 0;

    while pc < len && count < max_instructions {
        count += 1;
        let op = bytecode[pc];
        pc += 1;

        match op {
            0 | 1 => {}
            2 => {
                if pc + 1 < len {
                    let from_c = bytecode[pc];
                    let to_c = bytecode[pc + 1];
                    pc += 2;
                    grid = recolor(&grid, from_c, to_c);
                }
            }
            3 => {
                if pc < len {
                    let c = bytecode[pc];
                    pc += 1;
                    grid = filter_color(&grid, c);
                }
            }
            4 => {
                if pc < len {
                    let dir = bytecode[pc];
                    pc += 1;
                    grid = gravity(&grid, dir);
                }
            }
            5 => {
                if pc + 3 < len {
                    let r1 = bytecode[pc] as usize;
                    let c1 = bytecode[pc + 1] as usize;
                    let r2 = bytecode[pc + 2] as usize;
                    let c2 = bytecode[pc + 3] as usize;
                    pc += 4;
                    grid = crop(&grid, r1, c1, r2, c2);
                }
            }
            6 => {
                let (r1, c1, r2, c2) = bounding_box(&grid);
                grid = crop(&grid, r1, c1, r2, c2);
            }
            7 => grid = rot90(&grid),
            8 => grid = rot180(&grid),
            9 => grid = rot270(&grid),
            10 => grid = flip_h(&grid),
            11 => grid = flip_v(&grid),
            12 => grid = transpose(&grid),
            13 => {
                let comps = connected_components(&grid);
                if let Some(largest) = comps
                    .into_iter()
                    .max_by_key(|c| c.data.iter().filter(|&&x| x != 0).count())
                {
                    grid = largest;
                }
            }
            14 => {
                let comps = connected_components(&grid);
                if let Some(smallest) = comps
                    .into_iter()
                    .min_by_key(|c| c.data.iter().filter(|&&x| x != 0).count())
                {
                    grid = smallest;
                }
            }
            _ => {}
        }
    }
    grid
}

/// Evaluates similarity between predicted and target grids in [0.0, 1.0].
pub fn score_grid(pred: &ArcGrid, target: &ArcGrid) -> f64 {
    if pred.width == 0 || target.width == 0 || pred.height == 0 || target.height == 0 {
        return if pred == target { 1.0 } else { 0.0 };
    }
    if pred == target {
        return 1.0;
    }
    let max_cells = (pred.width * pred.height).max(target.width * target.height) as f64;
    let min_h = pred.height.min(target.height);
    let min_w = pred.width.min(target.width);
    let mut matches = 0;
    for r in 0..min_h {
        for c in 0..min_w {
            if pred.get(r, c) == target.get(r, c) {
                matches += 1;
            }
        }
    }
    let dim_factor = if pred.width == target.width && pred.height == target.height {
        1.0
    } else {
        0.5
    };
    (matches as f64 / max_cells) * dim_factor
}

// =========================================================================
// PyO3 Native Bindings
// =========================================================================

/// Multi-threaded Rayon hypothesis evaluator.
///
/// Given input/output demonstration pairs and a batch of candidate bytecodes,
/// scores and ranks candidates in parallel.
/// Returns sorted `(candidate_index, score)` pairs (descending).
#[pyfunction]
pub fn py_eval_arc_hypotheses(
    train_pairs: Vec<(Vec<Vec<u8>>, Vec<Vec<u8>>)>,
    candidates: Vec<Vec<u8>>,
) -> PyResult<Vec<(usize, f64)>> {
    let mut parsed_pairs = Vec::with_capacity(train_pairs.len());
    for (inp, out) in &train_pairs {
        let in_grid = ArcGrid::from_vec2d(inp).ok_or_else(|| {
            PyValueError::new_err("Invalid or ragged input grid in train_pairs")
        })?;
        let out_grid = ArcGrid::from_vec2d(out).ok_or_else(|| {
            PyValueError::new_err("Invalid or ragged output grid in train_pairs")
        })?;
        parsed_pairs.push((in_grid, out_grid));
    }

    if parsed_pairs.is_empty() {
        return Ok(candidates
            .into_iter()
            .enumerate()
            .map(|(i, _)| (i, 0.0))
            .collect());
    }

    let mut results: Vec<(usize, f64)> = candidates
        .par_iter()
        .enumerate()
        .map(|(idx, bytecode)| {
            let mut total_score = 0.0;
            for (in_grid, target_grid) in &parsed_pairs {
                let pred = execute_program(in_grid.clone(), bytecode);
                total_score += score_grid(&pred, target_grid);
            }
            let avg = total_score / parsed_pairs.len() as f64;
            (idx, avg)
        })
        .collect();

    results.sort_by(|a, b| {
        b.1.partial_cmp(&a.1)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| a.0.cmp(&b.0))
    });

    Ok(results)
}

/// 4-connectivity flood fill object extraction.
#[pyfunction]
pub fn py_extract_connected_components(grid: Vec<Vec<u8>>) -> PyResult<Vec<Vec<Vec<u8>>>> {
    let arc_grid = ArcGrid::from_vec2d(&grid)
        .ok_or_else(|| PyValueError::new_err("Invalid or ragged grid"))?;
    let comps = connected_components(&arc_grid);
    Ok(comps.into_iter().map(|c| c.to_vec2d()).collect())
}

#[pyfunction]
pub fn py_recolor(
    grid: Vec<Vec<u8>>,
    from_color: u8,
    to_color: u8,
) -> PyResult<Vec<Vec<u8>>> {
    let arc_grid = ArcGrid::from_vec2d(&grid)
        .ok_or_else(|| PyValueError::new_err("Invalid or ragged grid"))?;
    Ok(recolor(&arc_grid, from_color, to_color).to_vec2d())
}

#[pyfunction]
pub fn py_filter_color(grid: Vec<Vec<u8>>, color: u8) -> PyResult<Vec<Vec<u8>>> {
    let arc_grid = ArcGrid::from_vec2d(&grid)
        .ok_or_else(|| PyValueError::new_err("Invalid or ragged grid"))?;
    Ok(filter_color(&arc_grid, color).to_vec2d())
}

#[pyfunction]
pub fn py_gravity(grid: Vec<Vec<u8>>, direction: u8) -> PyResult<Vec<Vec<u8>>> {
    let arc_grid = ArcGrid::from_vec2d(&grid)
        .ok_or_else(|| PyValueError::new_err("Invalid or ragged grid"))?;
    Ok(gravity(&arc_grid, direction).to_vec2d())
}

#[pyfunction]
pub fn py_crop(
    grid: Vec<Vec<u8>>,
    r1: usize,
    c1: usize,
    r2: usize,
    c2: usize,
) -> PyResult<Vec<Vec<u8>>> {
    let arc_grid = ArcGrid::from_vec2d(&grid)
        .ok_or_else(|| PyValueError::new_err("Invalid or ragged grid"))?;
    Ok(crop(&arc_grid, r1, c1, r2, c2).to_vec2d())
}

#[pyfunction]
pub fn py_bounding_box(grid: Vec<Vec<u8>>) -> PyResult<(usize, usize, usize, usize)> {
    let arc_grid = ArcGrid::from_vec2d(&grid)
        .ok_or_else(|| PyValueError::new_err("Invalid or ragged grid"))?;
    Ok(bounding_box(&arc_grid))
}

#[pyfunction]
pub fn py_execute_arc_dsl(
    grid: Vec<Vec<u8>>,
    bytecode: Vec<u8>,
) -> PyResult<Vec<Vec<u8>>> {
    let arc_grid = ArcGrid::from_vec2d(&grid)
        .ok_or_else(|| PyValueError::new_err("Invalid or ragged grid"))?;
    Ok(execute_program(arc_grid, &bytecode).to_vec2d())
}
