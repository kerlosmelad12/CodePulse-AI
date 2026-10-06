import ast
import hashlib
import os
import shutil
from .ParsingController import CodeVisitor
from .BaseController import BaseController
from git import Repo
from models.Neo4jModel import Neo4jModel
from utils.indexing import (extract_module_node_data,walk_project_files,
                             extract_function_node_data,extract_contains_relationship_data,
                             extract_defines_relationship_data,extract_imports_relationship_data,
                            extract_class_node_data,extract_import_node_data,extract_calls_relationship_data,
                                 is_valid_url_syntax,check_url_status)
from models.db_schemas.Neo4jNodes import ProjectNode


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
            normalized = identifier.strip().lower().rstrip('/')
            if normalized.endswith('.git'):
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
                "error": str(e)
            }
    
        visitor = CodeVisitor(module_name)
        visitor.visit(tree)
    
        return {
            "module": module_name,
            "file": filepath,
            "functions": visitor.functions,
            "classes": visitor.classes,
            "imports": visitor.imports,
            "calls": visitor.calls
        }
    

    
    def extract_project(self, project_path: str) -> list[dict]:
        results = []
        for filepath in walk_project_files(project_path):
            result = self.extract_file(filepath, project_path)
            if result:
                results.append(result)
        return results

    def get_project_name_from_path(self, project_path: str) -> str:
        return project_path.split(os.sep)[-1] if os.sep in project_path else project_path


    def index_project( self, project_node: ProjectNode, parsing_results: list[dict],):

        project_hash = project_node.project_hash


        module_nodes = extract_module_node_data(project_hash,parsing_results)

        function_nodes = extract_function_node_data(project_hash , parsing_results)

        class_nodes = extract_class_node_data(
            project_hash,
            parsing_results,
        )

        import_nodes = extract_import_node_data(
            project_hash,
            parsing_results,
        )


        contains_relationships = extract_contains_relationship_data(
            project_node,
            module_nodes,
        )

        defines_relationships = extract_defines_relationship_data(
            module_nodes,
            function_nodes,
            class_nodes,
        )

        imports_relationships = extract_imports_relationship_data(
            module_nodes,
            import_nodes,
        )

        calls_relationships = extract_calls_relationship_data(
            project_hash,
            parsing_results,
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
            },
        }