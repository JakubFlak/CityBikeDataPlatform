from pathlib import Path

WORKFLOW = Path(".github/workflows/data-pipeline.yml")


def test_workflow_restores_before_running_and_only_publishes_success_state():
    content = WORKFLOW.read_text(encoding="utf-8")

    restore_position = content.index("Restore latest successful pipeline state")
    run_position = content.index("Run one pipeline job")
    schema_position = content.index("Validate Gold schema")
    success_upload_position = content.index("Upload successful pipeline state")
    failure_upload_position = content.index("Upload failed-run diagnostics")

    assert restore_position < run_position < schema_position < success_upload_position
    assert "name: pipeline-state" in content
    assert "if: success()" in content
    assert failure_upload_position > run_position
    assert "name: pipeline-failure-${{ github.run_id }}" in content
    assert "if: failure()" in content
    assert "actions: read" in content
    assert "scripts/validate_gold_schema.py" in content
