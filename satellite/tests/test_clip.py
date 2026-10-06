from pathlib import Path

from app.services.clipper import SentinelClipper


BAND_DIR = Path("data/extracted")
OUTPUT_DIR = Path("data/clipped")

BBOX = {
    "min_lon": 80.20,
    "min_lat": 26.40,
    "max_lon": 80.22,
    "max_lat": 26.42,
}


clipper = SentinelClipper()

for band_path in sorted(BAND_DIR.glob("*_10m.jp2")):

    output_path = (
        OUTPUT_DIR
        / f"{band_path.stem}_clipped.tif"
    )

    result = clipper.clip_band(
        input_path=band_path,
        output_path=output_path,
        **BBOX,
    )

    print(
        f"Clipped: {band_path.name}"
    )
    print(
        f"Saved:   {result}"
    )