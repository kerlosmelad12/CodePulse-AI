from typing import Optional
from pydantic import BaseModel, Field, computed_field
from ..enums.RelationEnums import RelationType

class ChunkLink(BaseModel):
    source: str = Field(..., description="The unique source CodeNode ID (e.g., function or class ID).")
    target: str = Field(..., description="The unique target CodeChunk node_id.")
    relation: RelationType = Field(RelationType.HAS_CODE, description="The structural dependency relation, defaults to HAS_CODE.")
    source_file: Optional[str] = Field(None, description="Path to the file where this chunk resides.")
    
    @computed_field
    @property
    def clean_neo4j_type(self) -> str:
        """Dynamically normalizes the relation enum to standard UPPERCASE notation for Neo4j."""
        return self.relation.value.upper()

    model_config = {
        "populate_by_name": True  
    }