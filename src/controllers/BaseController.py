import os
from helper.config import get_settings
from utils.indexing import is_valid_cloned_repo, is_valid_url_syntax,check_url_status

import shutil
class BaseController:

    def __init__(self):
        self.app_settings = get_settings()
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.projects_dir = os.path.join(self.base_dir, "assets/projects")


    def create_project_dir(self, project_hash: str) -> tuple[str, bool]:
        project_path = os.path.join(self.projects_dir, project_hash)

        is_valid_existing = is_valid_cloned_repo(project_path)

        if not is_valid_existing and os.path.exists(project_path):
            self.cleanup_project_dir(project_path)

        os.makedirs(project_path, exist_ok=True)
        return project_path, is_valid_existing
    

    def cleanup_project_dir(self, project_path: str):
        shutil.rmtree(project_path, ignore_errors=True)


    def check_url(self,url):
        if is_valid_url_syntax(url) and check_url_status(url):
            return True
        return False

    

