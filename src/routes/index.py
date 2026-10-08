from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from helper.config import get_settings
from models.enums.ResponsingEnums import ResponseStatus, ResponseMessage
from models.enums.Neo4jEnums import ProjectSource
from models.db_schemas.Neo4jNodes import ProjectNode
from controllers.IndexingController import IndexingController


index_router = APIRouter(
    prefix="/codepulse-ai",
    tags=['api_v1', 'index']
)


@index_router.post("/upload/github/")
async def upload_github(
    github_link: str,
    res: Request,
    app_settings: dict = Depends(get_settings),
):
    index_controller = IndexingController()
    neo4j_model = res.app.state.graphdb

    if not index_controller._is_remote_url(github_link):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")

    try:
        await run_in_threadpool(index_controller._check_url_reachable, github_link)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    project_hash = index_controller.generate_project_hash(github_link)
    project_path, is_valid_existing = index_controller.create_project_dir(project_hash)

    if is_valid_existing:
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
    except RuntimeError as e:
        index_controller.cleanup_project_dir(project_path)
        raise HTTPException(status_code=400, detail=str(e))

    try:
        parsing_results = await run_in_threadpool(
            index_controller.extract_project, project_path
        )

        if not parsing_results:
            index_controller.cleanup_project_dir(project_path)
            return JSONResponse(
                status_code=400,
                content={
                    "status": ResponseStatus.ERROR.value,
                    "message": ResponseMessage.PARSING_FAILD.value,
                },
            )

        project_node = ProjectNode(
            name=index_controller.get_project_name_from_path(github_link),
            path=project_path,
            project_hash=project_hash,
            project_source=ProjectSource.GITHUB,
            num_modules=len(parsing_results),
        )

        graph_data = index_controller.index_project(
            parsing_results=parsing_results,
            project_node=project_node,
        )

        await index_controller.persist_graph(neo4j_model, graph_data)

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
            "parsing_results":parsing_results
        },
    )