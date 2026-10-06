from datetime import date, timedelta
from typing import Any

import pystac_client


STAC_URL = "https://stac.dataspace.copernicus.eu/v1/"
SENTINEL_COLLECTION = "sentinel-2-l2a"


class SentinelCatalog:
    """
    Handles discovery of Sentinel-2 observations
    from the Copernicus Data Space STAC catalog.
    """

    def __init__(self, stac_url: str = STAC_URL):
        self.stac_url = stac_url
        self.catalog = pystac_client.Client.open(stac_url)

    @staticmethod
    def bbox_to_geometry(
        bbox: dict[str, float],
    ) -> dict[str, Any]:
        return {
            "type": "Polygon",
            "coordinates": [
                [
                    [bbox["min_lon"], bbox["min_lat"]],
                    [bbox["max_lon"], bbox["min_lat"]],
                    [bbox["max_lon"], bbox["max_lat"]],
                    [bbox["min_lon"], bbox["max_lat"]],
                    [bbox["min_lon"], bbox["min_lat"]],
                ]
            ],
        }

    def search(
        self,
        bbox: dict[str, float],
        target_date: date,
        window_days: int,
        max_cloud_percentage: float,
    ) -> list[Any]:

        start_date = target_date - timedelta(days=window_days)
        end_date = target_date + timedelta(days=window_days)

        geometry = self.bbox_to_geometry(bbox)

        search = self.catalog.search(
            collections=[SENTINEL_COLLECTION],
            intersects=geometry,
            datetime=f"{start_date.isoformat()}/{end_date.isoformat()}",
            query={
                "eo:cloud_cover": {
                    "lte": max_cloud_percentage
                }
            },
            max_items=100,
        )

        return list(search.items())