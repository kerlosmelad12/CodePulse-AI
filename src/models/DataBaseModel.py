from helper.config import get_settings

class DatabaseModel:
    def __init__(self, db_client: object = None):
        self.app_settings = get_settings()
        self.driver = db_client
