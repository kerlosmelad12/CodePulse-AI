import logging
from .DataBaseModel import DatabaseModel
from .db_schemas.Neo4jNode import CodeNode
from .db_schemas.Neo4jRelation import CodeLink

from typing import List



class Neo4jModel(DatabaseModel):

    SCHEMA_QUERIES = [

        "CREATE CONSTRAINT CodeEntity_id IF NOT EXISTS FOR (n:CodeEntity) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT ExternalLibrary_id IF NOT EXISTS FOR (n:ExternalLibrary) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT CodeDocumentation_id IF NOT EXISTS FOR (n:CodeDocumentation) REQUIRE n.id IS UNIQUE"

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


    async def batch_create_nodes(self,nodes: List[CodeNode],batch_size: int = 1000,):
        if not nodes:
            return

        raw_nodes = [
            node.model_dump(mode="json",by_alias=True)
            for node in nodes
        ]

        labels = ["CodeEntity", "ExternalLibrary", "CodeDocumentation"]

        for i in range(0, len(raw_nodes), batch_size):
            chunk = raw_nodes[i:i + batch_size]

            for label in labels:
                sub_chunk = [
                    node
                    for node in chunk
                    if node.get("clean_neo4j_label") == label
                ]

                if not sub_chunk:
                    continue

                await self._execute_nodes_batch(
                    sub_chunk,
                    label,
                )


    async def _execute_nodes_batch(self, batch_data, label):
        query = f"""
        UNWIND $batch AS props
        MERGE (n:{label} {{id: props.id}})
        SET n.name = props.label,
            n.source_file = props.source_file,
            n.source_location = props.source_location,
            n.community = props.community,
            n.file_type = props.file_type,
            n.is_callable = props.is_callable,
            n.is_callable_class = props.is_callable_class
        """

        async with self.driver.session() as session:
            result = await session.run(query, batch=batch_data)
            await result.consume()


    

    async def batch_create_relationships(self,links: List[CodeLink],batch_size: int = 1000,):
        if not links:
            return

        raw_links = [
            link.model_dump(mode="json",by_alias=True)
            for link in links
        ]

        for i in range(0, len(raw_links), batch_size):
            chunk = raw_links[i:i + batch_size]

            distinct_types = {
                link.get("clean_neo4j_type")
                for link in chunk
                if link.get("clean_neo4j_type")
            }

            for rel_type in distinct_types:
                sub_chunk = [
                    link
                    for link in chunk
                    if link.get("clean_neo4j_type") == rel_type
                ]

                if not sub_chunk:
                    continue

                await self._execute_relationships_batch(
                    sub_chunk,
                    rel_type,
                )


    async def _execute_relationships_batch(self, batch_data, rel_type):
        # rel_type comes from the schema's normalized enum/computed field.
        query = f"""
        UNWIND $batch AS props
        MATCH (source {{id: props.source}})
        MATCH (target {{id: props.target}})
        MERGE (source)-[r:{rel_type}]->(target)
        SET r.context = props.context,
            r.source_file = props.source_file,
            r.source_location = props.source_location,
            r.confidence = props.confidence,
            r.confidence_score = props.confidence_score,
            r.weight = props.weight
        """

        async with self.driver.session() as session:
            result = await session.run(query, batch=batch_data)
            await result.consume()

