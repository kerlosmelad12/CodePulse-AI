from pydantic import BaseModel, Field, computed_field
from models.enums.Neo4jEnums import ProjectSource


class ProjectNode(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Name of the project")
    path: str = Field(..., min_length=1, max_length=500, description="Path of the project")
    project_hash: str = Field(..., min_length=1, max_length=100, description="Hash of the project")
    project_source: ProjectSource = Field(..., description="Source of the project")
    num_modules: int = Field(..., ge=0, description="Number of modules in the project")

    @computed_field
    @property
    def id(self) -> str:
        return self.project_hash


class ModuleNode(BaseModel):
    project_hash: str = Field(..., min_length=1, max_length=100, description="Hash of the project")
    name: str = Field(..., min_length=1, max_length=200, description="Name of the module")
    file_path: str = Field(..., min_length=1, max_length=500, description="Path of the module file")
    num_functions: int = Field(..., ge=0, description="Number of functions in the module")
    num_classes: int = Field(..., ge=0, description="Number of classes in the module")
    num_imports: int = Field(..., ge=0, description="Number of imports in the module")

    @computed_field
    @property
    def id(self) -> str:
        return f"{self.project_hash}:{self.name}"


class FunctionNode(BaseModel):
    project_hash: str = Field(..., min_length=1, max_length=100, description="Hash of the project")
    name: str = Field(..., min_length=1, max_length=200, description="Name of the function")
    module: str = Field(..., min_length=1, max_length=200, description="Name of the module")

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.module}.{self.name}"

    @computed_field
    @property
    def id(self) -> str:
        return f"{self.project_hash}:{self.module}:{self.name}"


class ClassNode(BaseModel):
    project_hash: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    module: str = Field(..., min_length=1, max_length=100)
    bases: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.module}.{self.name}"

    @computed_field
    @property
    def id(self) -> str:
        return f"{self.project_hash}:{self.module}:{self.name}"


class ImportNode(BaseModel):
    project_hash: str = Field(..., min_length=1, max_length=100)
    module: str = Field(..., min_length=1, max_length=200)
    imported_name: str = Field(..., min_length=1, max_length=200)
    alias: str | None = Field(default=None, max_length=200)
    source_module: str = Field(..., min_length=1, max_length=200)

    @computed_field
    @property
    def id(self) -> str:
        return (
            f"{self.project_hash}:import:{self.module}:"
            f"{self.source_module}:{self.imported_name}"
        )