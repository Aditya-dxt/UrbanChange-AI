from pathlib import Path

import rasterio

from app.services.processor import SentinelProcessor


BAND_DIR = Path("data/clipped")

BANDS = {
    "B02": next(BAND_DIR.glob("*B02_10m_clipped.tif")),
    "B03": next(BAND_DIR.glob("*B03_10m_clipped.tif")),
    "B04": next(BAND_DIR.glob("*B04_10m_clipped.tif")),
    "B08": next(BAND_DIR.glob("*B08_10m_clipped.tif")),
}

OUTPUT = Path("data/analysis/before_multiband.tif")


processor = SentinelProcessor()

result = processor.stack_bands(
    band_paths=BANDS,
    output_path=OUTPUT,
)

print("BEFORE multiband raster created:")
print(result)

with rasterio.open(result) as src:

    print("Driver:", src.driver)
    print("Band count:", src.count)
    print("Dtype:", src.dtypes)
    print("CRS:", src.crs)
    print("Size:", src.width, "x", src.height)
    print("Resolution:", src.res)
    print("Bounds:", src.bounds)
    print("Band descriptions:")

    for index in range(1, src.count + 1):
        print(
            f"  {index}: {src.descriptions[index - 1]}"
        )