# targetsRandom — Python scaffold for week 9 lab

This scaffold is a **from-scratch Python version** of the static-target dwell-time experiment for your week 9 lab.
It is designed so the **same experiment logic** works with:

- **mouse** in the virtual lab
- **Tobii** in the in-person lab

The app shows **static circles on screen**, highlights one active target at a time, and selects by **dwell-time**.
It also creates a **.log file** with the variables needed for later analysis.

---

## What this version already solves

1. **Screen resolution is configurable** from `config.json`
2. **Target size and spacing can be defined in visual angle degrees** and converted to pixels internally
3. **Input mode is configurable**: `mouse` or `tobii`
4. **Dwell-time conditions are configurable** from `config.json`
5. **Logging is ready** for participant, condition, level, timestamps, attempts, errors, accidental selections, and time per target

---

## Suggested folder structure

```text
.
├── config.json
├── main.py
├── requirements.txt
├── README.md
├── logs/
├── .vscode/
│   ├── settings.json
│   └── launch.json
└── experiment/
    ├── __init__.py
    ├── app.py
    ├── config.py
    ├── geometry.py
    ├── logger.py
    ├── models.py
    └── providers.py
```

---

## Quick start (mouse mode)

### 1. Create a virtual environment in macOS with Python 3.9.4

```bash
python3.9 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Run the app

```bash
python main.py --config config.json
```

By default, `config.json` starts in:

```json
"input_mode": "mouse"
```

So you can test the full experiment even before connecting Tobii.

---

## How the experiment works

- Static circles appear on the screen.
- One circle is the **active target**.
- The user selects by **remaining over the target for the configured dwell-time**.
- If the dwell threshold is reached on the wrong circle, it is logged as an **accidental selection**.
- The target stays active until the correct circle is selected.

This makes the experiment useful for comparing different dwell-times.

---

## Config file

Example:

```json
{
  "participant_id": "P01",
  "screen_width_px": 1440,
  "screen_height_px": 900,
  "screen_width_cm": 33.0,
  "screen_height_cm": 20.7,
  "viewing_distance_cm": 60.0,
  "input_mode": "mouse",
  "conditions": [
    {"id": "dwell_250", "label": "250 ms", "dwell_time_ms": 250},
    {"id": "dwell_500", "label": "500 ms", "dwell_time_ms": 500},
    {"id": "dwell_900", "label": "900 ms", "dwell_time_ms": 900}
  ]
}
```

### Important configurable fields

- `screen_width_px`, `screen_height_px` → screen resolution
- `screen_width_cm`, `screen_height_cm` → real physical screen size
- `viewing_distance_cm` → viewing distance
- `input_mode` → `mouse` or `tobii`
- `conditions[].dwell_time_ms` → dwell-time per condition
- `levels[].target_radius_deg` → target radius in visual angle
- `levels[].spacing_x_deg`, `levels[].spacing_y_deg` → target spacing in visual angle

---

## Why use visual angle instead of pixels?

The app converts **visual angle degrees → pixels** internally.

This makes the task more comparable across laptops and monitors.

The conversion used is:

```text
size_cm = 2 * viewing_distance_cm * tan(angle_deg / 2)
pixels = size_cm * (screen_px / screen_cm)
```

This is especially useful when you want target size to remain experimentally meaningful, not just visually approximate.

---

## Logging

The app writes a `.log` file (CSV-style) inside `logs/`.

### Main fields already included

- `participant_id`
- `condition_id`
- `condition_label`
- `level_id`
- `timestamp_iso`
- `trial_index`
- `attempt`
- `hit`
- `error`
- `error_count`
- `accidental_selection`
- `time_per_target_ms`
- `x_px`, `y_px`
- `x_norm`, `y_norm`
- `head_x`, `head_y`, `head_z`
- `event`

### About the optional fields you mentioned

#### `attempt`
This scaffold **does log attempts**.

Definition used here:

> An attempt starts each time the user enters a selectable target and begins a new dwell sequence.

That means if the user enters one target, exits, and re-enters the same or another target, that can generate a new attempt.

#### `accidental_selection`
This scaffold **does log accidental selections**.

Definition used here:

> An accidental selection happens when the dwell threshold is completed on a non-active target.

This is especially useful when comparing short dwell-times.

---

## Tobii mode

To switch to Tobii mode, set:

```json
"input_mode": "tobii"
```

This scaffold includes a ready Python provider for the `tobii_research` binding:

- file: `experiment/providers.py`
- class: `TobiiInputProvider`

### Important note

This does **not** depend on Tobii Pro Lab.
It depends on having a Python-accessible Tobii SDK binding available in your Mac environment.

If your local setup exposes Tobii through `tobii_research`, this code is ready to use.
If your local setup uses a different wrapper, the only file you should adapt is:

- `experiment/providers.py`

The rest of the experiment logic can remain unchanged.

### Head data in this scaffold

In Tobii mode, `head_x`, `head_y`, `head_z` are computed as an **approximate head-position proxy** using the average gaze origin in user coordinates when available from the SDK.

So the experiment is already prepared to store head-related information if the SDK returns it.

---

## VS Code setup on macOS (Python 3.9.4)

### 1. Recommended extensions

Install:

- **Python** (Microsoft)
- **Pylance** (Microsoft)

### 2. Open the project folder in VS Code

Then create the environment:

```bash
python3.9 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Select interpreter

In VS Code:

- `Cmd + Shift + P`
- **Python: Select Interpreter**
- choose `.venv/bin/python`

### 4. Run configuration

This scaffold already includes:

- `.vscode/settings.json`
- `.vscode/launch.json`

So you can run directly from VS Code once the interpreter is selected.

---

## Suggested workflow for your course

### Virtual lab

Use:

```json
"input_mode": "mouse"
```

Goal:

- validate UI logic
- validate dwell logic
- validate logs
- validate conditions

### In-person lab

Use:

```json
"input_mode": "tobii"
```

Goal:

- collect real gaze data
- collect head proxy data
- compare dwell-time conditions
- export logs for analysis

---

## Next improvements you may want later

- block randomization by participant
- more than one level
- score screen
- heatmap post-processing script
- calibration quality checks before starting a block
- separate raw-stream log and trial-summary log

---

## Practical note for this repository

If you want to merge this into the existing public repo, the safest path is:

1. keep this Python scaffold as a separate branch or folder,
2. test in mouse mode first,
3. verify the local Tobii Python binding on your Mac,
4. then adapt only `experiment/providers.py` if needed.

That way, the experimental logic and the Tobii connection layer stay cleanly separated.
