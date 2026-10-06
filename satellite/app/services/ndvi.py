from pathlib import Path

import numpy as np
import rasterio


class NDVICalculator:
    """
    Calculates NDVI from Sentinel-2 Red (B04)
    and Near-Infrared (B08) bands.
    """

    def calculate(
        self,
        red_path: str | Path,
        nir_path: str | Path,
        output_path: str | Path,
    ) -> Path:

        red_path = Path(red_path)
        nir_path = Path(nir_path)
        output_path = Path(output_path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with rasterio.open(red_path) as red_src:
            with rasterio.open(nir_path) as nir_src:

                # Ensure both rasters use the same spatial grid.
                if (
                    red_src.crs != nir_src.crs
                    or red_src.width != nir_src.width
                    or red_src.height != nir_src.height
                    or red_src.transform != nir_src.transform
                ):
                    raise ValueError(
                        "Red and NIR rasters are not spatially aligned."
                    )

                red = red_src.read(1).astype(
                    np.float32
                )

                nir = nir_src.read(1).astype(
                    np.float32
                )

                denominator = nir + red

                ndvi = np.full(
                    red.shape,
                    np.nan,
                    dtype=np.float32,
                )

                valid = denominator != 0

                ndvi[valid] = (
                    (nir[valid] - red[valid])
                    / denominator[valid]
                )

                # Build a GeoTIFF profile.
                profile = red_src.profile.copy()

                profile.update(
                    {
                        "driver": "GTiff",
                        "dtype": "float32",
                        "count": 1,
                        "nodata": np.nan,
                        "compress": "deflate",
                    }
                )

                with rasterio.open(
                    output_path,
                    "w",
                    **profile,
                ) as dst:

                    dst.write(ndvi, 1)

        return output_path