import logging
from .DataBaseModel import DatabaseModel
from .db_schemas.Neo4jNodes import (
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
    HasMethodRelationship,
    InheritsRelationship,
)


class Neo4jModel(DatabaseModel):

    SCHEMA_QUERIES = [
        "CREATE CONSTRAINT project_id IF NOT EXISTS FOR (n:Project) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT module_id IF NOT EXISTS FOR (n:Module) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT function_id IF NOT EXISTS FOR (n:Function) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT class_id IF NOT EXISTS FOR (n:Class) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT import_id IF NOT EXISTS FOR (n:Import) REQUIRE n.id IS UNIQUE",
    ]

    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.driver = db_client
        self.logger = logging.getLogger(__name__)

    @classmethod
    def create(cls, db_client: object):
        return cls(db_client)

    async def verify_connectivity(self):
        await self.driver.verify_connectivity()

    async def ensure_schema(self):
        for query in self.SCHEMA_QUERIES:
            await self._execute(query, "schema constraint")

    async def _execute(self, query: str, label: str, **params):
        try:
            async with self.driver.session() as session:
                result = await session.run(query, **params)
                await result.consume()
        except Exception as e:
            self.logger.error(f"Error creating {label}: {e}")
            raise RuntimeError(f"Failed to create {label}: {e}")

    async def create_project_node(self, project_node: ProjectNode):
        await self._execute(
            """
            MERGE (p:Project {id: $id})
            SET p.project_hash = $project_hash,
                p.project_path = $project_path,
                p.project_source = $project_source,
                p.name = $name,
                p.num_modules = $num_modules
            """,
            "project node",
            id=project_node.id,
            project_hash=project_node.project_hash,
            project_path=project_node.path,
            project_source=project_node.project_source.value,
            name=project_node.name,
            num_modules=project_node.num_modules,
        )
        return project_node.id

    async def create_modules_batch(self, module_nodes: list[ModuleNode]):
        if not module_nodes:
            return

        await self._execute(
            """
            UNWIND $modules AS module
            MERGE (m:Module {id: module.id})
            SET m.project_hash = module.project_hash,
                m.name = module.name,
                m.file_path = module.file_path,
                m.num_functions = module.num_functions,
                m.num_classes = module.num_classes,
                m.num_imports = module.num_imports
            """,
            "module nodes batch",
            modules=[m.model_dump(mode="json") for m in module_nodes],
        )

    async def create_functions_batch(self, function_nodes: list[FunctionNode]):
        if not function_nodes:
            return

        await self._execute(
            """
            UNWIND $functions AS fn
            MERGE (f:Function {id: fn.id})
            SET f.project_hash = fn.project_hash,
                f.name = fn.name,
                f.full_name = fn.full_name,
                f.module = fn.module
            """,
            "function nodes batch",
            functions=[f.model_dump(mode="json") for f in function_nodes],
        )

    async def create_classes_batch(self, class_nodes: list[ClassNode]):
        if not class_nodes:
            return

        await self._execute(
            """
            UNWIND $classes AS cls
            MERGE (c:Class {id: cls.id})
            SET c.project_hash = cls.project_hash,
                c.name = cls.name,
                c.full_name = cls.full_name,
                c.module = cls.module,
                c.bases = cls.bases
            """,
            "class nodes batch",
            classes=[c.model_dump(mode="json") for c in class_nodes],
        )

    async def create_imports_batch(self, import_nodes: list[ImportNode]):
        if not import_nodes:
            return

        await self._execute(
            """
            UNWIND $imports AS imp
            MERGE (i:Import {id: imp.id})
            SET i.project_hash = imp.project_hash,
                i.module = imp.module,
                i.imported_name = imp.imported_name,
                i.alias = imp.alias,
                i.source_module = imp.source_module
            """,
            "import nodes batch",
            imports=[i.model_dump(mode="json") for i in import_nodes],
        )

    async def create_contains_batch(self, relationships: list[ContainsRelationship]):
        if not relationships:
            return

        await self._execute(
            """
            UNWIND $rels AS rel
            MATCH (a:Project {id: rel.start_id})
            MATCH (b:Module {id: rel.end_id})
            MERGE (a)-[:CONTAINS]->(b)
            """,
            "CONTAINS batch",
            rels=[r.model_dump(mode="json") for r in relationships],
        )

    async def create_defines_batch(self, relationships: list[DefinesRelationship]):
        if not relationships:
            return

        await self._execute(
            """
            UNWIND $rels AS rel
            MATCH (a:Module {id: rel.start_id})
            MATCH (b:Function|Class {id: rel.end_id})
            MERGE (a)-[:DEFINES]->(b)
            """,
            "DEFINES batch",
            rels=[r.model_dump(mode="json") for r in relationships],
        )

    async def create_imports_rel_batch(self, relationships: list[ImportsRelationship]):
        if not relationships:
            return

        await self._execute(
            """
            UNWIND $rels AS rel
            MATCH (a:Module {id: rel.start_id})
            MATCH (b:Import {id: rel.end_id})
            MERGE (a)-[:IMPORTS]->(b)
            """,
            "IMPORTS batch",
            rels=[r.model_dump(mode="json") for r in relationships],
        )

    async def create_calls_batch(self, relationships: list[CallsRelationship]):
        if not relationships:
            return

        await self._execute(
            """
            UNWIND $rels AS rel
            MATCH (a:Function {id: rel.start_id})
            MATCH (b:Function|Class {id: rel.end_id})
            MERGE (a)-[r:CALLS]->(b)
            SET r.confidence = rel.confidence,
                r.source_module = rel.source_module
            """,
            "CALLS batch",
            rels=[r.model_dump(mode="json") for r in relationships],
        )

    async def create_has_method_batch(self, relationships: list[HasMethodRelationship]):
        if not relationships:
            return

        await self._execute(
            """
            UNWIND $rels AS rel
            MATCH (a:Class {id: rel.start_id})
            MATCH (b:Function {id: rel.end_id})
            MERGE (a)-[:HAS_METHOD]->(b)
            """,
            "HAS_METHOD batch",
            rels=[r.model_dump(mode="json") for r in relationships],
        )

    async def create_inherits_batch(self, relationships: list[InheritsRelationship]):
        if not relationships:
            return

        await self._execute(
            """
            UNWIND $rels AS rel
            MATCH (a:Class {id: rel.start_id})
            MATCH (b:Class {id: rel.end_id})
            MERGE (a)-[:INHERITS]->(b)
            """,
            "INHERITS batch",
            rels=[r.model_dump(mode="json") for r in relationships],
        )