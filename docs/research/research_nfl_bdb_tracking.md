# NFL Big Data Bowl 2027 Spatio-Temporal Kinematics

We need answer user. Need synthesize Python verification function verify_nfl_bdb_invariants(df_sample: dict) -> bool. Need understand request. They want for NFL Big Data Bowl 2027 combine-to-game tracking transfer. Need mathematically verifies invariants: coordinate normalization, kinematic continuity, pass-rush pressure semantics, Voronoi spatial dominance or closing vector calculation. Need enclose valid Python code in ```python ```.

We need craft function. Input df_sample: dict. Need likely dict of arrays? Need infer. We can design robust. Need return bool. Need include checks. Need maybe use numpy. Need handle missing. Need define invariants.

We need produce code only? User asks "synthesize a Python verification function ... Enclose valid Python code in ```python ```." We can include code. Need maybe no explanation? Desired oververbosity 5. We can provide code with comments. Need ensure valid Python.

Need think deeply about invariants.

We need define df_sample dict. Could be dictionary of columns. We can assume keys like 'x', 'y', 'dir', 'o', 's', 'a', 'quick_pressure', 'blitz', 'pressure', 'get_off', 'is_rushing', 'voronoi_area', 'closing_vector_x', 'closing_vector_y', etc. Need verify.

Need make function robust to missing keys? If missing, maybe return False? Or skip? "verifies" likely all required. We can implement helper.

Need coordinate normalization: x in [0,120], y in [0,53.3], direction oriented toward offensive endzone. Direction? In NFL tracking, dir is degrees clockwise from north? Need "direction oriented toward offensive endzone" maybe check dir in [0,360) and if play direction? Need maybe use 'play_direction' or 'offense_endzone_side'. Could check if direction vector has positive x component when offense moving right? Need define. We can check x,y bounds and dir between 0 and 360. "direction oriented toward offensive endzone" maybe need ensure if 'dir' is present, its unit vector dot with offensive endzone vector >= 0? But direction is player orientation, not velocity. Need maybe check 'dir' in [0, 360) and 'o' in [0,360). Could include optional check: if 'offensive_endzone_direction' present, compute vector from dir and ensure dot with endzone direction >= 0? But player direction can be any orientation, not necessarily toward endzone. The prompt says "direction oriented toward offensive endzone" maybe means coordinate system normalized so x-axis points toward offensive endzone. So check x in [0,120], y in [0,53.3], and if 'play_direction' or 'offensive_endzone_direction' present, ensure it is either +x or -x? Hmm.

Need maybe implement:
- x between 0 and 120 inclusive with tolerance.
- y between 0 and 53.3 inclusive.
- direction angle in [0, 360) if present.
- If 'offensive_endzone_direction' column exists, check values are either 1 or -1? Or if 'play_direction' exists, check in {'left','right'}? But not necessary.

Kinematic continuity: speed s >= 0, acceleration a = dv/dt bounded by human physiology <= 12.0 m/s^2. Need check s >= 0, a absolute <= 12.0. Also maybe compute acceleration from speed differences if a missing? Need "a = dv/dt bounded". We can check if 'a' present, abs(a) <= 12.0. If 's' present, s >= -tol. If 'a' missing but 's' and 'dt' present, compute finite difference and check. Need include.

Pass-rush pressure semantics: when quick_pressure is NA and blitz is True, pressure = 0; get_off is NA if not rushing. Need check:
- For rows where quick_pressure is NA (missing/None/NaN) and blitz is True, pressure should be 0.
- For rows where not rushing (is_rushing False or 0), get_off should be NA.
Need handle NA. Need define is_na. Use pandas? Input dict maybe can use pandas? We can import pandas as pd? But maybe not. We can use math.isnan, None. Need handle numpy? Could import numpy as np. We'll use numpy/pandas? The function can import numpy and pandas. But if input dict, convert to DataFrame? Could use pandas. Need ensure code valid. We'll import numpy as np, pandas as pd. But maybe environment has. Use pd.isna.

