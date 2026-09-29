from fastapi import FastAPI
from routes import base
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
    driver.verify_connectivity()  
    app.state.graphdb = driver




@app.on_event("shutdown")
async def shutdown_span():
    driver = app.state.graphdb
    driver.close()




app.include_router(base.base_router)

if __name__ == "__main__":
    uvicorn.run("main:app", port=5000, reload=True)