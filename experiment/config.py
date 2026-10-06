from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

Color = Tuple[int, int, int]


@dataclass
class ConditionConfig:
    id: str
    label: str
    dwell_time_ms: int


@dataclass
class LevelConfig:
    id: str
    name: str
    rows: int
    cols: int
    repetitions_per_target: int
    target_radius_deg: float
    spacing_x_deg: float
    spacing_y_deg: float
    labels: List[str]
    colors: List[Color]
    highlight_color: Color


@dataclass
class AppConfig:
    participant_id: str
    fullscreen: bool
    screen_width_px: int
    screen_height_px: int
    screen_width_cm: float
    screen_height_cm: float
    viewing_distance_cm: float
    background_color: Color
    show_grid: bool
    fps: int
    input_mode: str
    log_dir: str
    condition_order: str
    conditions: List[ConditionConfig]
    levels: List[LevelConfig]
    input: Dict[str, Any]



def _as_color(values: List[int]) -> Color:
    return int(values[0]), int(values[1]), int(values[2])



def load_config(path: Path) -> AppConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))

    conditions = [
        ConditionConfig(
            id=item["id"],
            label=item.get("label", item["id"]),
            dwell_time_ms=int(item["dwell_time_ms"]),
        )
        for item in raw["conditions"]
    ]

    levels = [
        LevelConfig(
            id=item["id"],
            name=item.get("name", item["id"]),
            rows=int(item["rows"]),
            cols=int(item["cols"]),
            repetitions_per_target=int(item["repetitions_per_target"]),
            target_radius_deg=float(item["target_radius_deg"]),
            spacing_x_deg=float(item["spacing_x_deg"]),
            spacing_y_deg=float(item["spacing_y_deg"]),
            labels=list(item["labels"]),
            colors=[_as_color(color) for color in item["colors"]],
            highlight_color=_as_color(item.get("highlight_color", [255, 255, 255])),
        )
        for item in raw["levels"]
    ]

    return AppConfig(
        participant_id=raw.get("participant_id", "P01"),
        fullscreen=bool(raw.get("fullscreen", False)),
        screen_width_px=int(raw.get("screen_width_px", 1440)),
        screen_height_px=int(raw.get("screen_height_px", 900)),
        screen_width_cm=float(raw.get("screen_width_cm", 33.0)),
        screen_height_cm=float(raw.get("screen_height_cm", 20.7)),
        viewing_distance_cm=float(raw.get("viewing_distance_cm", 60.0)),
        background_color=_as_color(raw.get("background_color", [22, 26, 35])),
        show_grid=bool(raw.get("show_grid", False)),
        fps=int(raw.get("fps", 60)),
        input_mode=raw.get("input_mode", "mouse").lower(),
        log_dir=raw.get("log_dir", "logs"),
        condition_order=raw.get("condition_order", "fixed"),
        conditions=conditions,
        levels=levels,
        input=raw.get("input", {}),
    )
