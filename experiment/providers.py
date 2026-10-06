from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

import pygame

from .models import InputSample


class BaseInputProvider(ABC):
    source_name = "base"

    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self) -> InputSample:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError


class MouseInputProvider(BaseInputProvider):
    source_name = "mouse"

    def __init__(self, screen_size: Tuple[int, int], settings: Optional[Dict[str, Any]] = None) -> None:
        self.screen_width_px, self.screen_height_px = screen_size
        self.settings = settings or {}

    def start(self) -> None:
        pygame.mouse.set_visible(not self.settings.get("hide_cursor", False))

    def update(self) -> InputSample:
        x_px, y_px = pygame.mouse.get_pos()
        x_norm = x_px / self.screen_width_px
        y_norm = y_px / self.screen_height_px
        return InputSample(
            x_px=float(x_px),
            y_px=float(y_px),
            x_norm=x_norm,
            y_norm=y_norm,
            valid=True,
            timestamp_ms=time.perf_counter() * 1000.0,
            source=self.source_name,
        )

    def stop(self) -> None:
        pygame.mouse.set_visible(True)


class TobiiInputProvider(BaseInputProvider):
    source_name = "tobii"

    def __init__(self, screen_size: Tuple[int, int], settings: Optional[Dict[str, Any]] = None) -> None:
        self.screen_width_px, self.screen_height_px = screen_size
        self.settings = settings or {}
        self.latest_sample = InputSample(
            x_px=self.screen_width_px / 2,
            y_px=self.screen_height_px / 2,
            x_norm=0.5,
            y_norm=0.5,
            valid=False,
            timestamp_ms=time.perf_counter() * 1000.0,
            source=self.source_name,
        )
        self.eye_tracker = None
        self.backend = self.settings.get("backend", "tobii_research")
        self.tr = None

    def start(self) -> None:
        if self.backend != "tobii_research":
            raise RuntimeError(
                f"Unsupported Tobii backend '{self.backend}'. "
                "This scaffold includes a ready provider for 'tobii_research'."
            )

        try:
            import tobii_research as tobii_research
        except ImportError as exc:
            raise RuntimeError(
                "Could not import 'tobii_research'. Install the Python SDK binding or "
                "keep input_mode='mouse' until the Tobii SDK is available on this Mac."
            ) from exc

        self.tr = tobii_research
        trackers = tobii_research.find_all_eyetrackers()
        if not trackers:
            raise RuntimeError("No Tobii tracker found by tobii_research.find_all_eyetrackers().")

        index = int(self.settings.get("screen_index", 0))
        if index >= len(trackers):
            raise RuntimeError(f"Requested Tobii tracker index {index}, but only {len(trackers)} tracker(s) were found.")

        self.eye_tracker = trackers[index]
        self.eye_tracker.subscribe_to(
            tobii_research.EYETRACKER_GAZE_DATA,
            self._gaze_callback,
            as_dictionary=True,
        )

    def _gaze_callback(self, gaze_data: Dict[str, Any]) -> None:
        points = []
        for side in ("left", "right"):
            if gaze_data.get(f"{side}_gaze_point_validity", 0):
                point = gaze_data.get(f"{side}_gaze_point_on_display_area")
                if point is not None:
                    points.append(point)

        valid = len(points) > 0
        if valid:
            x_norm = sum(point[0] for point in points) / len(points)
            y_norm = sum(point[1] for point in points) / len(points)
        else:
            x_norm = self.latest_sample.x_norm
            y_norm = self.latest_sample.y_norm

        origins = []
        for side in ("left", "right"):
            if gaze_data.get(f"{side}_gaze_origin_validity", 0):
                origin = gaze_data.get(f"{side}_gaze_origin_in_user_coordinate_system")
                if origin is not None:
                    origins.append(origin)

        head_x = head_y = head_z = None
        if origins:
            head_x = sum(origin[0] for origin in origins) / len(origins)
            head_y = sum(origin[1] for origin in origins) / len(origins)
            head_z = sum(origin[2] for origin in origins) / len(origins)

        timestamp_us = gaze_data.get("device_time_stamp") or gaze_data.get("system_time_stamp") or int(time.time() * 1_000_000)
        timestamp_ms = timestamp_us / 1000.0
        x_px = x_norm * self.screen_width_px
        y_px = y_norm * self.screen_height_px

        self.latest_sample = InputSample(
            x_px=float(x_px),
            y_px=float(y_px),
            x_norm=float(x_norm),
            y_norm=float(y_norm),
            valid=valid,
            timestamp_ms=float(timestamp_ms),
            source=self.source_name,
            head_x=head_x,
            head_y=head_y,
            head_z=head_z,
            user_present=valid,
        )

    def update(self) -> InputSample:
        return self.latest_sample

    def stop(self) -> None:
        if self.eye_tracker is not None and self.tr is not None:
            try:
                self.eye_tracker.unsubscribe_from(self.tr.EYETRACKER_GAZE_DATA, self._gaze_callback)
            except Exception:
                pass



def create_input_provider(input_mode: str, screen_size: Tuple[int, int], input_settings: Dict[str, Any]) -> BaseInputProvider:
    if input_mode == "mouse":
        return MouseInputProvider(screen_size, input_settings.get("mouse", {}))
    if input_mode == "tobii":
        return TobiiInputProvider(screen_size, input_settings.get("tobii", {}))
    raise ValueError(f"Unsupported input_mode: {input_mode}")
