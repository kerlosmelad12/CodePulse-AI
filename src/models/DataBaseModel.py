from helper.config import get_settings

class DatabaseModel:
    def __init__(self, driver: object = None):
        self.app_settings = get_settings()
        self.driver = driver
