from pathlib import Path

import rasterio


class SentinelProcessor:

    BAND_ORDER = ("B02", "B03", "B04", "B08")

    def stack_bands(
        self,
        band_paths: dict[str, Path],
        output_path: Path,
    ) -> Path:

        missing = [
            band for band in self.BAND_ORDER
            if band not in band_paths
        ]

        if missing:
            raise ValueError(
                f"Missing required bands: {', '.join(missing)}"
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        sources = []

        try:
            for band in self.BAND_ORDER:
                src = rasterio.open(band_paths[band])
                sources.append(src)

            reference = sources[0]

            # Validate every band against B02
            for band, src in zip(self.BAND_ORDER, sources):

                if src.crs != reference.crs:
                    raise ValueError(
                        f"{band} CRS does not match B02."
                    )

                if src.width != reference.width:
                    raise ValueError(
                        f"{band} width does not match B02."
                    )

                if src.height != reference.height:
                    raise ValueError(
                        f"{band} height does not match B02."
                    )

                if src.transform != reference.transform:
                    raise ValueError(
                        f"{band} transform does not match B02."
                    )

                if src.res != reference.res:
                    raise ValueError(
                        f"{band} resolution does not match B02."
                    )

            profile = reference.profile.copy()

            profile.update(
                driver="GTiff",
                count=4,
                dtype=reference.dtypes[0],
            )

            with rasterio.open(
                output_path,
                "w",
                **profile,
            ) as dst:

                for index, src in enumerate(sources, start=1):
                    dst.write(
                        src.read(1),
                        index,
                    )

                dst.set_band_description(1, "B02 Blue")
                dst.set_band_description(2, "B03 Green")
                dst.set_band_description(3, "B04 Red")
                dst.set_band_description(4, "B08 NIR")

        finally:
            for src in sources:
                src.close()

        return output_path