from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .config import settings
from .predictor import MMCLKinPredictionError, MMCLKinPredictor
from .schemas import (
    AffinityRequest,
    AffinityResponse,
    ErrorResponse,
    SelectivityRequest,
    SelectivityResponse,
)


predictor: MMCLKinPredictor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global predictor
    predictor = MMCLKinPredictor(settings)
    predictor.load()
    yield


app = FastAPI(
    title="MMCLKin API",
    description="Kinase-inhibitor affinity and selectivity prediction service.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": "MMCLKin"}


@app.post(
    "/api/mmclkin/affinity",
    response_model=AffinityResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def predict_affinity(request: AffinityRequest) -> AffinityResponse:
    try:
        if predictor is None:
            raise MMCLKinPredictionError("MMCLKin predictor has not been initialized.", status_code=500)
        return predictor.predict_affinity(request)
    except MMCLKinPredictionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"status": "error", "message": str(exc), "warnings": exc.warnings})


@app.post(
    "/api/mmclkin/selectivity",
    response_model=SelectivityResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def predict_selectivity(request: SelectivityRequest) -> SelectivityResponse:
    try:
        if predictor is None:
            raise MMCLKinPredictionError("MMCLKin predictor has not been initialized.", status_code=500)
        return predictor.predict_selectivity(request)
    except MMCLKinPredictionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"status": "error", "message": str(exc), "warnings": exc.warnings})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.mmclkin.api:app", host=settings.host, port=settings.port, reload=False)
