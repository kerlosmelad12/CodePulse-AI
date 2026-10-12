from typing import Optional
from pydantic import BaseModel, Field, computed_field
from ..enums.RelationEnums import RelationType,LinkContext

class CodeLink(BaseModel):
    source: str = Field(..., description="The unique source node ID where the relationship vector initiates.")
    target: str = Field(..., description="The unique target destination node ID where the vector arrow points.")
    relation: RelationType = Field(..., description="The strict underlying structural dependency category enum.")

    context: Optional[LinkContext] = Field(None, description="The technical software engineering scope context block.")
    source_file: Optional[str] = Field(None, description="Path to the file where this connection is physically typed.")
    source_location: Optional[str] = Field(None, description="Precise row or line notation anchor within the file (e.g., L15).")
    confidence: str = Field("EXTRACTED", description="The data extraction mechanism category string indicator.")
    confidence_score: float = Field(1.0, description="The precision rating float calculation from the engine parsing engine.")
    weight: float = Field(1, description="The traffic connection impact multiplier value for clustering analytics.")
    origin: str = Field("ast", alias="_origin", description="Underlying parser architecture used to map this edge link.")

    @computed_field
    @property
    def clean_neo4j_type(self) -> str:
        """Dynamically normalizes structural string enums to standard UPPERCASE notation for Neo4j architecture optimization."""
        return self.relation.value.upper()

    model_config = {
        "populate_by_name": True  # Seamlessly maps internal underscore JSON keys directly to Pythonic field models
    }


