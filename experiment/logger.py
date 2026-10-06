from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class ExperimentLogger:
    FIELDNAMES = [
        "timestamp_iso",
        "participant_id",
        "input_source",
        "condition_id",
        "condition_label",
        "dwell_time_ms",
        "level_id",
        "level_name",
        "trial_index",
        "active_target_id",
        "selected_target_id",
        "attempt",
        "event",
        "hit",
        "error",
        "error_count",
        "accidental_selection",
        "time_per_target_ms",
        "x_px",
        "y_px",
        "x_norm",
        "y_norm",
        "valid",
        "head_x",
        "head_y",
        "head_z",
        "note",
    ]

    def __init__(self, log_dir: Path, participant_id: str) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = log_dir / f"{participant_id}_{timestamp}.log"
        self.file = self.path.open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=self.FIELDNAMES)
        self.writer.writeheader()
        self.file.flush()

    def log_event(self, **kwargs: Any) -> None:
        row: Dict[str, Any] = {field: "" for field in self.FIELDNAMES}
        row["timestamp_iso"] = datetime.now().isoformat(timespec="milliseconds")
        row.update(kwargs)
        self.writer.writerow(row)
        self.file.flush()

    def close(self) -> None:
        self.file.close()
