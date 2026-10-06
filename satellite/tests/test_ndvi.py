from pathlib import Path

import numpy as np
import rasterio

from app.services.ndvi import NDVICalculator


BAND_DIR = Path("data/clipped")

red = next(
    BAND_DIR.glob("*_B04_10m_clipped.tif")
)

nir = next(
    BAND_DIR.glob("*_B08_10m_clipped.tif")
)

output = (
    Path("data/analysis")
    / "ndvi_before.tif"
)


calculator = NDVICalculator()

result = calculator.calculate(
    red_path=red,
    nir_path=nir,
    output_path=output,
)

print("NDVI created:")
print(result)


with rasterio.open(result) as src:

    ndvi = src.read(1)

    valid = ndvi[
        np.isfinite(ndvi)
    ]

    print("\nNDVI statistics:")
    print("Width:", src.width)
    print("Height:", src.height)
    print("CRS:", src.crs)
    print("Min:", float(valid.min()))
    print("Max:", float(valid.max()))
    print("Mean:", float(valid.mean()))