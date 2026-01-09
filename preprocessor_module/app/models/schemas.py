from pydantic import BaseModel, Field


class PreprocessResponse(BaseModel):
    row_count: int = Field(..., description="Number of rows processed")
    feature_count: int = Field(..., description="Number of features per row")
    features: list[list[float]] = Field(
        ..., description="Scaled feature vectors (row_count x feature_count)"
    )
    feature_names: list[str] = Field(..., description="Ordered feature column names")
    labels: list[str] | None = Field(
        None, description="Original labels if present in the CSV"
    )


class HealthResponse(BaseModel):
    status: str
    service: str
    scaler_loaded: bool
