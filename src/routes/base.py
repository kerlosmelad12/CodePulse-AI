from fastapi import APIRouter,Depends,Request,HTTPException
from helper.config import get_settings 

base_router=APIRouter(
    prefix="/CodePulse-Ai",
  tags=['api_v1','base']
  
  )

@base_router.get("/")
async def welcome(app_settings=Depends(get_settings)):
    return{
        "app_name":app_settings.APP_NAME,
        "app_version":app_settings.APP_VERSION
    }


@base_router.get("/Health/Neo4j")
async def Neo4j_health(req: Request):
    driver = req.app.state.graphdb
    try:
        driver.verify_connectivity()
        return {"status": "healthy", "database": "neo4j"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "database": "neo4j", "error": str(e)}
        )
