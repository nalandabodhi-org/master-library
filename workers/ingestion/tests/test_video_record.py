import pytest

from src.domain.video_record import normalize_video_record


def make_record(fields: dict) -> dict:
    return {"id": "rec123", "fields": fields}


def test_normalize_video_record_extracts_primary_asset():
    record = normalize_video_record(
        make_record(
            {
                "Slug": "heart-sutra-part-1",
                "Sync Status": "ready_for_ingest",
                "Assets": [
                    {
                        "id": "ast1",
                        "type": "source_video",
                        "isPrimary": True,
                        "r2Key": "videos/heart.mp4",
                    }
                ],
            }
        )
    )

    assert record.slug == "heart-sutra-part-1"
    assert record.primary_asset["r2Key"] == "videos/heart.mp4"


def test_normalize_video_record_defaults_sync_status_to_draft():
    record = normalize_video_record(
        make_record(
            {
                "Slug": "heart-sutra-part-1",
                "Assets": [
                    {
                        "id": "ast1",
                        "type": "source_video",
                        "isPrimary": True,
                        "r2Key": "videos/heart.mp4",
                    }
                ],
            }
        )
    )

    assert record.sync_status == "draft"


def test_normalize_video_record_raises_for_missing_slug():
    with pytest.raises(ValueError, match="Video missing Slug"):
        normalize_video_record(
            make_record(
                {
                    "Assets": [
                        {
                            "id": "ast1",
                            "type": "source_video",
                            "isPrimary": True,
                            "r2Key": "videos/heart.mp4",
                        }
                    ]
                }
            )
        )


def test_normalize_video_record_raises_for_zero_primary_assets():
    with pytest.raises(ValueError, match="exactly one primary source asset"):
        normalize_video_record(
            make_record(
                {
                    "Slug": "heart-sutra-part-1",
                    "Assets": [
                        {
                            "id": "ast1",
                            "type": "source_video",
                            "isPrimary": False,
                            "r2Key": "videos/heart.mp4",
                        }
                    ],
                }
            )
        )


def test_normalize_video_record_raises_for_multiple_primary_assets():
    with pytest.raises(ValueError, match="exactly one primary source asset"):
        normalize_video_record(
            make_record(
                {
                    "Slug": "heart-sutra-part-1",
                    "Assets": [
                        {
                            "id": "ast1",
                            "type": "source_video",
                            "isPrimary": True,
                            "r2Key": "videos/heart.mp4",
                        },
                        {
                            "id": "ast2",
                            "type": "source_video",
                            "isPrimary": True,
                            "r2Key": "videos/heart-alt.mp4",
                        },
                    ],
                }
            )
        )


def test_normalize_video_record_raises_for_primary_asset_missing_r2_key():
    with pytest.raises(ValueError, match="primary source asset must include r2Key"):
        normalize_video_record(
            make_record(
                {
                    "Slug": "heart-sutra-part-1",
                    "Assets": [
                        {
                            "id": "ast1",
                            "type": "source_video",
                            "isPrimary": True,
                        }
                    ],
                }
            )
        )
