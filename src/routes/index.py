from fastapi import APIRouter, HTTPException,Request,Depends
from fastapi.responses import JSONResponse
from helper.config import get_settings
from models.enums.ResponsingEnums import ResponseStatus, ResponseMessage
from controllers.IndexingController import IndexingController
from models.db_schemas.Neo4jNodes import ( ProjectNode,ModuleNode, FunctionNode,
    ClassNode,
    PackageNode,
)        


index_router = APIRouter(
    prefix="/codepulse-ai",
    tags=['api_v1', 'index']
)


@index_router.post("/upload/github/")
async def upload_github(github_link: str,app_settings: dict = Depends(get_settings)):
    index_controller = IndexingController()

    if not index_controller._is_remote_url(github_link):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")

    try:
        index_controller._check_url_reachable(github_link)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    project_hash = index_controller.generate_project_hash(github_link)
    project_path, is_valid_existing = index_controller.create_project_dir(project_hash)

    if is_valid_existing:
        return JSONResponse(status_code=200, content={
            "status": ResponseStatus.SUCCESS.value,
            "project_hash": project_hash,
            "project_path": project_path
        })

    try:
        index_controller.clone_url(github_link, project_path)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    parsing_results=index_controller.extract_project(project_path)

    if not parsing_results:

        return JSONResponse(status_code=400, content={
            "status": ResponseStatus.ERROR.value,
            "message": ResponseMessage.PARSING_FAILD.value
        })

    
    

    
    return JSONResponse(status_code=200, content={
        "status": ResponseStatus.SUCCESS.value,
        "project_hash": project_hash,
        "project_path": project_path,
        "parsing_results": parsing_results,
        "message": ResponseMessage.PARSING_SUCCESS.value
    })