Need Voronoi spatial dominance or closing vector calculation. Need verify. Could check if 'voronoi_area' present: non-negative and sum per frame maybe <= field area? Or if 'closing_vector_x','closing_vector_y' present: magnitude <= max speed * dt? Need "Voronoi spatial dominance or closing vector calculation." We can implement:
- If 'voronoi_area' present: check values >= 0 and <= field area (120*53.3=6396) maybe per player. Also if 'voronoi_dominance' present, check between 0 and 1.
- If 'closing_vector_x' and 'closing_vector_y' present: compute magnitude and check <= max_speed * dt + tol, where max_speed maybe 12? Actually closing vector is displacement over time? Need bound by max human speed maybe 12 m/s? But NFL speeds up to ~10 m/s. Use 12.0 m/s. If dt present, magnitude <= 12.0 * dt + tol. If no dt, magnitude <= 12.0? Hmm.
- Or if 'voronoi_control' present, check in [0,1].
Need maybe compute Voronoi spatial dominance from coordinates? Could verify if 'voronoi_area' sums to field area per frame? But player Voronoi cells partition field, sum of areas per frame should equal field area (within tolerance) if all players included. That's a strong invariant. Could implement if 'frameId' and 'voronoi_area' present: group by frameId, sum areas, check close to 6396. But input dict may not have frameId. Could use 'frame_id'. Need robust.

Need maybe include "closing vector calculation" as check if closing vector components are finite and magnitude bounded. Could also compute closing vector from player position to nearest opponent? But no.

Need produce function that returns bool. Need maybe include all checks and return True if all pass. Need handle empty dict? If empty, maybe True? But likely false? We can return True for no data? Hmm.

Need decide structure.

Let's craft code:

```python
import math
import numpy as np
import pandas as pd

def verify_nfl_bdb_invariants(df_sample: dict) -> bool:
    # Convert dict to DataFrame
    try:
        df = pd.DataFrame(df_sample)
    except Exception:
        return False
    
    if df.empty:
        return True  # vacuous
    
    tol = 1e-6
    field_length = 120.0
    field_width = 53.3
    max_accel = 12.0
    max_speed = 12.0
    
    # 1 coordinate normalization
    if 'x' in df.columns:
        if not np.all(np.isfinite(df['x'])) or ((df['x'] < -tol) | (df['x'] > field_length + tol)).any():
            return False
    if 'y' in df.columns:
        if not np.all(np.isfinite(df['y'])) or ((df['y'] < -tol) | (df['y'] > field_width + tol)).any():
            return False
    # direction angles
    for col in ['dir','o']:
        if col in df.columns:
            vals = df[col]
            if not np.all(np.isfinite(vals)) or ((vals < -tol) | (vals > 360.0 + tol)).any():
                return False
    # optional offensive endzone orientation: if column exists, must be +/-1 or left/right
    if 'offensive_endzone_direction' in df.columns:
        valid = df['offensive_endzone_direction'].isin([1, -1, 1.0, -1.0, 'left','right'])
        if not valid.all():
            return False
    if 'play_direction' in df.columns:
        valid = df['play_direction'].isin(['left','right', 1, -1, 1.0, -1.0])
        if not valid.all():
            return False
    
    # 2 kinematic continuity
    if 's' in df.columns:
        s = df['s']
        if not np.all(np.isfinite(s)) or (s < -tol).any():
            return False
    if 'a' in df.columns:
        a = df['a']
        if not np.all(np.isfinite(a)) or (np.abs(a) > max_accel + tol).any():
            return False
    # if a missing but s and dt present, compute finite difference
    if 'a' not in df.columns and 's' in df.columns and 'dt' in df.columns:
        s = df['s'].to_numpy(dtype=float)
        dt = df['dt'].to_numpy(dtype=float)
        if np.any(dt <= 0):
            return False
        # per row? Need
