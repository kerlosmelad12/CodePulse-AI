from urllib.parse import urlparse
import requests
import os
from models.db_schemas.Neo4jNodes import (
    ProjectNode,
    ModuleNode,
    FunctionNode,
    ClassNode,
    PackageNode,
)

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

