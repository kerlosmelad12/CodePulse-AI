import re
from typing import Optional
from pydantic import BaseModel, Field, computed_field

class CodeChunk(BaseModel):
    project_hash: str = Field(..., min_length=1, max_length=100)
    file_path: str = Field(..., min_length=1, max_length=500)
    language: str = Field(..., min_length=1, max_length=30)
    chunk_type: str = Field(..., min_length=1, max_length=100)
    name: Optional[str] = Field(None, max_length=300)
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    text: str = Field(..., min_length=1)
    file_hash: str = Field(..., min_length=64, max_length=64)
    node_id: str = Field(None)


    @computed_field
    @property
    def create_neo4j_chunk_type(self) -> str:
        # Sanitize chunk type into a safe Neo4j label uppercase string
        cleaned = re.sub(r'[^A-Z0-9_]', '_', str(self.chunk_type).upper())
        if not cleaned or not cleaned[0].isalpha():
            return "CODE_CHUNK"
        return cleaned