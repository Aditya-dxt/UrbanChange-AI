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

target_date = date(2024, 5, 15)

items = catalog.search(
    bbox=bbox,
    target_date=target_date,
    window_days=30,
    max_cloud_percentage=20,
)

selected = AcquisitionSelector.select_closest(
    items,
    target_date,
)

if selected is None:
    raise RuntimeError("No suitable Sentinel-2 observation found.")


print("Selected item:")
print(selected.id)

print("\nAvailable assets:")

for name, asset in selected.assets.items():
    print(f"{name:20} -> {asset.href}")