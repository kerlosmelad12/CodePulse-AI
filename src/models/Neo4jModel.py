import logging
import re
from typing import Any, Dict, List, Union

from pydantic import BaseModel

from .DataBaseModel import DatabaseModel
from .db_schemas.ChunkDataNode import CodeChunk
from .db_schemas.ChunkRelation import ChunkLink
from .db_schemas.Neo4jNode import CodeNode
from .db_schemas.Neo4jRelation import CodeLink

NODE_LABELS = ("CodeEntity", "ExternalLibrary", "CodeDocumentation")
REL_TYPE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,59}$")
CHUNK_LABEL_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,99}$")


class Neo4jModel(DatabaseModel):

    SCHEMA_QUERIES = [
        "CREATE CONSTRAINT CodeNode_id IF NOT EXISTS FOR (n:CodeNode) REQUIRE n.id IS UNIQUE",
        "CREATE INDEX CodeNode_project IF NOT EXISTS FOR (n:CodeNode) ON (n.project_hash)",
        "CREATE INDEX CodeNode_name IF NOT EXISTS FOR (n:CodeNode) ON (n.name)",

        "CREATE CONSTRAINT CodeChunk_node_id IF NOT EXISTS FOR (n:CodeChunk) REQUIRE n.node_id IS UNIQUE",
        "CREATE INDEX CodeChunk_project IF NOT EXISTS FOR (n:CodeChunk) ON (n.project_hash)",
        "CREATE INDEX CodeChunk_file_path IF NOT EXISTS FOR (n:CodeChunk) ON (n.file_path)",
        "CREATE INDEX chunk_file_line IF NOT EXISTS FOR (c:CodeChunk) ON (c.project_hash, c.file_path, c.start_line)",

        "CREATE CONSTRAINT Project_hash IF NOT EXISTS FOR (p:Project) REQUIRE p.project_hash IS UNIQUE",
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

    async def _run_batch(self, query: str, batch: list[dict]):

        async def work(tx):
            result = await tx.run(query, batch=batch)
            return await result.consume()

        async with self.driver.session() as session:
            summary = await session.execute_write(work)

        return summary.counters

    # ------------------------------------------------------------------
    # Chunk nodes
    # ------------------------------------------------------------------
    async def batch_create_ChunkNode(
        self,
        nodes: List[Union[CodeChunk, Dict[str, Any]]],
        batch_size: int = 5000,
    ) -> dict:
        stats = {"received": len(nodes), "created": 0, "unknown_label": 0}
        if not nodes:
            return stats

        by_label: dict[str, list[dict]] = {}
        for node in nodes:
            if isinstance(node, BaseModel):
                raw = node.model_dump(mode="json", by_alias=True)
            elif isinstance(node, dict):
                raw = node
            else:
                continue

            label = raw.get("create_neo4j_chunk_type")

            # label بيتحط في الـ query كـ string، فلازم نتأكد إنه آمن
            if not label or not CHUNK_LABEL_PATTERN.match(label):
                stats["unknown_label"] += 1
                label = "CODE_CHUNK"

            by_label.setdefault(label, []).append(raw)

        for label, items in by_label.items():
            for i in range(0, len(items), batch_size):
                counters = await self._execute_code_nodes_batch(items[i:i + batch_size], label)
                stats["created"] += counters.nodes_created

        return stats

    async def _execute_code_nodes_batch(self, batch_data: list[dict], label: str):
        query = f"""
        UNWIND $batch AS props
        MERGE (n:CodeChunk {{node_id: props.node_id}})
        SET n:`{label}`
        SET n.project_hash = props.project_hash,
            n.file_path = props.file_path,
            n.language = props.language,
            n.chunk_type = props.chunk_type,
            n.name = props.name,
            n.start_line = props.start_line,
            n.end_line = props.end_line,
            n.text = props.text,
            n.file_hash = props.file_hash
        """
        return await self._run_batch(query, batch_data)

    # ------------------------------------------------------------------
    # Chunk links  (CodeNode -[:HAS_CHUNK]-> CodeChunk)
    # بديل merge_nodes_and_chunks القديمة اللي كانت بتربط بالـ line number
    # ------------------------------------------------------------------
    async def batch_create_chunk_links(
        self,
        links: List[Union[ChunkLink, Dict[str, Any]]],
        batch_size: int = 5000,
    ) -> dict:
        stats = {"received": len(links), "created": 0, "skipped_bad_type": 0}
        if not links:
            return stats

        by_type: dict[str, list[dict]] = {}
        for link in links:
            if isinstance(link, BaseModel):
                raw = link.model_dump(mode="json", by_alias=True)
            elif isinstance(link, dict):
                raw = link
            else:
                continue

            rel_type = raw.get("clean_neo4j_type")
            if not rel_type or not REL_TYPE_PATTERN.match(rel_type):
                stats["skipped_bad_type"] += 1
                continue

            by_type.setdefault(rel_type, []).append(raw)

        for rel_type, items in by_type.items():
            for i in range(0, len(items), batch_size):
                counters = await self._execute_chunk_links_batch(items[i:i + batch_size], rel_type)
                stats["created"] += counters.relationships_created

        return stats

    async def _execute_chunk_links_batch(self, batch_data: list[dict], rel_type: str):
        # لازم الـ nodes والـ chunks يكونوا اتكتبوا قبل ما نستدعي الدالة دي
        query = f"""
        UNWIND $batch AS props
        MATCH (source:CodeNode {{id: props.source}})
        MATCH (target:CodeChunk {{node_id: props.target}})
        MERGE (source)-[r:`{rel_type}`]->(target)
        SET r.source_file = props.source_file
        """
        return await self._run_batch(query, batch_data)

    # ------------------------------------------------------------------
    # Code nodes
    # ------------------------------------------------------------------
    async def batch_create_nodes(self, nodes: List[CodeNode], batch_size: int = 5000) -> dict:
        stats = {"received": len(nodes), "created": 0, "unknown_label": 0}
        if not nodes:
            return stats

        by_label: dict[str, list[dict]] = {}
        for node in nodes:
            raw = node.model_dump(mode="json", by_alias=True)
            label = raw.get("clean_neo4j_label")

            if label not in NODE_LABELS:
                label = "CodeEntity"
                stats["unknown_label"] += 1

            by_label.setdefault(label, []).append(raw)

        for label, items in by_label.items():
            for i in range(0, len(items), batch_size):
                counters = await self._execute_nodes_batch(items[i:i + batch_size], label)
                stats["created"] += counters.nodes_created

        return stats

    async def _execute_nodes_batch(self, batch_data: list[dict], label: str):
        query = f"""
        UNWIND $batch AS props
        MERGE (n:CodeNode {{id: props.id}})
        SET n:{label}
        SET n.project_hash = props.project_hash,
            n.name = props.label,
            n.source_file = props.source_file,
            n.source_location = props.source_location,
            n.community = props.community,
            n.file_type = props.file_type,
            n.is_callable = props.is_callable,
            n.is_callable_class = props.is_callable_class,
            n.file_path = props.file_path
        """
        return await self._run_batch(query, batch_data)

    # ------------------------------------------------------------------
    # Relationships between code nodes
    # ------------------------------------------------------------------
    async def batch_create_relationships(self, links: List[CodeLink], batch_size: int = 5000) -> dict:
        stats = {"received": len(links), "created": 0, "skipped_bad_type": 0}
        if not links:
            return stats

        by_type: dict[str, list[dict]] = {}
        for link in links:
            raw = link.model_dump(mode="json", by_alias=True)
            rel_type = raw.get("clean_neo4j_type")

            if not rel_type or not REL_TYPE_PATTERN.match(rel_type):
                stats["skipped_bad_type"] += 1
                continue

            by_type.setdefault(rel_type, []).append(raw)

        for rel_type, items in by_type.items():
            for i in range(0, len(items), batch_size):
                counters = await self._execute_relationships_batch(items[i:i + batch_size], rel_type)
                stats["created"] += counters.relationships_created

        return stats

    async def _execute_relationships_batch(self, batch_data: list[dict], rel_type: str):
        query = f"""
        UNWIND $batch AS props
        MATCH (source:CodeNode {{id: props.source}})
        MATCH (target:CodeNode {{id: props.target}})
        MERGE (source)-[r:`{rel_type}`]->(target)
        SET r.context = props.context,
            r.source_file = props.source_file,
            r.source_location = props.source_location,
            r.confidence = props.confidence,
            r.confidence_score = props.confidence_score,
            r.weight = props.weight
        """
        return await self._run_batch(query, batch_data)

    # ------------------------------------------------------------------
    # Project helpers
    # ------------------------------------------------------------------
    async def project_has_graph(self, project_hash: str) -> bool:
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    "RETURN EXISTS { MATCH (n:CodeNode {project_hash: $project_hash}) } AS found",
                    project_hash=project_hash,
                )
                record = await result.single()
                return bool(record and record["found"])
        except Exception as e:
            self.logger.error(f"Error checking project graph: {e}")
            raise RuntimeError(f"Failed to check project graph: {e}")

    async def save_project_meta(self, project_hash: str, repo_url: str, branch: str | None, commit: str | None):
        """بيسجّل الـ branch والـ commit اللي الـ graph اتعمل منهم."""
        await self._execute(
            """
            MERGE (p:Project {project_hash: $project_hash})
            SET p.repo_url = $repo_url,
                p.indexed_branch = $branch,
                p.indexed_commit = $commit,
                p.indexed_at = datetime()
            """,
            "project metadata",
            project_hash=project_hash,
            repo_url=repo_url,
            branch=branch,
            commit=commit,
        )

    async def get_project_meta(self, project_hash: str) -> dict | None:
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    """
                    MATCH (p:Project {project_hash: $project_hash})
                    RETURN p.repo_url AS repo_url,
                           p.indexed_branch AS indexed_branch,
                           p.indexed_commit AS indexed_commit
                    """,
                    project_hash=project_hash,
                )
                record = await result.single()
                return dict(record) if record else None
        except Exception as e:
            self.logger.error(f"Error reading project metadata: {e}")
            raise RuntimeError(f"Failed to read project metadata: {e}")

    async def delete_project(self, project_hash: str):
        # الـ chunks الأول، لأن القديم كان بيمسح CodeNode بس وبيسيب الـ chunks يتيمة
        await self._execute(
            "MATCH (c:CodeChunk {project_hash: $project_hash}) DETACH DELETE c",
            "project chunks cleanup",
            project_hash=project_hash,
        )
        await self._execute(
            "MATCH (n:CodeNode {project_hash: $project_hash}) DETACH DELETE n",
            "project cleanup",
            project_hash=project_hash,
        )
        await self._execute(
            "MATCH (p:Project {project_hash: $project_hash}) DETACH DELETE p",
            "project metadata cleanup",
            project_hash=project_hash,
        )