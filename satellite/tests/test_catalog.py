from datetime import date

from app.services.catalog import SentinelCatalog
from app.services.acquisition import AcquisitionSelector


catalog = SentinelCatalog()

bbox = {
    "min_lon": 80.20,
    "min_lat": 26.40,
    "max_lon": 80.22,
    "max_lat": 26.42,
}

historical_date = date(2024, 5, 15)
current_date = date(2026, 5, 15)

max_cloud = 20
window_days = 30


before_items = catalog.search(
    bbox=bbox,
    target_date=historical_date,
    window_days=window_days,
    max_cloud_percentage=max_cloud,
)

after_items = catalog.search(
    bbox=bbox,
    target_date=current_date,
    window_days=window_days,
    max_cloud_percentage=max_cloud,
)


before, after = AcquisitionSelector.select_pair(
    before_items=before_items,
    after_items=after_items,
    historical_date=historical_date,
    current_date=current_date,
)


print(f"BEFORE candidates: {len(before_items)}")
print(f"AFTER candidates: {len(after_items)}")


if before:
    print("\nBEFORE:")
    print("ID:", before.id)
    print("Date:", before.datetime)
    print(
        "Cloud:",
        before.properties.get("eo:cloud_cover"),
    )
else:
    print("\nNo suitable BEFORE observation found.")


if after:
    print("\nAFTER:")
    print("ID:", after.id)
    print("Date:", after.datetime)
    print(
        "Cloud:",
        after.properties.get("eo:cloud_cover"),
    )
else:
    print("\nNo suitable AFTER observation found.")