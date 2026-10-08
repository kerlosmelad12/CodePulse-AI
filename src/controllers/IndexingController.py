import ast
import hashlib
import logging
import os
import shutil
from git import Repo
from .ParsingController import CodeVisitor
from .BaseController import BaseController
from models.Neo4jModel import Neo4jModel
from models.db_schemas.Neo4jNodes import ProjectNode
from utils.indexing import (
    extract_module_node_data,
    walk_project_files,
    extract_function_node_data,
    extract_contains_relationship_data,
    extract_defines_relationship_data,
    extract_imports_relationship_data,
    extract_class_node_data,
    extract_import_node_data,
    extract_calls_relationship_data,
    extract_has_method_relationship_data,
    extract_inherits_relationship_data,
    is_valid_url_syntax,
    check_url_status,
)

logger = logging.getLogger(__name__)


class IndexingController(BaseController):

    def __init__(self):
        super().__init__()

    def _is_remote_url(self, identifier: str) -> bool:
        return is_valid_url_syntax(identifier)

    def _check_url_reachable(self, url: str):
        status = check_url_status(url)
        if "✅" not in status:
            raise ValueError(f"URL is not reachable: {status}")

    def _normalize_identifier(self, identifier: str) -> str:
        if self._is_remote_url(identifier):
            normalized = identifier.strip().lower().rstrip("/")
            if normalized.endswith(".git"):
                normalized = normalized[:-4]
            return normalized
        else:
            if not os.path.exists(identifier):
                raise ValueError(f"Local path does not exist: {identifier}")
            return os.path.realpath(identifier)

    def generate_project_hash(self, project_identifier: str) -> str:
        normalized = self._normalize_identifier(project_identifier)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def clone_url(self, identifier: str, project_dir: str) -> bool:
        try:
            Repo.clone_from(identifier, project_dir)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to clone repository: {e}")

    def create_project_dir(self, project_hash: str) -> tuple[str, bool]:
        project_path = os.path.join(self.projects_dir, project_hash)

        is_valid_existing = self._is_valid_cloned_repo(project_path)

        if not is_valid_existing and os.path.exists(project_path):
            shutil.rmtree(project_path)

        os.makedirs(project_path, exist_ok=True)
        return project_path, is_valid_existing

    def _is_valid_cloned_repo(self, project_path: str) -> bool:
        git_dir = os.path.join(project_path, ".git")
        return os.path.exists(project_path) and os.path.isdir(git_dir)

    def cleanup_project_dir(self, project_path: str):
        shutil.rmtree(project_path, ignore_errors=True)

    def get_module_name(self, filepath: str, project_root: str) -> str:
        rel_path = os.path.relpath(filepath, project_root)
        without_ext = os.path.splitext(rel_path)[0]
        return without_ext.replace(os.sep, ".")

    def extract_file(self, filepath: str, project_root: str) -> dict | None:
        module_name = self.get_module_name(filepath, project_root)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError) as e:
            return {
                "module": module_name,
                "file": filepath,
                "error": str(e),
            }

        visitor = CodeVisitor(module_name)
        visitor.visit(tree)

        return {
            "module": module_name,
            "file": filepath,
            "functions": visitor.functions,
            "classes": visitor.classes,
            "imports": visitor.imports,
            "calls": visitor.calls,
            "methods": visitor.methods,
            "class_bases": visitor.class_bases,
        }

    def extract_project(self, project_path: str) -> list[dict]:
        results = []
        skipped = 0

        for filepath in walk_project_files(project_path):
            result = self.extract_file(filepath, project_path)
            if not result:
                continue
            if "error" in result:
                skipped += 1
                logger.warning(f"Skipped {filepath}: {result['error']}")
                continue
            results.append(result)

        if skipped:
            logger.warning(f"{skipped} file(s) skipped due to parse errors")

        return results

    def get_project_name_from_path(self, project_path: str) -> str:
        name = project_path.rstrip("/\\").replace("\\", "/").split("/")[-1]
        return name[:-4] if name.endswith(".git") else name

    def index_project(self, project_node: ProjectNode, parsing_results: list[dict]):
        project_hash = project_node.project_hash

        module_nodes = extract_module_node_data(project_hash, parsing_results)
        function_nodes = extract_function_node_data(project_hash, parsing_results)
        class_nodes = extract_class_node_data(project_hash, parsing_results)
        import_nodes = extract_import_node_data(project_hash, parsing_results)

        contains_relationships = extract_contains_relationship_data(
            project_node, module_nodes
        )
        defines_relationships = extract_defines_relationship_data(
            module_nodes, function_nodes, class_nodes
        )
        imports_relationships = extract_imports_relationship_data(
            module_nodes, import_nodes
        )
        calls_relationships = extract_calls_relationship_data(
            project_hash, parsing_results
        )
        has_method_relationships = extract_has_method_relationship_data(
            project_hash, parsing_results
        )
        inherits_relationships = extract_inherits_relationship_data(
            project_hash, parsing_results
        )

        return {
            "nodes": {
                "project": project_node,
                "modules": module_nodes,
                "functions": function_nodes,
                "classes": class_nodes,
                "imports": import_nodes,
            },
            "relationships": {
                "contains": contains_relationships,
                "defines": defines_relationships,
                "imports": imports_relationships,
                "calls": calls_relationships,
                "has_method": has_method_relationships,
                "inherits": inherits_relationships,
            },
        }

    async def persist_graph(self, neo4j_model: Neo4jModel, graph_data: dict):
        nodes = graph_data["nodes"]
        relationships = graph_data["relationships"]


        await neo4j_model.create_project_node(nodes["project"])
        await neo4j_model.create_modules_batch(nodes["modules"])
        await neo4j_model.create_functions_batch(nodes["functions"])
        await neo4j_model.create_classes_batch(nodes["classes"])
        await neo4j_model.create_imports_batch(nodes["imports"])

        await neo4j_model.create_contains_batch(relationships["contains"])
        await neo4j_model.create_defines_batch(relationships["defines"])
        await neo4j_model.create_imports_rel_batch(relationships["imports"])
        await neo4j_model.create_has_method_batch(relationships["has_method"])
        await neo4j_model.create_inherits_batch(relationships["inherits"])
        await neo4j_model.create_calls_batch(relationships["calls"])