from pathlib import Path

import rasterio


BAND_DIR = Path("data/extracted")


for path in sorted(BAND_DIR.glob("*_10m.jp2")):

    print("\n" + "=" * 60)
    print("Band:", path.name)

    with rasterio.open(path) as src:

        print("CRS:", src.crs)
        print("Width:", src.width)
        print("Height:", src.height)
        print("Resolution:", src.res)
        print("Bounds:", src.bounds)
        print("Data type:", src.dtypes[0])
        print("NoData:", src.nodata)
        print("Transform:", src.transform)