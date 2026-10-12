from typing import Optional
from pydantic import BaseModel, Field, computed_field
from ..enums.NodeEnums import FileType,DataOrigin,ProjectSource


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






# class ProjectNode(BaseModel):
#     name: str = Field(..., min_length=1, max_length=200, description="Name of the project")
#     path: str = Field(..., min_length=1, max_length=500, description="Path of the project")
#     project_hash: str = Field(..., min_length=1, max_length=100, description="Hash of the project")
#     project_source: ProjectSource = Field(..., description="Source of the project")
#     num_modules: int = Field(..., ge=0, description="Number of modules in the project")

#     @computed_field
#     @property
#     def id(self) -> str:
#         return self.project_hash


# class ModuleNode(BaseModel):
#     project_hash: str = Field(..., min_length=1, max_length=100, description="Hash of the project")
#     name: str = Field(..., min_length=1, max_length=200, description="Name of the module")
#     file_path: str = Field(..., min_length=1, max_length=500, description="Path of the module file")
#     num_functions: int = Field(..., ge=0, description="Number of functions in the module")
#     num_classes: int = Field(..., ge=0, description="Number of classes in the module")
#     num_imports: int = Field(..., ge=0, description="Number of imports in the module")

#     @computed_field
#     @property
#     def id(self) -> str:
#         return f"{self.project_hash}:{self.name}"


# class FunctionNode(BaseModel):
#     project_hash: str = Field(..., min_length=1, max_length=100, description="Hash of the project")
#     name: str = Field(..., min_length=1, max_length=200, description="Name of the function")
#     module: str = Field(..., min_length=1, max_length=200, description="Name of the module")

#     @computed_field
#     @property
#     def full_name(self) -> str:
#         return f"{self.module}.{self.name}"

#     @computed_field
#     @property
#     def id(self) -> str:
#         return f"{self.project_hash}:{self.module}:{self.name}"


# class ClassNode(BaseModel):
#     project_hash: str = Field(..., min_length=1, max_length=100)
#     name: str = Field(..., min_length=1, max_length=100)
#     module: str = Field(..., min_length=1, max_length=100)
#     bases: list[str] = Field(default_factory=list)

#     @computed_field
#     @property
#     def full_name(self) -> str:
#         return f"{self.module}.{self.name}"

#     @computed_field
#     @property
#     def id(self) -> str:
#         return f"{self.project_hash}:{self.module}:{self.name}"


# class ImportNode(BaseModel):
#     project_hash: str = Field(..., min_length=1, max_length=100)
#     module: str = Field(..., min_length=1, max_length=200)
#     imported_name: str = Field(..., min_length=1, max_length=200)
#     alias: str | None = Field(default=None, max_length=200)
#     source_module: str = Field(..., min_length=1, max_length=200)

#     @computed_field
#     @property
#     def id(self) -> str:
#         return (
#             f"{self.project_hash}:import:{self.module}:"
#             f"{self.source_module}:{self.imported_name}"
#         )