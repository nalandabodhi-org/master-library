import pytest

from src.domain.video_state import transition_video_state


def test_transition_video_state_allows_ready_for_ingest_to_ingesting():
    assert transition_video_state("ready_for_ingest", "ingesting") == "ingesting"


def test_transition_video_state_rejects_ready_to_stream_to_ingesting():
    with pytest.raises(ValueError, match="Invalid transition"):
        transition_video_state("ready_to_stream", "ingesting")


def test_transition_video_state_allows_no_op_transition():
    assert transition_video_state("ready_to_stream", "ready_to_stream") == "ready_to_stream"


def test_transition_video_state_rejects_unknown_state_no_op():
    with pytest.raises(ValueError, match="Invalid transition"):
        transition_video_state("bogus", "bogus")
