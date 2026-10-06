from pathlib import Path

from app.services.raster import SentinelRasterExtractor


PRODUCT = Path(
    "data/cache/"
    "S2B_MSIL2A_20240515T051649_N0510_R062_T44RMQ_20240515T074942.zip"
)


extractor = SentinelRasterExtractor()

bands = extractor.extract_bands(
    PRODUCT
)

print("Extracted bands:")

for band, path in bands.items():
    print(
        f"{band}: {path}"
    )