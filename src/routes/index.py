import logging

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from helper.config import get_settings
from models.enums.ResponsingEnums import ResponseStatus, ResponseMessage
from controllers.IndexingController import IndexingController
from models.Neo4jModel import Neo4jModel
from models.db_schemas.Neo4jNode import CodeNode
from models.db_schemas.Neo4jRelation import CodeLink
from utils.indexing import generate_project_hash

index_router = APIRouter(
    prefix="/codepulse-ai",
    tags=['api_v1', 'index']
)
logger = logging.getLogger('uvicorn')


@index_router.post("/upload/github/")
async def upload_github( github_link: str, res: Request, branch: str | None = None, app_settings: dict = Depends(get_settings),):
    index_controller = IndexingController()
    neo4j_model = Neo4jModel(res.app.state.driver)

    if not index_controller.check_url(url=github_link):
        return JSONResponse(
            status_code=404,
            content={
                "status": ResponseStatus.ERROR.value,
                "message": ResponseMessage.URL_FAILD.value,
            },
        )

    identifier = f"{github_link}@{branch}" if branch else github_link
    project_hash = generate_project_hash(project_identifier=identifier)

    project_path, is_valid_existing = index_controller.create_project_dir(project_hash)
    has_graph = await neo4j_model.project_has_graph(project_hash)

    if is_valid_existing and has_graph:
        meta = await neo4j_model.get_project_meta(project_hash) or {}
        logger.info(f"The project already exists at {project_path}")
        return JSONResponse(
            status_code=200,
            content={
                "status": ResponseStatus.SUCCESS.value,
                "project_hash": project_hash,
                "project_path": project_path,
                "branch": meta.get("indexed_branch"),
                "commit": meta.get("indexed_commit"),
                "message": "Project already indexed",
            },
        )

    try:
        clone_info = await run_in_threadpool(
            index_controller.clone_url,
            identifier=github_link,
            project_dir=project_path,
            branch=branch,
        )
        logger.info(f"Cloned {github_link} @ {clone_info['branch']} ({clone_info['commit'][:8]})")
    except RuntimeError as e:
        index_controller.cleanup_project_dir(project_path)
        logger.error(f"Error during repository cloning: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # --- analyze + chunk + write ---
    try:
        nodes, links = await run_in_threadpool(
            index_controller.analyze_project,
            project_path=project_path,
            project_hash=project_hash,
            no_cluster=app_settings.HAS_CLUSTERS,
            max_workers=app_settings.NUMBER_WORKERS,
            graphify_path=app_settings.GRAPHIFY_PATH,
        )

        if not nodes or not links:
            logger.info(f"No nodes ({len(nodes)}) or links ({len(links)}) found.")
            index_controller.cleanup_project_dir(project_path)
            return JSONResponse(
                status_code=400,
                content={
                    "status": ResponseStatus.ERROR.value,
                    "message": ResponseMessage.PARSING_FAILD.value,
                },
            )

        chunks, chunk_links = await run_in_threadpool(
            index_controller.chuncking_code, nodes, project_path, project_hash
        )

        code_nodes = [CodeNode(**n) for n in nodes]
        code_links = [CodeLink(**l) for l in links]

        await neo4j_model.batch_create_nodes(code_nodes)
        await neo4j_model.batch_create_relationships(code_links)
        await neo4j_model.batch_create_ChunkNode(chunks)
        await neo4j_model.batch_create_chunk_links(chunk_links)

        await neo4j_model.save_project_meta(
            project_hash=project_hash,
            repo_url=github_link,
            branch=clone_info["branch"],
            commit=clone_info["commit"],
        )

    except Exception as e:
        index_controller.cleanup_project_dir(project_path)
        try:
            await neo4j_model.delete_project(project_hash)
        except Exception:
            logger.exception("Cleanup after failed indexing also failed")
        logger.error(f"Indexing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")

    return JSONResponse(
        status_code=200,
        content={
            "status": ResponseStatus.SUCCESS.value,
            "project_hash": project_hash,
            "project_path": project_path,
            "branch": clone_info["branch"],
            "commit": clone_info["commit"],
            "message": "Project indexed successfully",
            "nodes_count": len(nodes),
            "links_count": len(links),
            "chunks_count": len(chunks),
            "chunk_links_count": len(chunk_links),
        },
    )


@index_router.delete("/delete/github/{project_hash}")
async def delete_project(project_hash: str, res: Request):

    index_controller = IndexingController()
    neo4j_model = Neo4jModel(res.app.state.driver)

    has_graph = await neo4j_model.project_has_graph(project_hash)
    project_path, is_valid_existing = index_controller.create_project_dir(project_hash)

    if has_graph and is_valid_existing:
        try:
            index_controller.cleanup_project_dir(project_path=project_path)
            await neo4j_model.delete_project(project_hash=project_hash)

            return JSONResponse(
                status_code=200,
                content={
                    "status": ResponseStatus.SUCCESS.value,
                    "result": ResponseMessage.DELETING_SUCCESS.value,
                },
            )
        except Exception as e:
            logger.error(f"There is an error while deleting: {e}")
            raise HTTPException(status_code=500, detail=f"Error while deleting the project {project_hash}")

    return JSONResponse(
        status_code=404,
        content={
            "status": ResponseStatus.ERROR.value,
            "result": ResponseMessage.DELETING_FAIL.value,
        },
    )