from fastapi import FastAPI

from api.molecule_property_prediction_api import router as molecule_property_router


app = FastAPI(title="DrugAgent Model API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(molecule_property_router)
