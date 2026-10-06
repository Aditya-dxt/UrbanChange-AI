from pathlib import Path

import rasterio


CLIPPED_DIR = Path("data/clipped")

for path in sorted(
    CLIPPED_DIR.glob("*_clipped.tif")
):
    print("\n" + "=" * 60)
    print("Band:", path.name)

    with rasterio.open(path) as src:
        print("CRS:", src.crs)
        print("Width:", src.width)
        print("Height:", src.height)
        print("Resolution:", src.res)
        print("Bounds:", src.bounds)
        print("Data type:", src.dtypes[0])
        print("Transform:", src.transform)