from __future__ import annotations

import os
import socket
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path
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


class TobiiSdkBridgeInputProvider(BaseInputProvider):
    source_name = "tobii"

    def __init__(
        self,
        screen_size: Tuple[int, int],
        settings: Optional[Dict[str, Any]] = None,
        project_root: Optional[Path] = None,
    ) -> None:
        self.screen_width_px, self.screen_height_px = screen_size
        self.settings = settings or {}
        self.project_root = Path(project_root or Path.cwd())

        self.udp_ip = self.settings.get("udp_ip", "127.0.0.1")
        self.udp_port = int(self.settings.get("udp_port", 5005))
        self.launch_bridge = bool(self.settings.get("launch_bridge", False))
        self.bridge_executable = self._resolve_path(self.settings.get("bridge_executable"))
        self.bridge_cwd = self._resolve_path(self.settings.get("bridge_cwd")) if self.settings.get("bridge_cwd") else None
        self.source_screen_width_px = float(self.settings.get("source_screen_width_px", self.screen_width_px))
        self.source_screen_height_px = float(self.settings.get("source_screen_height_px", self.screen_height_px))
        self.treat_zero_zero_as_invalid = bool(self.settings.get("treat_zero_zero_as_invalid", True))
        self.sample_stale_after_ms = float(self.settings.get("sample_stale_after_ms", 250))
        self.startup_wait_ms = float(self.settings.get("startup_wait_ms", 1000))

        self.sock: Optional[socket.socket] = None
        self.bridge_process: Optional[subprocess.Popen] = None
        self.latest_sample = InputSample(
            x_px=self.screen_width_px / 2,
            y_px=self.screen_height_px / 2,
            x_norm=0.5,
            y_norm=0.5,
            valid=False,
            timestamp_ms=time.perf_counter() * 1000.0,
            source=self.source_name,
        )
        self.last_packet_monotonic_ms = 0.0

    def _resolve_path(self, value: Optional[str]) -> Optional[Path]:
        if not value:
            return None
        path = Path(value)
        if not path.is_absolute():
            path = self.project_root / path
        return path

    def start(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind((self.udp_ip, self.udp_port))
        except OSError as exc:
            raise RuntimeError(
                f"No se pudo abrir el puerto UDP {self.udp_ip}:{self.udp_port}. "
                "Verifica que no haya otro proceso usando el mismo puerto."
            ) from exc
        self.sock.setblocking(False)

        if self.launch_bridge:
            if self.bridge_executable is None:
                raise RuntimeError("Falta configurar 'bridge_executable' para el modo tobii.")
            if not self.bridge_executable.exists():
                raise RuntimeError(f"No existe el ejecutable del bridge: {self.bridge_executable}")
            if os.name != 'nt' and self.bridge_executable.suffix.lower() == '.exe':
                raise RuntimeError(
                    "El bridge incluido es un ejecutable de Windows (.exe). "
                    "Puedes usarlo directamente en Windows, o en macOS dejar launch_bridge=false "
                    "y conectarte a un bridge externo compatible que envíe UDP."
                )

            cwd = self.bridge_cwd or self.bridge_executable.parent
            creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
            self.bridge_process = subprocess.Popen(
                [str(self.bridge_executable)],
                cwd=str(cwd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            time.sleep(self.startup_wait_ms / 1000.0)

    def _consume_udp_messages(self) -> None:
        if self.sock is None:
            return

        while True:
            try:
                payload, _ = self.sock.recvfrom(1024)
            except BlockingIOError:
                break

            decoded = payload.decode('utf-8', errors='ignore').strip()
            if not decoded:
                continue
            parts = decoded.split(',')
            if len(parts) != 3:
                continue
            try:
                timestamp_us = int(parts[0])
                raw_x = float(parts[1])
                raw_y = float(parts[2])
            except ValueError:
                continue

            x_norm = raw_x / self.source_screen_width_px if self.source_screen_width_px else 0.0
            y_norm = raw_y / self.source_screen_height_px if self.source_screen_height_px else 0.0
            x_px = max(0.0, min(float(self.screen_width_px), x_norm * self.screen_width_px))
            y_px = max(0.0, min(float(self.screen_height_px), y_norm * self.screen_height_px))

            valid = True
            if self.treat_zero_zero_as_invalid and raw_x == 0 and raw_y == 0:
                valid = False

            self.latest_sample = InputSample(
                x_px=x_px,
                y_px=y_px,
                x_norm=x_norm,
                y_norm=y_norm,
                valid=valid,
                timestamp_ms=timestamp_us / 1000.0,
                source=self.source_name,
                user_present=valid,
            )
            self.last_packet_monotonic_ms = time.perf_counter() * 1000.0

    def update(self) -> InputSample:
        self._consume_udp_messages()
        now_ms = time.perf_counter() * 1000.0
        if self.last_packet_monotonic_ms and (now_ms - self.last_packet_monotonic_ms) > self.sample_stale_after_ms:
            return InputSample(
                x_px=self.latest_sample.x_px,
                y_px=self.latest_sample.y_px,
                x_norm=self.latest_sample.x_norm,
                y_norm=self.latest_sample.y_norm,
                valid=False,
                timestamp_ms=self.latest_sample.timestamp_ms,
                source=self.latest_sample.source,
                head_x=self.latest_sample.head_x,
                head_y=self.latest_sample.head_y,
                head_z=self.latest_sample.head_z,
                user_present=False,
            )
        return self.latest_sample

    def stop(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

        if self.bridge_process is not None:
            try:
                self.bridge_process.terminate()
                self.bridge_process.wait(timeout=2)
            except Exception:
                try:
                    self.bridge_process.kill()
                except Exception:
                    pass
            self.bridge_process = None



def create_input_provider(
    input_mode: str,
    screen_size: Tuple[int, int],
    input_settings: Dict[str, Any],
    project_root: Optional[Path] = None,
) -> BaseInputProvider:
    if input_mode == "mouse":
        return MouseInputProvider(screen_size, input_settings.get("mouse", {}))
    if input_mode == "tobii":
        return TobiiSdkBridgeInputProvider(screen_size, input_settings.get("tobii", {}), project_root)
    raise ValueError(f"Unsupported input_mode: {input_mode}")
