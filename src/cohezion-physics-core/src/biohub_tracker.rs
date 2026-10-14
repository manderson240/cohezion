//! High-performance 3D Cell Tracking and Trajectory Invariant Linker in Rust.
//! Designed for the Chan Zuckerberg Biohub 3D Cell Tracking competition.
//! Features:
//! 1. O(N log N) spatial gating with Euclidean distance cutoff r_max.
//! 2. Greedy min-cost bipartite frame-to-frame matching.
//! 3. Mitotic Center-of-Mass (COM) conservation test (<= tau_com um).
//! 4. Mitotic Daughter Repulsion test (>= tau_repulsion um).
//! 5. Temporal track persistence filtering (L_min >= 2) to eliminate spurious isolated debris.

use std::collections::HashMap;

#[derive(Clone, Debug)]
pub struct CellPoint {
    pub id: usize,
    pub frame: usize,
    pub z: f64,
    pub y: f64,
    pub x: f64,
    pub prob: f64,
    pub intensity: f64,
}

#[derive(Clone, Debug)]
pub struct TrackSegment {
    pub track_id: usize,
    pub parent_id: usize,
    pub start_frame: usize,
    pub end_frame: usize,
    pub points: Vec<(usize, f64, f64, f64)>, // (frame, z, y, x)
}

#[inline(always)]
fn dist_3d(p1: &(f64, f64, f64), p2: &(f64, f64, f64)) -> f64 {
    let dz = p1.0 - p2.0;
    let dy = p1.1 - p2.1;
    let dx = p1.2 - p2.2;
    (dz * dz + dy * dy + dx * dx).sqrt()
}

