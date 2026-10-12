from typing import Optional
from pydantic import BaseModel, Field, computed_field
from ..enums.NodeEnums import FileType,DataOrigin


class CodeNode(BaseModel):
    # --- Mandatory / Core Fields ---
    id: str = Field(...,description="The globally unique identification string mapped from file paths and code signatures.")
    label: str = Field(..., description="The human-readable display name of the artifact (e.g., Class or Function name).")
    file_type: FileType = Field(...,  description="Categorizes the node type using the strict FileType enum." )

    source_file: Optional[str] = Field(None, description="Relative system path to the physical physical file containing this logic.")
    source_location: Optional[str] = Field(None, description="The precise row anchor or line number notation prefix where the code block opens (e.g., L12).")
    community: int = Field(0, description="The topological cluster neighborhood grouping integer processed by graph algorithms.")
    origin: DataOrigin = Field(DataOrigin.AST, alias="_origin",description="Underlying source mechanism used to detect this element.")
    is_callable: bool = Field( False,  alias="_callable",  description="Boolean state confirming whether this node can be programmatically invoked as an engine execution unit." )
    is_callable_class: bool = Field(False, alias="_callable_class", description="Boolean state confirming whether this node functions as an object-oriented constructor factory.")

    @computed_field
    @property
    def clean_neo4j_label(self) -> str:
        """
        Dynamically yields structural classification routing strings for Neo4j database optimization layers.
        Maps external framework ecosystems separately from localized codebase repositories.
        """
        if self.file_type == FileType.CONCEPT:
            return "ExternalLibrary"
        if self.file_type == FileType.RATIONALE:
            return "CodeDocumentation"
        return "CodeEntity"

    model_config = {
        "populate_by_name": True  
    }



