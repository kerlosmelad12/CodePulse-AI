from pydantic import BaseModel, Field, computed_field
from models.enums.Neo4jEnums import ProjectSource


class ProjectNode(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Name of the project")
    path: str = Field(..., min_length=1, max_length=200, description="Path of the project")
    project_hash: str = Field(..., min_length=1, max_length=100, description="Hash of the project")
    project_source: ProjectSource = Field(..., description="Source of the project")
    num_modules: int = Field(..., ge=0, description="Number of modules in the project")

    @computed_field
    @property
    def id(self) -> str:
        return self.project_hash


class ModuleNode(BaseModel):
    project_hash: str = Field(..., min_length=1, max_length=100, description="Hash of the project")
    name: str = Field(..., min_length=1, max_length=50, description="Name of the module")
    file_path: str = Field(..., min_length=1, max_length=200, description="Path of the module file")
    num_functions: int = Field(..., ge=0, description="Number of functions in the module")
    num_classes: int = Field(..., ge=0, description="Number of classes in the module")
    num_imports: int = Field(..., ge=0, description="Number of imports in the module")

    @computed_field
    @property
    def id(self) -> str:
        return f"{self.project_hash}:{self.name}"


class FunctionNode(BaseModel):
    project_hash: str = Field(..., min_length=1, max_length=100, description="Hash of the project")
    name: str = Field(..., min_length=1, max_length=50, description="Name of the function")
    full_name: str = Field(..., min_length=1, max_length=100, description="Full name of the function")
    module: str = Field(..., min_length=1, max_length=50, description="Name of the module")

    @computed_field
    @property
    def id(self) -> str:
        return f"{self.project_hash}:{self.full_name}"


class ClassNode(BaseModel):
    project_hash: str = Field(..., min_length=1, max_length=100, description="Hash of the project")
    name: str = Field(..., min_length=1, max_length=50, description="Name of the class")
    full_name: str = Field(..., min_length=1, max_length=100, description="Full name of the class")
    module: str = Field(..., min_length=1, max_length=50, description="Name of the module")

    @computed_field
    @property
    def id(self) -> str:
        return f"{self.project_hash}:{self.full_name}"


class PackageNode(BaseModel):
    project_hash: str = Field(..., min_length=1, max_length=100, description="Hash of the project")
    name: str = Field(..., min_length=1, max_length=50, description="Name of the package")

    @computed_field
    @property
    def id(self) -> str:
        return f"{self.project_hash}:{self.name}"