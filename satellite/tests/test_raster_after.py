from pathlib import Path

from app.services.raster import SentinelRasterExtractor


PRODUCT = Path(
    "data/cache/"
    "S2C_MSIL2A_20260517T050651_N0512_R019_T44RMQ_20260517T100909.SAFE.zip"
)


extractor = SentinelRasterExtractor(
    extract_dir="data/extracted_after"
)

bands = extractor.extract_bands(
    PRODUCT
)

print("Extracted AFTER bands:")

for band, path in bands.items():
    print(f"{band}: {path}")