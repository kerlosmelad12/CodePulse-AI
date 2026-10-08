from pydantic import BaseModel, Field
from models.enums.Neo4jEnums import RelationType, CallConfidence


class BaseRelationship(BaseModel):

    start_id: str = Field(..., min_length=1, description="ID of the start node")
    end_id: str = Field(..., min_length=1, description="ID of the end node")
    relation_type: RelationType = Field(..., description="Type of the relationship")


class DefinesRelationship(BaseRelationship):
    relation_type: RelationType = Field(default=RelationType.DEFINES, frozen=True)


class ImportsRelationship(BaseRelationship):
    relation_type: RelationType = Field(default=RelationType.IMPORTS, frozen=True)


class ContainsRelationship(BaseRelationship):
    relation_type: RelationType = Field(default=RelationType.CONTAINS, frozen=True)


class CallsRelationship(BaseRelationship):

    relation_type: RelationType = Field(default=RelationType.CALLS, frozen=True)
    confidence: CallConfidence = Field(..., description="Confidence level of this call relationship")
    source_module: str = Field(..., min_length=1, max_length=100, description="Module the callee is believed to come from")

class HasMethodRelationship(BaseRelationship):
    relation_type: RelationType = Field(default=RelationType.HAS_METHOD, frozen=True)


class InheritsRelationship(BaseRelationship):
    relation_type: RelationType = Field(default=RelationType.INHERITS, frozen=True)