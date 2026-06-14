from src.domain.video_record import VideoRecord


def assert_eligible_for_ingest(record: VideoRecord) -> None:
    if record.sync_status != "ready_for_ingest":
        raise ValueError("Video is not ready_for_ingest")
    if not record.slug:
        raise ValueError("Video missing slug")
    if not record.primary_asset.get("r2Key"):
        raise ValueError("Video missing primary source asset")
