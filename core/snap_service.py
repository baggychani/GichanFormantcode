"""Framework-neutral nearest-point snapping."""

import numpy as np

try:
    from scipy.spatial import cKDTree

    _HAS_KD = True
except ImportError:
    cKDTree = None
    _HAS_KD = False


def snap_query(ax, snapping_data, x_px, y_px, max_dist_px=20):
    if not ax or not snapping_data:
        return None
    points = np.array([[point["x"], point["y"]] for point in snapping_data])
    pixel_points = ax.transData.transform(points)
    query_point = np.array([x_px, y_px])
    if _HAS_KD and len(pixel_points) > 0:
        distance, index = cKDTree(pixel_points).query(query_point, k=1)
        distance = float(distance)
        index = int(index)
    else:
        distances = np.linalg.norm(pixel_points - query_point, axis=1)
        index = int(np.argmin(distances))
        distance = float(distances[index])
    if distance <= max_dist_px:
        return snapping_data[index]
    return None
