from datetime import date

from app.services.catalog import SentinelCatalog
from app.services.acquisition import AcquisitionSelector
from app.services.downloader import CopernicusDownloader


catalog = SentinelCatalog()
downloader = CopernicusDownloader()

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
    raise RuntimeError(
        "No suitable Sentinel-2 observation found."
    )


print("Selected product:")
print(selected.id)


private_data = selected.properties.get("_private")

if not private_data:
    raise RuntimeError(
        "STAC item does not contain _private metadata."
    )


product_id = private_data.get("product_uuid")
product_name = private_data.get("product_name")


if not product_id:
    raise RuntimeError(
        "Product UUID not found in STAC item."
    )

if not product_name:
    raise RuntimeError(
        "Product name not found in STAC item."
    )


print("\nProduct UUID:")
print(product_id)

print("\nProduct name:")
print(product_name)

print("\nStarting download...")
print("This product is approximately 600+ MB.")


product_path = downloader.download_product(
    product_id=product_id,
    product_name=product_name.removesuffix(".SAFE"),
)


print("\nDownload successful!")

print("Saved to:")
print(product_path)

print("\nFile size:")
print(
    f"{product_path.stat().st_size / (1024 * 1024):.2f} MB"
)