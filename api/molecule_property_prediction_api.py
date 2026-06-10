from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter(prefix="/models", tags=["molecule-property"])


class MoleculePropertyRequest(BaseModel):
    smiles: str = Field(..., min_length=1, description="Input molecule SMILES")


@router.get("/info")
def model_info() -> dict[str, object]:
    return {
        "model_name": "molecule_property_prediction_demo",
        "model_version": "0.1.0",
        "status": "demo",
        "source_dir": "models/molecule_property_prediction",
        "supported_properties": ["logp", "molecular_weight", "solubility"],
    }


@router.post("/molecule_property_prediction")
def predict_molecule_property(request: MoleculePropertyRequest) -> dict[str, object]:
    return {
        "model_name": "molecule_property_prediction_demo",
        "model_version": "0.1.0",
        "status": "demo",
        "input": {"smiles": request.smiles},
        "predictions": {
            "logp": None,
            "molecular_weight": None,
            "solubility": None,
        },
        "message": "Demo response only. Add real model code under models/molecule_property_prediction.",
    }
