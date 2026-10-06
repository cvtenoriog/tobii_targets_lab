from pathlib import Path
import argparse

from experiment.app import ExperimentApp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Static-circle dwell-time experiment with Mouse/Tobii input")
    parser.add_argument("--config", default="config.json", help="Path to config JSON")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = ExperimentApp(Path(args.config))
    app.run()


if __name__ == "__main__":
    main()
