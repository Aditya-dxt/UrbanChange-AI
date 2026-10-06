from pathlib import Path

import rasterio

from app.services.change import NDVIChangeCalculator


BEFORE = Path("data/analysis/ndvi_before.tif")
AFTER = Path("data/analysis/ndvi_after.tif")

OUTPUT = Path("data/analysis/ndvi_change.tif")


calculator = NDVIChangeCalculator()

result = calculator.calculate(
    before_path=BEFORE,
    after_path=AFTER,
    output_path=OUTPUT,
)

print("NDVI change created:")
print(result)

with rasterio.open(result) as src:

    data = src.read(1)

    print("CRS:", src.crs)
    print("Size:", src.width, "x", src.height)
    print("Resolution:", src.res)
    print("Bounds:", src.bounds)

    print("Min:", data.min())
    print("Max:", data.max())
    print("Mean:", data.mean())