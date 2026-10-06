import numpy as np
import rasterio


FILES = [
    "data/analysis/ndvi_before.tif",
    "data/analysis/ndvi_after.tif",
    "data/analysis/ndvi_change.tif",
]


for path in FILES:
    with rasterio.open(path) as src:
        data = src.read(1)

    valid = np.isfinite(data)

    print("\n" + "=" * 50)
    print(path)
    print("Valid:", valid.sum())
    print("NaN:", np.isnan(data).sum())
    print("Total:", data.size)

    if valid.any():
        print("Min:", np.nanmin(data))
        print("Max:", np.nanmax(data))
        print("Mean:", np.nanmean(data))
    else:
        print("NO VALID DATA")