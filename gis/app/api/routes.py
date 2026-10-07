import logging
from typing import Any
from fastapi import APIRouter
from shapely.ops import unary_union

from app.models.schemas import (
    GISAnalyzeChangeResponse,
    GISAnalyzeRequest,
    NearbyFeature,
    SensitiveIntersection,
)
from app.services.context import ContextService
from app.services.geometry import (
    compute_projected_area_m2,
    parse_geojson_geometry,
)
from app.services.sensitive import SensitiveLayerManager

log = logging.getLogger(__name__)

router = APIRouter(prefix="/gis", tags=["GIS"])
sensitive_mgr = SensitiveLayerManager()


@router.post(
    "/analyze-change",
    response_model=GISAnalyzeChangeResponse,
    summary="Analyze change polygons against sensitive layers and context",
)
@router.post(
    "/analyze",
    response_model=GISAnalyzeChangeResponse,
    summary="Alias for /analyze-change",
)
def analyze_change(request: GISAnalyzeRequest) -> GISAnalyzeChangeResponse:
    # 1. Parse change geometries
    parsed_geoms = []
    for reg in request.change_regions:
        geom_dict = reg.get("geometry") or reg
        s = parse_geojson_geometry(geom_dict)
        if s is not None and not s.is_empty:
            parsed_geoms.append(s)

    # Fallback to bbox if no change regions provided
    if not parsed_geoms and len(request.bbox) == 4:
        w, s, e, n = request.bbox
        from shapely.geometry import box
        # Use an inner subset of the bbox as a simulated change polygon
        dw = (e - w) * 0.2
        dh = (n - s) * 0.2
        parsed_geoms.append(box(w + dw, s + dh, e - dw, n - dh))

    combined_geom = unary_union(parsed_geoms) if parsed_geoms else None

    # 2. Compute area in projected CRS (m²)
    changed_area_m2 = compute_projected_area_m2(combined_geom)

    # 3. Analyze sensitive intersections
    raw_intersections = sensitive_mgr.analyze_intersections(
        change_geom=combined_geom,
        change_area_m2=changed_area_m2,
    )

    intersections = [
        SensitiveIntersection(
            layer_name=item["layer_name"],
            layer_id=item["layer_id"],
            overlap_pct=item["overlap_pct"],
            geometry=item["geometry"],
        )
        for item in raw_intersections
    ]

    overlap_pcts = {item["layer_name"]: item["overlap_pct"] for item in raw_intersections}

    # 4. Nearby context features
    centroid_lon = combined_geom.centroid.x if combined_geom else (request.bbox[0] + request.bbox[2]) / 2
    centroid_lat = combined_geom.centroid.y if combined_geom else (request.bbox[1] + request.bbox[3]) / 2

    raw_nearby = ContextService.get_nearby_features(request.bbox, centroid_lon, centroid_lat)
    nearby_features = [
        NearbyFeature(
            feature_type=f["feature_type"],
            name=f["name"],
            distance_m=f["distance_m"],
            geometry=f.get("geometry"),
        )
        for f in raw_nearby
    ]

    distances = {f["name"] or f["feature_type"]: f["distance_m"] for f in raw_nearby}

    # 5. Composite GeoJSON for client visualization
    geojson_features = []
    for item in raw_intersections:
        if item.get("geometry"):
            geojson_features.append({
                "type": "Feature",
                "geometry": item["geometry"],
                "properties": {
                    "layer_name": item["layer_name"],
                    "overlap_pct": item["overlap_pct"],
                    "overlap_area_m2": item["overlap_area_m2"],
                    "legal_disclaimer": "Authoritative sample buffer; not legal title or determination",
                },
            })

    geojson_out = {
        "type": "FeatureCollection",
        "features": geojson_features,
    }

    return GISAnalyzeChangeResponse(
        changed_area_m2=round(changed_area_m2, 2),
        sensitive_intersections=intersections,
        overlap_percentages=overlap_pcts,
        nearby_features=nearby_features,
        geojson=geojson_out,
        layer_versions={"sample-sensitive-zones": "v1.2"},
        distances=distances,
    )
