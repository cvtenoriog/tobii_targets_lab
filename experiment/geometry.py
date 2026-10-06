from math import radians, tan
from typing import List, Tuple



def deg_to_cm(angle_deg: float, viewing_distance_cm: float) -> float:
    return 2.0 * viewing_distance_cm * tan(radians(angle_deg) / 2.0)



def cm_to_px(size_cm: float, screen_px: int, screen_cm: float) -> float:
    return size_cm * (screen_px / screen_cm)



def deg_to_px(angle_deg: float, viewing_distance_cm: float, screen_px: int, screen_cm: float) -> float:
    return cm_to_px(deg_to_cm(angle_deg, viewing_distance_cm), screen_px, screen_cm)



def build_grid_positions(
    screen_width_px: int,
    screen_height_px: int,
    rows: int,
    cols: int,
    spacing_x_px: float,
    spacing_y_px: float,
) -> List[Tuple[int, int]]:
    center_x = screen_width_px / 2.0
    center_y = screen_height_px / 2.0
    total_width = (cols - 1) * spacing_x_px
    total_height = (rows - 1) * spacing_y_px
    start_x = center_x - total_width / 2.0
    start_y = center_y - total_height / 2.0

    positions = []
    for row in range(rows):
        for col in range(cols):
            positions.append((round(start_x + col * spacing_x_px), round(start_y + row * spacing_y_px)))
    return positions
