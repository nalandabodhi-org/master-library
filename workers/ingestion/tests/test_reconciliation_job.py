import pytest

from src.reconciliation_job import reconcile_state


def test_reconcile_state_marks_error_for_failed_stream():
    assert reconcile_state("processing", {"failed": True}) == "error"


def test_reconcile_state_uses_shared_stream_failure_interpretation():
    assert reconcile_state("processing", {"status": "failed"}) == "error"


def test_reconcile_state_recovers_drifted_ingesting_record_to_ready_to_stream():
    assert reconcile_state("ingesting", {"readyToStream": True}) == "ready_to_stream"


def test_reconcile_state_rejects_invalid_transition_from_stream_state():
    with pytest.raises(ValueError, match="Invalid transition"):
        reconcile_state("ready_for_ingest", {"status": "downloading"})
