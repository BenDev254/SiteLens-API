from typing import Optional, List, Any, Dict
from pydantic import BaseModel
from datetime import datetime


class FLExperimentCreate(BaseModel):
    name: str
    params: Optional[Dict[str, Any]] = None
    participant_threshold: int = 3


class FLExperimentRead(BaseModel):
    id: int
    name: str
    params: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, Any]] = None
    created_at: datetime


class JoinExperimentRequest(BaseModel):
    experiment_id: int


class JoinExperimentResponse(BaseModel):
    experiment_id: int
    participant_id: int
    joined_at: datetime


class WeightsUploadRequest(BaseModel):
    experiment_id: int
    weights: Optional[List[float]] = None
    storage_key: Optional[str] = None


class WeightsUploadResponse(BaseModel):
    upload_id: int
    experiment_id: int
    uploader_id: Optional[int]
    created_at: datetime


class AggregationStatus(BaseModel):
    experiment_id: int
    aggregated: bool
    version: int
    details: Optional[Dict[str, Any]] = None


class LocalTrainingRequest(BaseModel):
    experiment_id: int
    project_id: int


class LocalTrainingResponse(BaseModel):
    experiment_id: int
    project_id: int
    trained_round: int
    uploaded_weights: Dict[str, float]





# -------------------------
# Global Model
# -------------------------
class GlobalModelRead(BaseModel):
    experiment_id: int
    round: int
    weights: Dict[str, Any]




# -------------------------
# Aggregation
# -------------------------
class AggregateResponse(BaseModel):
    experiment_id: int
    new_round: int
    aggregated_weights: Dict[str, Any]
