from typing import Literal
from pydantic import BaseModel, Field


class ClassificationResult(BaseModel):
    verdict: Literal["allowed", "borderline", "violating"]
    confidence_score: float = Field(ge=0.0, le=1.0)
    cited_sections: list[str] = Field(min_length=1)
    reasoning: str
