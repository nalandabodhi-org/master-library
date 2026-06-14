from src.domain.video_record import VideoRecord
from src.eligibility import assert_eligible_for_ingest


def test_assert_eligible_for_ingest_accepts_valid_record():
    record = VideoRecord(
        record_id="rec123",
        slug="heart-sutra-part-1",
        sync_status="ready_for_ingest",
        primary_asset={"r2Key": "videos/heart.mp4"},
    )

    assert_eligible_for_ingest(record)
