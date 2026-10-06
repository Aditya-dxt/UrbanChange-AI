import os
import time
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import requests


TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/"
    "auth/realms/CDSE/protocol/openid-connect/token"
)

DOWNLOAD_URL = (
    "https://download.dataspace.copernicus.eu/"
    "odata/v1/Products({product_id})/$value"
)


class CopernicusDownloader:
    """
    Downloads Sentinel-2 products from Copernicus Data Space
    and stores them in a local cache.
    """

    def __init__(
        self,
        cache_dir: str = "data/cache",
    ):
        self.username = os.getenv("CDSE_USERNAME")
        self.password = os.getenv("CDSE_PASSWORD")

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.username or not self.password:
            raise RuntimeError(
                "CDSE_USERNAME and CDSE_PASSWORD "
                "environment variables are required."
            )

    def get_access_token(self) -> str:
        response = requests.post(
            TOKEN_URL,
            data={
                "client_id": "cdse-public",
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
            },
            timeout=30,
        )

        if not response.ok:
            try:
                error_details = response.json()
            except ValueError:
                error_details = response.text

            raise RuntimeError(
                f"Copernicus authentication failed "
                f"(HTTP {response.status_code}): "
                f"{error_details}"
            )

        data = response.json()

        if "access_token" not in data:
            raise RuntimeError(
                "Copernicus authentication succeeded "
                "but no access token was returned."
            )

        return data["access_token"]

    @staticmethod
    def validate_zip(path: Path) -> bool:
        """
        Check whether a downloaded file is a valid ZIP archive.
        """

        try:
            with ZipFile(path, "r") as archive:
                return archive.testzip() is None

        except BadZipFile:
            return False

        except OSError:
            return False

    def download_product(
        self,
        product_id: str,
        product_name: str,
        max_retries: int = 3,
    ) -> Path:
        """
        Download a Copernicus product and cache it locally.

        The file is first written to a temporary .part file.
        It is only renamed to .zip after the download has
        successfully completed and passed ZIP validation.
        """

        output_path = (
            self.cache_dir
            / f"{product_name}.zip"
        )

        temp_path = (
            self.cache_dir
            / f"{product_name}.zip.part"
        )

        # Existing valid cache
        if output_path.exists():
            if self.validate_zip(output_path):
                print("Valid cached product found.")
                return output_path

            print(
                "Existing ZIP is invalid. "
                "Removing incomplete file."
            )

            output_path.unlink()

        url = DOWNLOAD_URL.format(
            product_id=product_id
        )

        for attempt in range(1, max_retries + 1):

            print(
                f"\nDownload attempt "
                f"{attempt}/{max_retries}"
            )

            # Remove previous partial download.
            if temp_path.exists():
                temp_path.unlink()

            access_token = self.get_access_token()

            headers = {
                "Authorization": (
                    f"Bearer {access_token}"
                )
            }

            try:
                with requests.get(
                    url,
                    headers=headers,
                    stream=True,
                    timeout=(30, 300),
                ) as response:

                    print(
                        "HTTP status:",
                        response.status_code,
                    )

                    print(
                        "Content-Type:",
                        response.headers.get(
                            "Content-Type"
                        ),
                    )

                    print(
                        "Content-Length:",
                        response.headers.get(
                            "Content-Length"
                        ),
                    )

                    response.raise_for_status()

                    expected_size = response.headers.get(
                        "Content-Length"
                    )

                    expected_size = (
                        int(expected_size)
                        if expected_size
                        else None
                    )

                    downloaded_size = 0

                    with open(
                        temp_path,
                        "wb",
                    ) as file:

                        for chunk in response.iter_content(
                            chunk_size=1024 * 1024
                        ):
                            if not chunk:
                                continue

                            file.write(chunk)
                            downloaded_size += len(chunk)

                            if (
                                downloaded_size
                                % (50 * 1024 * 1024)
                                < 1024 * 1024
                            ):
                                print(
                                    "Downloaded:",
                                    f"{downloaded_size / (1024 * 1024):.1f} MB"
                                )

                print(
                    "Download finished:",
                    f"{downloaded_size / (1024 * 1024):.2f} MB"
                )

                # Check HTTP Content-Length when available.
                if (
                    expected_size is not None
                    and downloaded_size != expected_size
                ):
                    raise RuntimeError(
                        "Incomplete download: "
                        f"expected {expected_size} bytes, "
                        f"received {downloaded_size} bytes."
                    )

                # Most important check: ZIP integrity.
                print("Validating ZIP archive...")

                if not self.validate_zip(temp_path):
                    raise RuntimeError(
                        "Downloaded file is not a valid "
                        "complete ZIP archive."
                    )

                # Only now expose it as the final .zip.
                temp_path.replace(output_path)

                print(
                    "\nDownload and validation successful."
                )

                return output_path

            except Exception as exc:

                print(
                    f"Download attempt {attempt} failed:"
                )
                print(exc)

                if temp_path.exists():
                    temp_path.unlink()

                if attempt < max_retries:
                    print(
                        "Retrying in 5 seconds..."
                    )
                    time.sleep(5)

                else:
                    raise RuntimeError(
                        "Failed to download a valid "
                        "Sentinel-2 product after "
                        f"{max_retries} attempts."
                    ) from exc

        raise RuntimeError(
            "Download failed unexpectedly."
        )