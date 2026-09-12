import shutil
from pathlib import Path

from test_gold import _populate_raw

from bike_data.config import Settings
from bike_data.pipeline import run_pipeline
from bike_data.pipeline_state import restore_latest_successful_state


def _successful_artifact(source_root: Path, artifact_root: Path) -> None:
    data_root = artifact_root / "data"
    shutil.copytree(source_root, data_root)


def test_first_run_without_previous_state_is_empty(tmp_path):
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        from subprocess import CompletedProcess

        return CompletedProcess(command, 0, stdout="", stderr="")

    result = restore_latest_successful_state(tmp_path, runner=runner)

    assert result.run_id is None
    assert not (tmp_path / "data").exists()
    assert len(calls) == 1


def test_restores_latest_successful_state(tmp_path):
    artifact_root = tmp_path / "artifact"
    source_root = tmp_path / "source"
    _populate_raw(source_root)
    (source_root / "silver").mkdir()
    (source_root / "silver" / "_incremental_state.json").write_text(
        '{"raw_snapshots": {}}', encoding="utf-8"
    )
    _successful_artifact(source_root, artifact_root)
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        if command[2] == "list":
            from subprocess import CompletedProcess

            return CompletedProcess(command, 0, stdout="123\n", stderr="")
        download_root = Path(command[command.index("--dir") + 1])
        shutil.copytree(artifact_root / "data", download_root / "data")
        from subprocess import CompletedProcess

        return CompletedProcess(command, 0, stdout="", stderr="")

    result = restore_latest_successful_state(tmp_path / "workspace", runner=runner)

    assert result.run_id == "123"
    assert result.artifact_name == "pipeline-state"
    assert (tmp_path / "workspace/data/silver/_incremental_state.json").exists()
    assert any(command[2] == "download" for command in calls)


def test_incremental_pipeline_is_idempotent_after_restore(tmp_path):
    source_root = tmp_path / "source"
    source_data = source_root / "data"
    _populate_raw(source_data / "raw")
    silver_root = source_data / "silver"
    gold_root = source_data / "gold"
    run_pipeline(
        settings=Settings(
            raw_data_dir=source_data / "raw",
            silver_data_dir=silver_root,
            gold_data_dir=gold_root,
        ),
        ingest=lambda: [],
    )
    artifact_root = tmp_path / "artifact"
    _successful_artifact(source_data, artifact_root)

    def runner(command, **kwargs):
        from subprocess import CompletedProcess

        if command[2] == "list":
            return CompletedProcess(command, 0, stdout="123\n", stderr="")
        download_root = Path(command[command.index("--dir") + 1])
        shutil.copytree(artifact_root / "data", download_root / "data")
        return CompletedProcess(command, 0, stdout="", stderr="")

    workspace = tmp_path / "workspace"
    restore_latest_successful_state(workspace, runner=runner)
    settings = Settings(
        raw_data_dir=workspace / "data/raw",
        silver_data_dir=workspace / "data/silver",
        gold_data_dir=workspace / "data/gold",
    )

    summary = run_pipeline(settings, ingest=lambda: [])

    assert summary.new_snapshots_processed == 0
    assert summary.snapshots_skipped == 12
