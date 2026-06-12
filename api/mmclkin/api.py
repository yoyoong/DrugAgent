from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import sys
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException

from .config import PROJECT_ROOT, settings
from .predictor import MMCLKinPredictionError, MMCLKinPredictor
from .schemas import (
    AffinityRequest,
    AffinityResponse,
    ErrorResponse,
    SelectivityRequest,
    SelectivityResponse,
)


logger = logging.getLogger(__name__)
predictor: Optional[MMCLKinPredictor] = None


def _configure_logger() -> None:
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return

    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(PROJECT_ROOT / "mmclkin_api.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


_configure_logger()


def _model_dump(model):
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


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
def health() -> Dict[str, str]:
    return {"status": "ok", "model": "MMCLKin"}


@app.post(
    "/api/mmclkin/affinity",
    response_model=AffinityResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def predict_affinity(request: AffinityRequest) -> AffinityResponse:
    logger.info("MMCLKin affinity request: %s", _model_dump(request))
    try:
        if predictor is None:
            raise MMCLKinPredictionError("MMCLKin predictor has not been initialized.", status_code=500)
        response = predictor.predict_affinity(request)
        logger.info("MMCLKin affinity response: %s", _model_dump(response))
        return response
    except MMCLKinPredictionError as exc:
        error_response = {"status": "error", "message": str(exc), "warnings": exc.warnings}
        logger.info("MMCLKin affinity response: %s", error_response)
        raise HTTPException(status_code=exc.status_code, detail={"status": "error", "message": str(exc), "warnings": exc.warnings})


@app.post(
    "/api/mmclkin/selectivity",
    response_model=SelectivityResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def predict_selectivity(request: SelectivityRequest) -> SelectivityResponse:
    logger.info("MMCLKin selectivity request: %s", _model_dump(request))
    try:
        if predictor is None:
            raise MMCLKinPredictionError("MMCLKin predictor has not been initialized.", status_code=500)
        response = predictor.predict_selectivity(request)
        logger.info("MMCLKin selectivity response: %s", _model_dump(response))
        return response
    except MMCLKinPredictionError as exc:
        error_response = {"status": "error", "message": str(exc), "warnings": exc.warnings}
        logger.info("MMCLKin selectivity response: %s", error_response)
        raise HTTPException(status_code=exc.status_code, detail={"status": "error", "message": str(exc), "warnings": exc.warnings})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.mmclkin.api:app", host=settings.host, port=settings.port, reload=False)
