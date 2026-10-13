from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from helper.config import get_settings
from models.enums.ResponsingEnums import ResponseStatus, ResponseMessage
from controllers.IndexingController import IndexingController
from models.Neo4jModel import Neo4jModel
from models.db_schemas.Neo4jNode import CodeNode
from models.db_schemas.Neo4jRelation import CodeLink
import logging


index_router = APIRouter(
    prefix="/codepulse-ai",
    tags=['api_v1', 'index']
)
logger=logging.getLogger('uvicorn')


@index_router.post("/upload/github/")
async def upload_github(github_link: str,res: Request
                        ,app_settings: dict = Depends(get_settings)):
    index_controller = IndexingController()
    neo4j_model = Neo4jModel(res.app.state.driver)
    

    if not index_controller._is_remote_url(github_link):
        logger.error("Invalid GitHub URL")
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")

    try:
        await run_in_threadpool(index_controller._check_url_reachable, github_link)
    except ValueError as e:
        logger.error("the url not reachable {e}")
        raise HTTPException(status_code=400, detail=str(e))

    project_hash = index_controller.generate_project_hash(github_link)
    project_path, is_valid_existing = index_controller.create_project_dir(project_hash)
    has_graph=await neo4j_model.project_has_graph(project_hash)

    if is_valid_existing and has_graph :
        logger.info(f"The project is existed at {project_path}")
        return JSONResponse(
            status_code=200,
            content={
                "status": ResponseStatus.SUCCESS.value,
                "project_hash": project_hash,
                "project_path": project_path,
            },
        )
    

    try:
        await run_in_threadpool(index_controller.clone_url, github_link, project_path)
        logger.info("the repo is cloned ")
    except RuntimeError as e:
        index_controller.cleanup_project_dir(project_path)
        logger.error(f"there is an error during cloned the repo {e}")
        raise HTTPException(status_code=400, detail=str(e))

    try:
        nodes,links =index_controller.analyze_project(
                                              project_path=project_path,
                                              project_hash=project_hash,
                                              no_cluster=app_settings.NUMBER_CLUSTERS,
                                              max_workers=app_settings.NUMBER_WORKERS,
                                              graphify_path=app_settings.GRAPHIFY_PATH)
        
        if not nodes or not links:
            logger.info(f"there is no nodes {nodes} or links {links}")
            index_controller.cleanup_project_dir(project_path)
            return JSONResponse(
                status_code=400,
                content={
                    "status": ResponseStatus.ERROR.value,
                    "message": ResponseMessage.PARSING_FAILD.value,
                },
            )


        nodes=[CodeNode(**n) for n in nodes ]
        links=[CodeLink(**l) for l in links ]

        await neo4j_model.batch_create_nodes(nodes)
        await neo4j_model.batch_create_relationships(links)

    except Exception as e:
        index_controller.cleanup_project_dir(project_path)
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")

    return JSONResponse(
        status_code=200,
        content={
            "status": ResponseStatus.SUCCESS.value,
            "project_hash": project_hash,
            "project_path": project_path,
            "message": "Project indexed successfully",
        },
    )

@index_router.delete("/delete/github/{project_hash}")
async def delete_project(project_hash:str,res:Request):

    # check if the project exist or not 
    index_controller = IndexingController()
    neo4j_model = Neo4jModel(res.app.state.driver)

    has_graph=await neo4j_model.project_has_graph(project_hash)
    project_path, is_valid_existing = index_controller.create_project_dir(project_hash)
    

    if has_graph and is_valid_existing:
        try:
            index_controller.cleanup_project_dir(project_path=project_path)
            await neo4j_model.delete_project(project_hash=project_hash)

            return JSONResponse(
                        status_code=200,
                        content={
                            "status": ResponseStatus.SUCCESS.value,
                            "result":ResponseMessage.DELETING_SUCCESS.value
                         
                        },
                    )
        except Exception as e :
            logger.error(f"There is an error while deleting {e}")   
            raise ValueError(f"There is an error while deleting the {project_hash}")

    return JSONResponse(
                        status_code=404,
                        content={
                            "status": ResponseStatus.ERROR.value,
                            "result":ResponseMessage.DELETING_FAIL.value
                         
                        }
                    )
            






