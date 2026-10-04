import hashlib
import os
import shutil
from .BaseController import BaseController
from utils.indexing import is_valid_url_syntax, check_url_status
from git import Repo


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