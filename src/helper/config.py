from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    APP_VERSION:str
    APP_NAME:str

    NEO4J_PASSWORD:str
    NEO4J_URI:str
    NEO4J_USERNAME:str
    
    


    model_config = SettingsConfigDict(env_file=".env")


def get_settings():
    return Settings()