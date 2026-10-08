from urllib.parse import urlparse
import requests
import os
from models.db_schemas.Neo4jNodes import (
    ProjectNode,
    ModuleNode,
    FunctionNode,
    ClassNode,
    ImportNode,
)
from models.db_schemas.Neo4jRelations import (
    CallsRelationship,
    ContainsRelationship,
    DefinesRelationship,
    ImportsRelationship,
    HasMethodRelationship,
    InheritsRelationship,
)
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


def extract_module_node_data(project_hash: str, parsing_results: list[dict]) -> list[ModuleNode]:
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


def extract_class_node_data( project_hash: str, parsing_results: list[dict],) -> list[ClassNode]:

    classes = []

    for result in parsing_results:
        for class_name in result["classes"]:
            classes.append(
                ClassNode(
                    project_hash=project_hash,
                    name=class_name,
                    module=result["module"],
                    bases=result["class_bases"].get(class_name, []),
                )
            )

    return classes


def extract_import_node_data(project_hash: str, parsing_results: list[dict]) -> list[ImportNode]:
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


def extract_contains_relationship_data(
    project_node: ProjectNode,
    module_nodes: list[ModuleNode],
) -> list[ContainsRelationship]:
    return [
        ContainsRelationship(start_id=project_node.id, end_id=module.id)
        for module in module_nodes
    ]


def extract_defines_relationship_data(
    module_nodes: list[ModuleNode],
    function_nodes: list[FunctionNode],
    class_nodes: list[ClassNode],
) -> list[DefinesRelationship]:
    defines = []

    module_map = {module.name: module for module in module_nodes}

    for function in function_nodes:
        module = module_map.get(function.module)
        if module:
            defines.append(DefinesRelationship(start_id=module.id, end_id=function.id))

    for cls in class_nodes:
        module = module_map.get(cls.module)
        if module:
            defines.append(DefinesRelationship(start_id=module.id, end_id=cls.id))

    return defines


def extract_imports_relationship_data(
    module_nodes: list[ModuleNode],
    import_nodes: list[ImportNode],
) -> list[ImportsRelationship]:
    imports = []

    module_map = {module.name: module for module in module_nodes}

    for import_node in import_nodes:
        module = module_map.get(import_node.module)
        if module:
            imports.append(ImportsRelationship(start_id=module.id, end_id=import_node.id))

    return imports


def build_node_id(project_hash: str, module: str, name: str) -> str:
    return f"{project_hash}:{module}:{name}"



def extract_calls_relationship_data(
    project_hash: str,
    parsing_results: list[dict],
) -> list[CallsRelationship]:
    calls = []

    for result in parsing_results:
        for call in result["calls"]:
            caller_id = build_node_id(project_hash, result["module"], call["caller"])
            callee_id = build_node_id(project_hash, call["source_module"], call["callee"])

            calls.append(
                CallsRelationship(
                    start_id=caller_id,
                    end_id=callee_id,
                    confidence=CallConfidence(call["confidence"]),
                    source_module=call["source_module"],
                )
            )

    return calls


def extract_has_method_relationship_data(project_hash: str,parsing_results: list[dict],) -> list[HasMethodRelationship]:
    relationships = []

    for result in parsing_results:
        module = result["module"]
        for method in result["methods"]:
            relationships.append(
                HasMethodRelationship(
                    start_id=build_node_id(project_hash, module, method["class"]),
                    end_id=build_node_id(project_hash, module, method["method"]),
                )
            )

    return relationships


def extract_inherits_relationship_data(project_hash: str,parsing_results: list[dict],) -> list[InheritsRelationship]:

    relationships = []
    # Class name -> module
    class_index = {}

    for result in parsing_results:
        module = result["module"]

        for class_name in result["classes"]:
            class_index[class_name] = module

    for result in parsing_results:
        module = result["module"]

        import_lookup = {
            (imp["alias"] or imp["imported_name"]): (
                imp["source_module"],
                imp["imported_name"],
            )
            for imp in result["imports"]
        }

        for class_name, bases in result["class_bases"].items():

            for base in bases:

                # 1. Class defined in the same module
                if base in result["classes"]:
                    target_module = module
                    target_name = base

                # 2. Imported class
                elif base in import_lookup:
                    target_module, target_name = import_lookup[base]

                # 3. Class defined somewhere else in this project
                elif base in class_index:
                    target_module = class_index[base]
                    target_name = base

                # 4. External class / unresolved
                else:
                    continue

                relationships.append(
                    InheritsRelationship(
                        start_id=(
                            build_node_id(project_hash,module,class_name)
                        ),
                        end_id=(
                            build_node_id(project_hash,target_module,target_name)
                        ),
                    )
                )

    return relationships