from contextlib import asynccontextmanager
from fastapi import FastAPI
from neo4j import AsyncGraphDatabase
import uvicorn

from routes import base, index
from helper.config import get_settings
from models.Neo4jModel import Neo4jModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_settings = get_settings()

    driver = AsyncGraphDatabase.driver(
        app_settings.NEO4J_URI,
        auth=(app_settings.NEO4J_USERNAME, app_settings.NEO4J_PASSWORD),
    )
    await driver.verify_connectivity()

    graphdb = Neo4jModel.create(db_client=driver)
    await graphdb.ensure_schema()
    app.state.graphdb = graphdb

    yield

    await driver.close()


app = FastAPI(lifespan=lifespan)

app.include_router(base.base_router)
app.include_router(index.index_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        port=5000,
        reload=True,
        reload_excludes=["assets/*"],
    )