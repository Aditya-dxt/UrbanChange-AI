from fastapi import FastAPI

from app.api.routes import router as satellite_router


app = FastAPI(
    title="UrbanChange AI - Satellite Service",
    version="0.1.0",
)

app.include_router(satellite_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "satellite",
    }