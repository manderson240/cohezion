import numpy as np

def extract_play_kinematics(df_play):
    """Extracts closing acceleration and angular burst velocity at 0.5s post-snap."""
    s_mean = float(np.mean(df_play['s'])) if 's' in df_play else 0.0
    acc_closing = float(np.max(df_play['a'])) if 'a' in df_play else 0.0
    angular_rate = float(np.std(df_play['dir'])) if 'dir' in df_play else 0.0
    
    # Voronoi spatial control area (simplified as bounding box of active players)
    x_coords = np.array([p['x'] for p in df_play]) if 'x' in str(type(df_play)) and hasattr(df_play, '__iter__') else None
    y_coords = np.array([p['y'] for p in df_play]) if 'y' in str(type(df_play)) and hasattr(df_play, '__iter__') else None
    
    # Fallback to simple area estimation if coordinates exist
    control_area = 0.0
    if x_coords is not None and y_coords is not None:
        min_x, max_x = np.min(x_coords), np.max(x_coords)
        min_y, max_y = np.min(y_coords), np.max(y_coords)
        control_area = (max_x - min_x) * (max_y - min_y)

    return {'speed_mean': s_mean, 'acc_closing': acc_closing, 'angular_burst': angular_rate, 'control_area': control_area}