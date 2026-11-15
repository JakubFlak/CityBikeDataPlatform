"""Restore the latest successful GitHub Actions pipeline state."""

import shutil
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

PIPELINE_WORKFLOW = "data-pipeline.yml"
PIPELINE_ARTIFACT = "pipeline-state"
LEGACY_ARTIFACT_PREFIX = "pipeline-output-"
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class RestoreResult:
    """Describe whether a prior successful state was restored."""

    run_id: str | None
    artifact_name: str | None


def restore_latest_successful_state(
    workspace: Path,
    *,
    runner: CommandRunner = subprocess.run,
) -> RestoreResult:
    """Restore a prior successful state, or leave a first run empty.

    The GitHub CLI uses the workflow's read permission and the inherited
    ``GH_TOKEN`` to find and download artifacts. A legacy artifact name is
    supported so the first fixed workflow run can continue from an older
    successful run.
    """
    result = runner(
        [
            "gh",
            "run",
            "list",
            "--workflow",
            PIPELINE_WORKFLOW,
            "--status",
            "success",
            "--limit",
            "1",
            "--json",
            "databaseId",
            "--jq",
            ".[0].databaseId",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    run_id = result.stdout.strip()
    if not run_id:
        return RestoreResult(run_id=None, artifact_name=None)

    workspace.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".pipeline-restore-", dir=workspace
    ) as directory:
        download_root = Path(directory)
        artifact_name = _download_state(
            run_id, download_root, runner, PIPELINE_ARTIFACT
        )
        if artifact_name is None:
            artifact_name = _download_state(
                run_id,
                download_root,
                runner,
                f"{LEGACY_ARTIFACT_PREFIX}{run_id}",
            )
        if artifact_name is None:
            raise RuntimeError(
                f"successful pipeline run {run_id} has no downloadable state artifact"
            )

        source = _find_state_root(download_root)
        destination = workspace / "data"
        staged = Path(tempfile.mkdtemp(prefix=".pipeline-state-", dir=workspace))
        try:
            shutil.copytree(source, staged / "data")
            if destination.exists():
                shutil.rmtree(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            staged_data = staged / "data"
            staged_data.replace(destination)
        finally:
            shutil.rmtree(staged, ignore_errors=True)

    return RestoreResult(run_id=run_id, artifact_name=artifact_name)


def _download_state(
    run_id: str,
    directory: Path,
    runner: CommandRunner,
    artifact_name: str,
) -> str | None:
    command: Sequence[str] = [
        "gh",
        "run",
        "download",
        run_id,
        "--name",
        artifact_name,
        "--dir",
        str(directory),
    ]
    try:
        runner(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        return None
    return artifact_name


def _find_state_root(download_root: Path) -> Path:
    candidates = [download_root / "data", download_root]
    candidates.extend(download_root.glob("*/data"))
    candidates.extend(
        state_path.parent.parent
        for state_path in download_root.glob("**/silver/_incremental_state.json")
    )
    for candidate in candidates:
        if (candidate / "silver" / "_incremental_state.json").exists():
            return candidate
    raise RuntimeError(
        "downloaded pipeline artifact does not contain data/silver/"
        "_incremental_state.json"
    )
