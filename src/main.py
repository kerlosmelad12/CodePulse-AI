from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from neo4j import AsyncGraphDatabase
from routes import base, index
from helper.config import get_settings
from models.Neo4jModel import Neo4jModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_settings = get_settings()
    URI = app_settings.NEO4J_URI
    AUTH = (app_settings.NEO4J_USERNAME, app_settings.NEO4J_PASSWORD)

    driver =  AsyncGraphDatabase.driver(URI, auth=AUTH)
    await driver.verify_connectivity()

    app.state.graphdb = Neo4jModel(db_client=driver)

    yield

    await driver.close()


app = FastAPI(lifespan=lifespan)

app.include_router(base.base_router)
app.include_router(index.index_router)


if __name__ == "__main__":
    uvicorn.run("main:app", port=5000, reload=True,reload_excludes=["assests/projects/*", "assests/projects/**/*"])