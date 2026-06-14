from dataclasses import dataclass


@dataclass
class VideoRecord:
    record_id: str
    slug: str
    sync_status: str
    primary_asset: dict


def normalize_video_record(record: dict) -> VideoRecord:
    fields = record.get("fields", {})
    slug = fields.get("Slug")
    if not slug:
        raise ValueError("Video missing Slug")

    assets = fields.get("Assets", [])
    primary_assets = [
        asset for asset in assets if asset.get("isPrimary") and asset.get("type") == "source_video"
    ]
    if len(primary_assets) != 1:
        raise ValueError("Video must have exactly one primary source asset")

    primary_asset = primary_assets[0]
    if not primary_asset.get("r2Key"):
        raise ValueError("Video primary source asset must include r2Key")

    return VideoRecord(
        record_id=record["id"],
        slug=slug,
        sync_status=fields.get("Sync Status", "draft"),
        primary_asset=primary_asset,
    )
