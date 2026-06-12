from typing import Literal

from pydantic import BaseModel, Field


DatasetName = Literal["3DKDavis"]
StructureSource = Literal["mmclkin_database"]


class AffinityRequest(BaseModel):
    kinase_id: str = Field(..., min_length=1)
    ligand_id: str = Field(..., min_length=1)
    dataset: DatasetName = "3DKDavis"
    structure_source: StructureSource = "mmclkin_database"


class AffinityResponse(BaseModel):
    task: Literal["affinity_prediction"] = "affinity_prediction"
    kinase_id: str
    ligand_id: str
    predicted_affinity: float
    unit: str = "pKd_or_model_score"
    model: str = "MMCLKin"
    dataset: str
    structure_source: str
    status: Literal["success"] = "success"
    warnings: list[str] = Field(default_factory=list)


class SelectivityRequest(BaseModel):
    ligand_id: str = Field(..., min_length=1)
    kinase_panel: list[str] = Field(..., min_length=1)
    dataset: DatasetName = "3DKDavis"
    structure_source: StructureSource = "mmclkin_database"


class AffinityProfileItem(BaseModel):
    kinase_id: str
    predicted_affinity: float


class SelectivityMetrics(BaseModel):
    gini: float
    selectivity_entropy: float


class SelectivityResponse(BaseModel):
    task: Literal["selectivity_prediction"] = "selectivity_prediction"
    ligand_id: str
    affinity_profile: list[AffinityProfileItem]
    selectivity_metrics: SelectivityMetrics
    model: str = "MMCLKin"
    dataset: str
    structure_source: str
    status: Literal["success"] = "success"
    warnings: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    message: str
    warnings: list[str] = Field(default_factory=list)
