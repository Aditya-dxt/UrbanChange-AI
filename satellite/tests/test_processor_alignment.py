from pathlib import Path

import rasterio


BEFORE = Path("data/analysis/before_multiband.tif")
AFTER = Path("data/analysis/after_multiband.tif")


with rasterio.open(BEFORE) as before, \
     rasterio.open(AFTER) as after:

    assert before.count == after.count == 4
    assert before.crs == after.crs
    assert before.width == after.width
    assert before.height == after.height
    assert before.transform == after.transform
    assert before.res == after.res
    assert before.bounds == after.bounds

    print("BEFORE/AFTER multiband alignment: PASS")
    print("Bands:", before.count)
    print("CRS:", before.crs)
    print("Size:", before.width, "x", before.height)
    print("Resolution:", before.res)
    print("Transform:", before.transform)
    print("Bounds:", before.bounds)