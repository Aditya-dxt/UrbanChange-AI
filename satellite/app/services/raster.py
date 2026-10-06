from pathlib import Path
from zipfile import ZipFile


class SentinelRasterExtractor:
    """
    Extracts selected Sentinel-2 raster bands from a
    downloaded SAFE ZIP product.
    """

    REQUIRED_BANDS = {
        "B02": "_B02_10m.jp2",
        "B03": "_B03_10m.jp2",
        "B04": "_B04_10m.jp2",
        "B08": "_B08_10m.jp2",
    }

    def __init__(
        self,
        extract_dir: str = "data/extracted",
    ):
        self.extract_dir = Path(extract_dir)
        self.extract_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def find_band_paths(
        self,
        product_zip: str | Path,
    ) -> dict[str, str]:
        """
        Find the paths of the required 10m bands
        inside the Sentinel-2 ZIP archive.
        """

        product_zip = Path(product_zip)

        if not product_zip.exists():
            raise FileNotFoundError(
                f"Product ZIP not found: {product_zip}"
            )

        with ZipFile(product_zip, "r") as archive:

            names = archive.namelist()

        band_paths = {}

        for band, suffix in self.REQUIRED_BANDS.items():

            matches = [
                name
                for name in names
                if name.endswith(suffix)
            ]

            if not matches:
                raise RuntimeError(
                    f"{band} 10m band not found "
                    f"in {product_zip}"
                )

            if len(matches) > 1:
                raise RuntimeError(
                    f"Multiple {band} 10m bands found: "
                    f"{matches}"
                )

            band_paths[band] = matches[0]

        return band_paths

    def extract_bands(
        self,
        product_zip: str | Path,
    ) -> dict[str, Path]:
        """
        Extract the required 10m bands from the ZIP.

        Returns:
            Dictionary mapping band names to extracted
            local JP2 paths.
        """

        product_zip = Path(product_zip)

        band_paths = self.find_band_paths(
            product_zip
        )

        extracted = {}

        with ZipFile(product_zip, "r") as archive:

            for band, archive_path in band_paths.items():

                filename = Path(
                    archive_path
                ).name

                output_path = (
                    self.extract_dir
                    / filename
                )

                if not output_path.exists():

                    with archive.open(
                        archive_path
                    ) as source:

                        with open(
                            output_path,
                            "wb",
                        ) as target:

                            while True:
                                chunk = source.read(
                                    1024 * 1024
                                )

                                if not chunk:
                                    break

                                target.write(chunk)

                extracted[band] = output_path

        return extracted