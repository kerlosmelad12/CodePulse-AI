from fastapi import FastAPI
from routes import base,index
from helper.config import get_settings
import uvicorn
from neo4j import GraphDatabase
app=FastAPI()


@app.on_event("startup")
async def startup_span():
    app_settings=get_settings()
    URI=app_settings.NEO4J_URI
    AUTH=(app_settings.NEO4J_USERNAME, app_settings.NEO4J_PASSWORD)


    driver = GraphDatabase.driver(URI, auth=AUTH)
    Neo4jdatabase=app_settings.DATABASE_NAME
    app.state.neo4j_database=Neo4jdatabase
    driver.verify_connectivity() 
    with driver.session(database=Neo4jdatabase) as session:
        #create the database if it doesn't exist
        session.execute_write(lambda tx: tx.run(f"CREATE DATABASE {Neo4jdatabase} IF NOT EXISTS"))
    app.state.graphdb = driver





@app.on_event("shutdown")
async def shutdown_span():
    driver = app.state.graphdb
    driver.close()




app.include_router(base.base_router)
app.include_router(index.index_router)

if __name__ == "__main__":
    uvicorn.run("main:app", port=5000, reload=True)