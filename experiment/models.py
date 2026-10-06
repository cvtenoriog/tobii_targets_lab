from dataclasses import dataclass
from typing import Optional, Tuple

Color = Tuple[int, int, int]


@dataclass
class InputSample:
    x_px: float
    y_px: float
    x_norm: float
    y_norm: float
    valid: bool
    timestamp_ms: float
    source: str
    head_x: Optional[float] = None
    head_y: Optional[float] = None
    head_z: Optional[float] = None
    user_present: Optional[bool] = None


@dataclass
class Target:
    id: str
    label: str
    color: Color
    center_px: Tuple[int, int]
    radius_px: int
