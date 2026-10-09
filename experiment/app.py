from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

import pygame

from .config import AppConfig, ConditionConfig, LevelConfig, load_config
from .geometry import build_grid_positions, deg_to_px
from .logger import ExperimentLogger
from .models import InputSample, Target
from .providers import create_input_provider


@dataclass
class TrialOutcome:
    trial_index: int
    active_target_id: str
    time_ms: float
    error_count: int


class ExperimentApp:
    def __init__(self, config_path: Path) -> None:
        self.config_path = Path(config_path)
        self.root_dir = self.config_path.parent
        self.config: AppConfig = load_config(self.config_path)
        pygame.init()
        pygame.font.init()

        flags = pygame.FULLSCREEN if self.config.fullscreen else 0
        self.screen = pygame.display.set_mode((self.config.screen_width_px, self.config.screen_height_px), flags)
        pygame.display.set_caption("Tobii Dwell-Time Lab")
        self.clock = pygame.time.Clock()

        self.title_font = pygame.font.SysFont("Arial", 40, bold=True)
        self.body_font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 18)

        self.provider = create_input_provider(
            self.config.input_mode,
            (self.config.screen_width_px, self.config.screen_height_px),
            self.config.input,
            self.root_dir,
        )
        self.logger = ExperimentLogger(self.root_dir / self.config.log_dir, self.config.participant_id)
        self.running = True
        self.background_color = self.config.background_color

    def run(self) -> None:
        self.provider.start()
        self.logger.log_event(
            participant_id=self.config.participant_id,
            input_source=self.provider.source_name,
            event="session_start",
            note=f"config={self.config_path.name}",
        )

        self._wait_screen(
            [
                "Static-circle dwell-time experiment",
                f"Participant: {self.config.participant_id}",
                f"Input mode: {self.config.input_mode}",
                "Press SPACE to start. Press ESC to quit.",
            ]
        )

        conditions = list(self.config.conditions)
        if self.config.condition_order == "random":
            random.shuffle(conditions)

        for condition in conditions:
            for level in self.config.levels:
                if not self.running:
                    break
                self._run_block(condition, level)
            if not self.running:
                break

        self.logger.log_event(
            participant_id=self.config.participant_id,
            input_source=self.provider.source_name,
            event="session_end",
        )
        self.provider.stop()
        self.logger.close()
        self._wait_screen([
            "Session finished",
            f"Log saved at: {self.logger.path.name}",
            "Press ESC to close.",
        ], wait_for_space=False)
        pygame.quit()

    def _wait_screen(self, lines: Sequence[str], wait_for_space: bool = True) -> None:
        waiting = True
        while waiting and self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    waiting = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                        waiting = False
                    if wait_for_space and event.key == pygame.K_SPACE:
                        waiting = False

            self.screen.fill(self.background_color)
            y = self.config.screen_height_px * 0.28
            for index, line in enumerate(lines):
                font = self.title_font if index == 0 else self.body_font
                surface = font.render(line, True, (245, 245, 245))
                rect = surface.get_rect(center=(self.config.screen_width_px / 2, y))
                self.screen.blit(surface, rect)
                y += 62 if index == 0 else 40
            pygame.display.flip()
            self.clock.tick(self.config.fps)

    def _run_block(self, condition: ConditionConfig, level: LevelConfig) -> None:
        targets = self._build_targets(level)
        trial_order = [target.id for target in targets for _ in range(level.repetitions_per_target)]
        random.shuffle(trial_order)

        self.logger.log_event(
            participant_id=self.config.participant_id,
            input_source=self.provider.source_name,
            condition_id=condition.id,
            condition_label=condition.label,
            dwell_time_ms=condition.dwell_time_ms,
            level_id=level.id,
            level_name=level.name,
            event="block_start",
        )

        self._wait_screen(
            [
                f"Condition: {condition.label}",
                f"Level: {level.name}",
                f"Dwell-time: {condition.dwell_time_ms} ms",
                "Press SPACE to start this block.",
            ]
        )

        outcomes: List[TrialOutcome] = []
        for trial_index, active_target_id in enumerate(trial_order, start=1):
            if not self.running:
                break
            outcome = self._run_trial(condition, level, targets, active_target_id, trial_index, len(trial_order))
            if outcome is not None:
                outcomes.append(outcome)

        if outcomes:
            avg_time = sum(item.time_ms for item in outcomes) / len(outcomes)
            total_errors = sum(item.error_count for item in outcomes)
            self._wait_screen(
                [
                    f"Block finished: {condition.label}",
                    f"Average time per target: {avg_time:.0f} ms",
                    f"Total errors in block: {total_errors}",
                    "Press SPACE to continue.",
                ]
            )

        self.logger.log_event(
            participant_id=self.config.participant_id,
            input_source=self.provider.source_name,
            condition_id=condition.id,
            condition_label=condition.label,
            dwell_time_ms=condition.dwell_time_ms,
            level_id=level.id,
            level_name=level.name,
            event="block_end",
            note=f"trials_completed={len(outcomes)}",
        )

    def _run_trial(
        self,
        condition: ConditionConfig,
        level: LevelConfig,
        targets: Sequence[Target],
        active_target_id: str,
        trial_index: int,
        total_trials: int,
    ) -> Optional[TrialOutcome]:
        active_target = next(target for target in targets if target.id == active_target_id)
        trial_start_ms = time.perf_counter() * 1000.0
        current_hover_id: Optional[str] = None
        hover_start_ms: Optional[float] = None
        attempt_index = 0
        error_count = 0
        flash_until_ms = 0.0
        flash_target_id: Optional[str] = None

        self.logger.log_event(
            participant_id=self.config.participant_id,
            input_source=self.provider.source_name,
            condition_id=condition.id,
            condition_label=condition.label,
            dwell_time_ms=condition.dwell_time_ms,
            level_id=level.id,
            level_name=level.name,
            trial_index=trial_index,
            active_target_id=active_target_id,
            event="trial_start",
        )

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False

            sample = self.provider.update()
            now_ms = time.perf_counter() * 1000.0
            hovered_target = self._hit_test(sample, targets) if sample.valid else None
            hovered_id = hovered_target.id if hovered_target is not None else None

            if hovered_id != current_hover_id:
                if current_hover_id is not None:
                    self.logger.log_event(
                        participant_id=self.config.participant_id,
                        input_source=self.provider.source_name,
                        condition_id=condition.id,
                        condition_label=condition.label,
                        dwell_time_ms=condition.dwell_time_ms,
                        level_id=level.id,
                        level_name=level.name,
                        trial_index=trial_index,
                        active_target_id=active_target_id,
                        selected_target_id=current_hover_id,
                        attempt=attempt_index,
                        event="hover_exit",
                        x_px=round(sample.x_px, 2),
                        y_px=round(sample.y_px, 2),
                        x_norm=round(sample.x_norm, 4),
                        y_norm=round(sample.y_norm, 4),
                        valid=int(sample.valid),
                        head_x=sample.head_x,
                        head_y=sample.head_y,
                        head_z=sample.head_z,
                    )
                current_hover_id = hovered_id
                hover_start_ms = None
                if hovered_id is not None:
                    attempt_index += 1
                    hover_start_ms = now_ms
                    self.logger.log_event(
                        participant_id=self.config.participant_id,
                        input_source=self.provider.source_name,
                        condition_id=condition.id,
                        condition_label=condition.label,
                        dwell_time_ms=condition.dwell_time_ms,
                        level_id=level.id,
                        level_name=level.name,
                        trial_index=trial_index,
                        active_target_id=active_target_id,
                        selected_target_id=hovered_id,
                        attempt=attempt_index,
                        event="attempt_start",
                        x_px=round(sample.x_px, 2),
                        y_px=round(sample.y_px, 2),
                        x_norm=round(sample.x_norm, 4),
                        y_norm=round(sample.y_norm, 4),
                        valid=int(sample.valid),
                        head_x=sample.head_x,
                        head_y=sample.head_y,
                        head_z=sample.head_z,
                    )

            dwell_elapsed_ms = 0.0
            if hovered_id is not None and hover_start_ms is not None:
                dwell_elapsed_ms = now_ms - hover_start_ms
                if dwell_elapsed_ms >= condition.dwell_time_ms:
                    is_hit = hovered_id == active_target_id
                    accidental_selection = int(not is_hit)
                    selection_time_ms = now_ms - trial_start_ms
                    self.logger.log_event(
                        participant_id=self.config.participant_id,
                        input_source=self.provider.source_name,
                        condition_id=condition.id,
                        condition_label=condition.label,
                        dwell_time_ms=condition.dwell_time_ms,
                        level_id=level.id,
                        level_name=level.name,
                        trial_index=trial_index,
                        active_target_id=active_target_id,
                        selected_target_id=hovered_id,
                        attempt=attempt_index,
                        event="selection",
                        hit=int(is_hit),
                        error=int(not is_hit),
                        error_count=error_count + int(not is_hit),
                        accidental_selection=accidental_selection,
                        time_per_target_ms=round(selection_time_ms, 2),
                        x_px=round(sample.x_px, 2),
                        y_px=round(sample.y_px, 2),
                        x_norm=round(sample.x_norm, 4),
                        y_norm=round(sample.y_norm, 4),
                        valid=int(sample.valid),
                        head_x=sample.head_x,
                        head_y=sample.head_y,
                        head_z=sample.head_z,
                    )
                    if is_hit:
                        self.logger.log_event(
                            participant_id=self.config.participant_id,
                            input_source=self.provider.source_name,
                            condition_id=condition.id,
                            condition_label=condition.label,
                            dwell_time_ms=condition.dwell_time_ms,
                            level_id=level.id,
                            level_name=level.name,
                            trial_index=trial_index,
                            active_target_id=active_target_id,
                            selected_target_id=hovered_id,
                            attempt=attempt_index,
                            event="trial_end",
                            hit=1,
                            error=0,
                            error_count=error_count,
                            accidental_selection=0,
                            time_per_target_ms=round(selection_time_ms, 2),
                        )
                        return TrialOutcome(
                            trial_index=trial_index,
                            active_target_id=active_target_id,
                            time_ms=selection_time_ms,
                            error_count=error_count,
                        )
                    error_count += 1
                    flash_until_ms = now_ms + 450.0
                    flash_target_id = hovered_id
                    current_hover_id = None
                    hover_start_ms = None

            self._draw_trial(
                condition=condition,
                level=level,
                targets=targets,
                active_target_id=active_target_id,
                hovered_id=hovered_id,
                dwell_elapsed_ms=dwell_elapsed_ms,
                trial_index=trial_index,
                total_trials=total_trials,
                sample=sample,
                flash_until_ms=flash_until_ms,
                flash_target_id=flash_target_id,
                now_ms=now_ms,
                error_count=error_count,
            )
            self.clock.tick(self.config.fps)

        return None

    def _draw_trial(
        self,
        condition: ConditionConfig,
        level: LevelConfig,
        targets: Sequence[Target],
        active_target_id: str,
        hovered_id: Optional[str],
        dwell_elapsed_ms: float,
        trial_index: int,
        total_trials: int,
        sample: InputSample,
        flash_until_ms: float,
        flash_target_id: Optional[str],
        now_ms: float,
        error_count: int,
    ) -> None:
        self.screen.fill(self.background_color)
        self._draw_header(condition, level, trial_index, total_trials, error_count)

        for target in targets:
            is_active = target.id == active_target_id
            is_hovered = target.id == hovered_id
            is_flash = flash_target_id == target.id and now_ms < flash_until_ms

            fill_color = target.color
            if is_flash:
                fill_color = (240, 80, 80)
            pygame.draw.circle(self.screen, fill_color, target.center_px, target.radius_px)

            ring_width = 5 if is_active else 2
            ring_color = level.highlight_color if is_active else (70, 80, 95)
            pygame.draw.circle(self.screen, ring_color, target.center_px, target.radius_px + 4, ring_width)

            if is_hovered:
                ratio = min(1.0, dwell_elapsed_ms / condition.dwell_time_ms)
                progress_radius = target.radius_px + 12
                end_angle = -1.5708 + ratio * 6.2831
                pygame.draw.arc(
                    self.screen,
                    (255, 255, 255),
                    pygame.Rect(
                        target.center_px[0] - progress_radius,
                        target.center_px[1] - progress_radius,
                        progress_radius * 2,
                        progress_radius * 2,
                    ),
                    -1.5708,
                    end_angle,
                    5,
                )

            label_surface = self.body_font.render(target.label, True, (18, 18, 22))
            label_rect = label_surface.get_rect(center=target.center_px)
            self.screen.blit(label_surface, label_rect)

        if sample.valid:
            pygame.draw.circle(self.screen, (250, 250, 250), (int(sample.x_px), int(sample.y_px)), 6)
            pygame.draw.circle(self.screen, (20, 20, 20), (int(sample.x_px), int(sample.y_px)), 6, 1)

        pygame.display.flip()

    def _draw_header(self, condition: ConditionConfig, level: LevelConfig, trial_index: int, total_trials: int, error_count: int) -> None:
        lines = [
            f"Participant: {self.config.participant_id}",
            f"Condition: {condition.label} | Dwell: {condition.dwell_time_ms} ms",
            f"Level: {level.name} | Trial {trial_index}/{total_trials} | Errors this trial: {error_count}",
            f"Input: {self.config.input_mode} | ESC = quit",
        ]
        y = 18
        for line in lines:
            surface = self.small_font.render(line, True, (245, 245, 245))
            self.screen.blit(surface, (20, y))
            y += 22

    def _hit_test(self, sample: InputSample, targets: Sequence[Target]) -> Optional[Target]:
        for target in targets:
            dx = sample.x_px - target.center_px[0]
            dy = sample.y_px - target.center_px[1]
            if (dx * dx + dy * dy) <= (target.radius_px * target.radius_px):
                return target
        return None

    def _build_targets(self, level: LevelConfig) -> List[Target]:
        radius_px = round(
            deg_to_px(
                level.target_radius_deg,
                self.config.viewing_distance_cm,
                self.config.screen_width_px,
                self.config.screen_width_cm,
            )
        )
        spacing_x_px = deg_to_px(
            level.spacing_x_deg,
            self.config.viewing_distance_cm,
            self.config.screen_width_px,
            self.config.screen_width_cm,
        )
        spacing_y_px = deg_to_px(
            level.spacing_y_deg,
            self.config.viewing_distance_cm,
            self.config.screen_height_px,
            self.config.screen_height_cm,
        )
        positions = build_grid_positions(
            self.config.screen_width_px,
            self.config.screen_height_px,
            level.rows,
            level.cols,
            spacing_x_px,
            spacing_y_px,
        )

        target_count = level.rows * level.cols
        labels = list(level.labels)
        if len(labels) < target_count:
            for code in range(ord('A') + len(labels), ord('A') + target_count):
                labels.append(chr(code))

        colors = list(level.colors)
        if len(colors) < target_count and colors:
            while len(colors) < target_count:
                colors.extend(colors)
        colors = colors[:target_count]

        targets = []
        for index, position in enumerate(positions[:target_count]):
            targets.append(
                Target(
                    id=f"T{index + 1}",
                    label=labels[index],
                    color=colors[index],
                    center_px=position,
                    radius_px=radius_px,
                )
            )
        return targets
