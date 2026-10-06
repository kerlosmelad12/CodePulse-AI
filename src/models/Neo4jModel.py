from .DataBaseModel import DatabaseModel
from .db_schemas.Neo4jNodes import (
    ImportNode,
    ProjectNode,
    ModuleNode,
    FunctionNode,
    ClassNode,
    ImportNode,
)
from .db_schemas.Neo4jRelations import (
    ContainsRelationship,
    DefinesRelationship,
    ImportsRelationship,
    CallsRelationship,
)
import logging


class Neo4jModel(DatabaseModel):

    def __init__(self, db_client: object ):
        super().__init__( db_client)
        self.driver = db_client
        self.logger = logging.getLogger(__name__)

    @classmethod
    def create(cls, db_client: object):
        return cls( db_client)

    


    async def create_project_node(self, project_node: ProjectNode):
        try:
            async with self.driver.session() as session:
                await session.run(
                    """
                    MERGE (p:Project {id: $id})
                    SET p.project_hash = $project_hash,
                        p.project_path = $project_path,
                        p.project_source = $project_source,
                        p.name = $name,
                        p.num_modules = $num_modules
                    """,
                    id=project_node.id,
                    project_hash=project_node.project_hash,
                    project_path=project_node.path,
                    project_source=project_node.project_source.value,
                    name=project_node.name,
                    num_modules=project_node.num_modules,
                )

            return project_node.id

        except Exception as e:
            self.logger.error(f"Error creating project node: {e}")
            raise RuntimeError(f"Failed to create project node: {e}")

    async def create_module_node(self, module_node: ModuleNode):
        try:
            async with self.driver.session() as session:
                await session.run(
                    """
                    MERGE (m:Module {id: $id})
                    SET m.project_hash = $project_hash,
                        m.name = $name,
                        m.file_path = $file_path,
                        m.num_functions = $num_functions,
                        m.num_classes = $num_classes,
                        m.num_imports = $num_imports
                    """,
                    id=module_node.id,
                    project_hash=module_node.project_hash,
                    name=module_node.name,
                    file_path=module_node.file_path,
                    num_functions=module_node.num_functions,
                    num_classes=module_node.num_classes,
                    num_imports=module_node.num_imports,
                )

            return module_node.id

        except Exception as e:
            self.logger.error(f"Error creating module node: {e}")
            raise RuntimeError(f"Failed to create module node: {e}")

    async def create_function_node(self, function_node: FunctionNode):
        try:
            async with self.driver.session() as session:
                await session.run(
                    """
                    MERGE (f:Function {id: $id})
                    SET f.project_hash = $project_hash,
                        f.name = $name,
                        f.full_name = $full_name,
                        f.module = $module
                    """,
                    id=function_node.id,
                    project_hash=function_node.project_hash,
                    name=function_node.name,
                    full_name=function_node.full_name,
                    module=function_node.module,
                )

            return function_node.id

        except Exception as e:
            self.logger.error(f"Error creating function node: {e}")
            raise RuntimeError(f"Failed to create function node: {e}")

    async def create_class_node(self, class_node: ClassNode):
        try:
            async with self.driver.session() as session:
                await session.run(
                    """
                    MERGE (c:Class {id: $id})
                    SET c.project_hash = $project_hash,
                        c.name = $name,
                        c.full_name = $full_name,
                        c.module = $module
                    """,
                    id=class_node.id,
                    project_hash=class_node.project_hash,
                    name=class_node.name,
                    full_name=class_node.full_name,
                    module=class_node.module,
                )

            return class_node.id

        except Exception as e:
            self.logger.error(f"Error creating class node: {e}")
            raise RuntimeError(f"Failed to create class node: {e}")
            
    async def create_import_node(self, import_node: ImportNode):
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    """
                    MERGE (i:Import {id: $id})
                    SET i.project_hash = $project_hash,
                        i.module = $module,
                        i.imported_name = $imported_name,
                        i.alias = $alias,
                        i.source_module = $source_module
                    """,
                    id=import_node.id,
                    project_hash=import_node.project_hash,
                    module=import_node.module,
                    imported_name=import_node.imported_name,
                    alias=import_node.alias,
                    source_module=import_node.source_module,
                )

                await result.consume()

        except Exception as e:
            raise RuntimeError(f"Failed to create import node: {e}")



    async def create_contains_relationship(self, relationship: ContainsRelationship):
        try:
            async with self.driver.session() as session:
                await session.run(
                    """
                    MATCH (start {id: $start_id})
                    MATCH (end {id: $end_id})
                    MERGE (start)-[:CONTAINS]->(end)
                    """,
                    start_id=relationship.start_id,
                    end_id=relationship.end_id,
                )

            return relationship

        except Exception as e:
            self.logger.error(
                f"Error creating CONTAINS relationship: {e}"
            )
            raise RuntimeError(
                f"Failed to create CONTAINS relationship: {e}"
            )

    async def create_defines_relationship(self , relationship: DefinesRelationship):
        try:
            async with self.driver.session() as session:
                await session.run(
                    """
                    MATCH (start {id: $start_id})
                    MATCH (end {id: $end_id})
                    MERGE (start)-[:DEFINES]->(end)
                    """,
                    start_id=relationship.start_id,
                    end_id=relationship.end_id,
                )

            return relationship

        except Exception as e:
            self.logger.error(
                f"Error creating DEFINES relationship: {e}"
            )
            raise RuntimeError(
                f"Failed to create DEFINES relationship: {e}"
            )

    async def create_imports_relationship(self, relationship: ImportsRelationship, ):
        try:
            async with self.driver.session() as session:
                await session.run(
                    """
                    MATCH (start {id: $start_id})
                    MATCH (end {id: $end_id})
                    MERGE (start)-[:IMPORTS]->(end)
                    """,
                    start_id=relationship.start_id,
                    end_id=relationship.end_id,
                )

            return relationship

        except Exception as e:
            self.logger.error(
                f"Error creating IMPORTS relationship: {e}"
            )
            raise RuntimeError(
                f"Failed to create IMPORTS relationship: {e}"
            )

    async def create_calls_relationship( self, relationship: CallsRelationship,):
        try:
            async with self.driver.session() as session:
                await session.run(
                    """
                    MATCH (start {id: $start_id})
                    MATCH (end {id: $end_id})
                    MERGE (start)-[r:CALLS]->(end)
                    SET r.confidence = $confidence,
                        r.source_module = $source_module
                    """,
                    start_id=relationship.start_id,
                    end_id=relationship.end_id,
                    confidence=relationship.confidence.value,
                    source_module=relationship.source_module,
                )

            return relationship

        except Exception as e:
            self.logger.error(
                f"Error creating CALLS relationship: {e}"
            )
            raise RuntimeError(
                f"Failed to create CALLS relationship: {e}"
            )

     

    