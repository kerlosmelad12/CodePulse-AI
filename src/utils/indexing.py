from urllib.parse import urlparse
import requests
import os
from models.db_schemas.Neo4jNodes import (  ProjectNode,ModuleNode,FunctionNode,
                                          ClassNode, ImportNode )
from models.db_schemas.Neo4jRelations import (CallsRelationship, ContainsRelationship, 
                                                  DefinesRelationship, ImportsRelationship)
from models.enums.Neo4jEnums import CallConfidence

IGNORED_DIRS = {".git", "__pycache__", "venv", ".venv", "node_modules"}

def is_valid_url_syntax(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def check_url_status(url):
    try:
        response = requests.get(url, allow_redirects=True, timeout=5, stream=True)
        if response.status_code == 200:
            return f"✅ Active (Status: {response.status_code})"
        else:
            return f"⚠️ Accessible but returned status: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"❌ Unreachable (Error: {e.__class__.__name__})"

def walk_project_files(project_path: str, extensions: tuple = (".py",)):
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
 
        for file in files:
            if file.endswith(extensions) and not file.startswith("__"):
                yield os.path.join(root, file)

def extract_module_node_data( project_hash: str, parsing_results: list[dict] ) -> list[ModuleNode]:

    return [
        ModuleNode(
            project_hash=project_hash,
            name=result["module"],
            file_path=result["file"],
            num_functions=len(result["functions"]),
            num_classes=len(result["classes"]),
            num_imports=len(result["imports"]),
        )
        for result in parsing_results
    ]

def extract_function_node_data(project_hash: str, parsing_results: list[dict]) -> list[FunctionNode]:

    functions = []

    for result in parsing_results:
        for function in result["functions"]:
            functions.append(
                FunctionNode(
                    project_hash=project_hash,
                    name=function,
                    module=result["module"],
                )
            )

    return functions

def extract_class_node_data( project_hash: str,parsing_results: list[dict] ) -> list[ClassNode]:

    classes = []

    for result in parsing_results:
        for class_name in result["classes"]:
            classes.append(
                ClassNode(
                    project_hash=project_hash,
                    name=class_name,
                    module=result["module"],
                )
            )

    return classes

def extract_import_node_data( project_hash: str,parsing_results: list[dict]) -> list[ImportNode]:

    imports = []

    for result in parsing_results:

        for import_data in result["imports"]:

            imports.append(
                ImportNode(
                    project_hash=project_hash,
                    module=result["module"],
                    imported_name=import_data["imported_name"],
                    alias=import_data["alias"],
                    source_module=import_data["source_module"],
                )
            )

    return imports

def extract_contains_relationship_data( project_node: ProjectNode,
                                       module_nodes: list[ModuleNode]) -> list[ContainsRelationship]:

    contains_results = []

    for module in module_nodes:
        contains_results.append(
            ContainsRelationship(
                start_id=project_node.id,
                end_id=module.id
            )
        )

    return contains_results

def extract_defines_relationship_data(module_nodes: list[ModuleNode],
                                      function_nodes: list[FunctionNode],
                                      class_nodes: list[ClassNode],) -> list[DefinesRelationship]:

    defines = []

    module_map = {
        module.name: module
        for module in module_nodes
    }

    for function in function_nodes:
        module = module_map.get(function.module)

        if module:
            defines.append(
                DefinesRelationship(
                    start_id=module.id,
                    end_id=function.id,
                )
            )

    for cls in class_nodes:
        module = module_map.get(cls.module)

        if module:
            defines.append(
                DefinesRelationship(
                    start_id=module.id,
                    end_id=cls.id,
                )
            )

    return defines

def extract_imports_relationship_data(module_nodes: list[ModuleNode],import_nodes: list[ImportNode],) -> list[ImportsRelationship]:

    imports = []

    module_map = {
        module.name: module
        for module in module_nodes
    }

    for import_node in import_nodes:

        module = module_map.get(import_node.module)

        if module:
            imports.append(
                ImportsRelationship(
                    start_id=module.id,
                    end_id=import_node.id,
                )
            )

    return imports

def build_function_id(project_hash: str,full_name: str) -> str:

    module, function_name = full_name.rsplit(".", 1)

    return f"{project_hash}:{module}:{function_name}"


def extract_calls_relationship_data(project_hash: str, parsing_results: list[dict] ) -> list[CallsRelationship]:

    calls = []

    for result in parsing_results:

        for call in result["calls"]:

            caller_id = build_function_id(
                project_hash,
                call["caller"]
            )

            callee_full_name = (
                f"{call['source_module']}.{call['callee']}"
            )

            callee_id = build_function_id(
                project_hash,
                callee_full_name
            )

            calls.append(
                CallsRelationship(
                    start_id=caller_id,
                    end_id=callee_id,
                    confidence=CallConfidence(call["confidence"]),
                    source_module=call["source_module"],
                )
            )

    return calls