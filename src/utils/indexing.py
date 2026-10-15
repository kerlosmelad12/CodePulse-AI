from urllib.parse import urlparse
import requests
import os
import hashlib
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
            return True         
        else:
            return False
    except requests.exceptions.RequestException as e:
        return f"Unreachable (Error: {e.__class__.__name__})"


def normalize_identifier(identifier: str) -> str:
        if is_valid_url_syntax(identifier):
            normalized = identifier.strip().lower().rstrip("/")
            if normalized.endswith(".git"):
                normalized = normalized[:-4]
        return normalized


def is_valid_cloned_repo(project_path: str) -> bool:
        git_dir = os.path.join(project_path, ".git")
        return os.path.exists(project_path) and os.path.isdir(git_dir)


def generate_project_hash(self, project_identifier: str) -> str:
        normalized = self.normalize_identifier(project_identifier)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]



def walk_project_files(project_path: str, extensions: tuple = (".py",)):
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for file in files:
            if file.endswith(extensions) and not file.startswith("__"):
                yield os.path.join(root, file)


