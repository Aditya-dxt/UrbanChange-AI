from fastapi import FastAPI
from app.api.routes import router as gis_router

app = FastAPI(
    title="UrbanChange AI - GIS Engine (Role 3)",
    description="Spatial analysis of change polygons against sensitive zoning and environmental layers",
    version="0.1.0",
)

app.include_router(gis_router)


@app.get("/health")
def health():
    return {"status": "healthy", "module": "gis"}