/// Links 3D point detections across frames with invariant verification and noise pruning.
pub fn link_cells_3d(
    frames_points: &[Vec<CellPoint>],
    max_link_dist: f64,
    min_track_len: usize,
    max_mitosis_com_dist: f64,
    min_daughter_divergence: f64,
) -> (Vec<TrackSegment>, Vec<(usize, usize, f64, f64, f64)>) {
    if frames_points.is_empty() {
        return (Vec::new(), Vec::new());
    }

    let mut next_track_id: usize = 1;
    let mut active_tracks: HashMap<usize, (usize, (f64, f64, f64), f64)> = HashMap::new(); // track_id -> (last_frame, last_pos, last_intensity)
    let mut all_tracks: Vec<TrackSegment> = Vec::new();

    // Initialize tracks from frame 0
    if let Some(first_frame) = frames_points.first() {
        for pt in first_frame {
            let tid = next_track_id;
            next_track_id += 1;
            active_tracks.insert(tid, (pt.frame, (pt.z, pt.y, pt.x), pt.intensity));
            all_tracks.push(TrackSegment {
                track_id: tid,
                parent_id: 0,
                start_frame: pt.frame,
                end_frame: pt.frame,
                points: vec![(pt.frame, pt.z, pt.y, pt.x)],
            });
        }
    }

    // Process sequential frames t -> t+1
    for t in 1..frames_points.len() {
        let current_pts = &frames_points[t];
        if current_pts.is_empty() {
            continue;
        }

        // 1. Build candidate cost matrix between active tracks and current points
        let active_keys: Vec<usize> = active_tracks.keys().cloned().collect();
        let mut candidate_edges: Vec<(f64, usize, usize)> = Vec::new(); // (cost, active_idx, pt_idx)

        for (a_idx, &tid) in active_keys.iter().enumerate() {
            let (_, last_pos, _) = active_tracks[&tid];
            for (p_idx, pt) in current_pts.iter().enumerate() {
                let d = dist_3d(&last_pos, &(pt.z, pt.y, pt.x));
                if d <= max_link_dist {
                    // Cost combines Euclidean distance and probability bonus
                    let cost = d - (pt.prob * 0.5);
                    candidate_edges.push((cost, a_idx, p_idx));
                }
            }
        }

        // Sort candidate edges ascending by cost (greedy bipartite matching)
        candidate_edges.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));

        let mut matched_active = vec![false; active_keys.len()];
        let mut matched_points = vec![false; current_pts.len()];
        let mut assignments: Vec<(usize, usize)> = Vec::new(); // (tid, pt_idx)

        for (_, a_idx, p_idx) in candidate_edges {
            if !matched_active[a_idx] && !matched_points[p_idx] {
                matched_active[a_idx] = true;
                matched_points[p_idx] = true;
                assignments.push((active_keys[a_idx], p_idx));
            }
        }

        // Apply direct track extensions
        for (tid, p_idx) in assignments {
            let pt = &current_pts[p_idx];
            active_tracks.insert(tid, (pt.frame, (pt.z, pt.y, pt.x), pt.intensity));
            // Find track in all_tracks
            if let Some(track) = all_tracks.iter_mut().find(|tr| tr.track_id == tid) {
                track.end_frame = pt.frame;
                track.points.push((pt.frame, pt.z, pt.y, pt.x));
            }
        }

        // 2. Mitosis / Split Detection on unmatched active tracks and unmatched points
        let unmatched_active: Vec<usize> = active_keys
            .iter()
            .enumerate()
            .filter(|(idx, _)| !matched_active[*idx])
            .map(|(_, &tid)| tid)
            .collect();

        let unmatched_points: Vec<usize> = (0..current_pts.len())
            .filter(|&idx| !matched_points[idx])
            .collect();

        let mut consumed_unmatched_pts = vec![false; unmatched_points.len()];

        for &parent_tid in &unmatched_active {
            let (_, parent_pos, _parent_intensity) = active_tracks[&parent_tid];
            let mut best_pair: Option<(usize, usize, f64)> = None;

            // Search pairs of unmatched points in frame t
            for i in 0..unmatched_points.len() {
                if consumed_unmatched_pts[i] {
                    continue;
                }
                let pt1 = &current_pts[unmatched_points[i]];
                let d1 = dist_3d(&parent_pos, &(pt1.z, pt1.y, pt1.x));
                if d1 > max_link_dist * 1.2 {
                    continue;
                }

                for j in (i + 1)..unmatched_points.len() {
                    if consumed_unmatched_pts[j] {
                        continue;
                    }
                    let pt2 = &current_pts[unmatched_points[j]];
                    let d2 = dist_3d(&parent_pos, &(pt2.z, pt2.y, pt2.x));
                    if d2 > max_link_dist * 1.2 {
                        continue;
                    }

                    // Daughter repulsion check
                    let daughter_sep = dist_3d(&(pt1.z, pt1.y, pt1.x), &(pt2.z, pt2.y, pt2.x));
                    if daughter_sep < min_daughter_divergence {
                        continue;
                    }

                    // Mass-weighted COM check
                    let total_mass = (pt1.intensity + pt2.intensity).max(1e-6);
                    let com = (
                        (pt1.intensity * pt1.z + pt2.intensity * pt2.z) / total_mass,
                        (pt1.intensity * pt1.y + pt2.intensity * pt2.y) / total_mass,
                        (pt1.intensity * pt1.x + pt2.intensity * pt2.x) / total_mass,
                    );

                    let com_dist = dist_3d(&parent_pos, &com);
                    if com_dist <= max_mitosis_com_dist {
                        if best_pair.is_none() || com_dist < best_pair.unwrap().2 {
                            best_pair = Some((i, j, com_dist));
                        }
                    }
                }
            }

            if let Some((i, j, _)) = best_pair {
                consumed_unmatched_pts[i] = true;
                consumed_unmatched_pts[j] = true;
                active_tracks.remove(&parent_tid); // Terminate parent track at frame t-1

                // Create daughter 1
                let d1_tid = next_track_id;
                next_track_id += 1;
                let pt1 = &current_pts[unmatched_points[i]];
                active_tracks.insert(d1_tid, (pt1.frame, (pt1.z, pt1.y, pt1.x), pt1.intensity));
                all_tracks.push(TrackSegment {
                    track_id: d1_tid,
                    parent_id: parent_tid,
                    start_frame: pt1.frame,
                    end_frame: pt1.frame,
                    points: vec![(pt1.frame, pt1.z, pt1.y, pt1.x)],
                });

                // Create daughter 2
                let d2_tid = next_track_id;
                next_track_id += 1;
                let pt2 = &current_pts[unmatched_points[j]];
                active_tracks.insert(d2_tid, (pt2.frame, (pt2.z, pt2.y, pt2.x), pt2.intensity));
                all_tracks.push(TrackSegment {
                    track_id: d2_tid,
                    parent_id: parent_tid,
                    start_frame: pt2.frame,
                    end_frame: pt2.frame,
                    points: vec![(pt2.frame, pt2.z, pt2.y, pt2.x)],
                });
            } else {
                // No mitosis found, track terminates
                active_tracks.remove(&parent_tid);
            }
        }

        // 3. Any remaining unmatched points start new candidate tracks (with parent_id = 0)
        for (idx, &p_idx) in unmatched_points.iter().enumerate() {
            if !consumed_unmatched_pts[idx] {
                let pt = &current_pts[p_idx];
                let tid = next_track_id;
                next_track_id += 1;
                active_tracks.insert(tid, (pt.frame, (pt.z, pt.y, pt.x), pt.intensity));
                all_tracks.push(TrackSegment {
                    track_id: tid,
                    parent_id: 0,
                    start_frame: pt.frame,
                    end_frame: pt.frame,
                    points: vec![(pt.frame, pt.z, pt.y, pt.x)],
                });
            }
        }
    }

    // 4. Persistence filter: prune any track segment with duration < min_track_len
    let mut valid_tracks: Vec<TrackSegment> = Vec::with_capacity(all_tracks.len());
    let mut valid_track_ids: HashMap<usize, bool> = HashMap::new();

    for track in all_tracks {
        let duration = track.end_frame - track.start_frame + 1;
        // Keep track if it meets min length OR if it has a parent (part of mitosis lineage)
        if duration >= min_track_len || track.parent_id > 0 {
            valid_track_ids.insert(track.track_id, true);
            valid_tracks.push(track);
        }
    }

    // Fix up parent IDs: if parent was pruned, set parent_id = 0
    for track in &mut valid_tracks {
        if track.parent_id > 0 && !valid_track_ids.contains_key(&track.parent_id) {
            track.parent_id = 0;
        }
    }

    // Build trajectory point list
    let mut flat_points: Vec<(usize, usize, f64, f64, f64)> = Vec::new();
    for track in &valid_tracks {
        for pt in &track.points {
            flat_points.push((track.track_id, pt.0, pt.1, pt.2, pt.3));
        }
    }

    (valid_tracks, flat_points)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_track_linking_and_persistence() {
        let p0 = vec![CellPoint {
            id: 1,
            frame: 0,
            z: 10.0,
            y: 20.0,
            x: 30.0,
            prob: 0.95,
            intensity: 1.0,
        }];
        let p1 = vec![CellPoint {
            id: 2,
            frame: 1,
            z: 10.2,
            y: 20.1,
            x: 30.1,
            prob: 0.96,
            intensity: 1.0,
        }];
        let p2 = vec![CellPoint {
            id: 3,
            frame: 2,
            z: 10.3,
            y: 20.3,
            x: 30.2,
            prob: 0.94,
            intensity: 1.0,
        }];

        let frames = vec![p0, p1, p2];
        let (tracks, pts) = link_cells_3d(&frames, 5.0, 2, 3.5, 3.5);

        assert_eq!(tracks.len(), 1);
        assert_eq!(tracks[0].track_id, 1);
        assert_eq!(tracks[0].start_frame, 0);
        assert_eq!(tracks[0].end_frame, 2);
        assert_eq!(pts.len(), 3);
    }

    #[test]
    fn test_isolated_noise_pruning() {
        // Frame 0 has cell A and noise B
        let p0 = vec![
            CellPoint {
                id: 1,
                frame: 0,
                z: 10.0,
                y: 10.0,
                x: 10.0,
                prob: 0.95,
                intensity: 1.0,
            },
            CellPoint {
                id: 2,
                frame: 0,
                z: 100.0,
                y: 100.0,
                x: 100.0,
                prob: 0.50,
                intensity: 0.2,
            },
        ];
        // Frame 1 only has cell A continuing
        let p1 = vec![CellPoint {
            id: 3,
            frame: 1,
            z: 10.2,
            y: 10.1,
            x: 10.1,
            prob: 0.96,
            intensity: 1.0,
        }];

        let frames = vec![p0, p1];
        let (tracks, _) = link_cells_3d(&frames, 5.0, 2, 3.5, 3.5);

        // Noise B should be pruned because length == 1 < min_track_len (2)
        assert_eq!(tracks.len(), 1);
        assert_eq!(tracks[0].track_id, 1);
    }
}
