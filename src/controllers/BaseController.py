import os
from helper.config import get_settings


class BaseController:

    def __init__(self):
        self.app_settings=get_settings()
        self.base_dir=os.path.dirname(os.path.dirname(__file__))
        self.projects_dir=os.path.join(self.base_dir,"assets/projects")
    
  