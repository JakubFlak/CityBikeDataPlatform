"""Restore the latest successful GitHub Actions pipeline state."""

import logging
from pathlib import Path

from bike_data.pipeline_state import restore_latest_successful_state


def main() -> int:
    try:
        result = restore_latest_successful_state(Path.cwd())
    except Exception:
        logging.getLogger(__name__).exception("pipeline_state_restore_failed")
        return 1

    if result.run_id is None:
        print("No successful pipeline state found; starting with empty data/")
    else:
        print(
            f"Restored {result.artifact_name} from successful pipeline run "
            f"{result.run_id}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
