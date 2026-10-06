from datetime import date
from typing import Any


class AcquisitionSelector:

    @staticmethod
    def select_closest(
        items: list[Any],
        target_date: date,
    ) -> Any | None:

        if not items:
            return None

        valid_items = [
            item
            for item in items
            if item.datetime is not None
        ]

        if not valid_items:
            return None

        return min(
            valid_items,
            key=lambda item: abs(
                item.datetime.date() - target_date
            )
        )

    @classmethod
    def select_pair(
        cls,
        before_items: list[Any],
        after_items: list[Any],
        historical_date: date,
        current_date: date,
    ) -> tuple[Any | None, Any | None]:

        before = cls.select_closest(
            before_items,
            historical_date,
        )

        after = cls.select_closest(
            after_items,
            current_date,
        )

        return before, after

    @staticmethod
    def to_observation(item: Any):
        from app.models.schemas import SatelliteObservation

        return SatelliteObservation(
            item_id=item.id,
            acquisition_date=item.datetime.date(),
            sensor="Sentinel-2",
            cloud_percentage=item.properties.get("eo:cloud_cover"),
            crs=None,
            resolution_m=10.0,
            image_reference=None,
        )