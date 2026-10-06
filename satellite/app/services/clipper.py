from pathlib import Path

import rasterio
from rasterio.mask import mask
from rasterio.warp import transform_bounds
from shapely.geometry import box, mapping


class SentinelClipper:
    """
    Clips Sentinel-2 raster bands to a WGS84 bounding box.
    """

    def clip_band(
        self,
        input_path: str | Path,
        output_path: str | Path,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
    ) -> Path:

        input_path = Path(input_path)
        output_path = Path(output_path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with rasterio.open(input_path) as src:

            # Transform WGS84 bbox into the raster CRS.
            bounds = transform_bounds(
                "EPSG:4326",
                src.crs,
                min_lon,
                min_lat,
                max_lon,
                max_lat,
            )

            geometry = box(*bounds)

            clipped, transform = mask(
                src,
                [mapping(geometry)],
                crop=True,
            )

            profile = src.profile.copy()

            profile.update(
                {
                    "height": clipped.shape[1],
                    "width": clipped.shape[2],
                    "transform": transform,
                }
            )

            with rasterio.open(
                output_path,
                "w",
                **profile,
            ) as dst:

                dst.write(clipped)

        return output_path