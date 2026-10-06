from fastapi import APIRouter, HTTPException,Request,Depends
from fastapi.responses import JSONResponse
from helper.config import get_settings
from models.enums.ResponsingEnums import ResponseStatus, ResponseMessage
from controllers.IndexingController import IndexingController
from models.db_schemas.Neo4jNodes import ProjectNode

from models.Neo4jModel import Neo4jModel
  
from models.enums.Neo4jEnums import ProjectSource   


index_router = APIRouter(
    prefix="/codepulse-ai",
    tags=['api_v1', 'index']
)


@index_router.post("/upload/github/")
async def upload_github(github_link: str, res: Request,app_settings: dict = Depends(get_settings) ):
    index_controller = IndexingController()

    neo4j_model = Neo4jModel.create(db_client=res.app.state.graphdb.driver)

    if not index_controller._is_remote_url(github_link):
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub URL"
        )

    try:
        index_controller._check_url_reachable(github_link)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    project_hash = index_controller.generate_project_hash(github_link)

    project_path, is_valid_existing = (
        index_controller.create_project_dir(project_hash)
    )

    if is_valid_existing:
        return JSONResponse(
            status_code=200,
            content={
                "status": ResponseStatus.SUCCESS.value,
                "project_hash": project_hash,
                "project_path": project_path
            }
        )

    try:
        index_controller.clone_url(
            github_link,
            project_path
        )
    except RuntimeError as e:
        raise HTTPException( status_code=400, detail=str(e))

    parsing_results = index_controller.extract_project(
        project_path
    )

    if not parsing_results:
        return JSONResponse(
            status_code=400,
            content={
                "status": ResponseStatus.ERROR.value,
                "message": ResponseMessage.PARSING_FAILD.value
            }
        )

    project_node = ProjectNode(
        name=index_controller.get_project_name_from_path(
            project_path
        ),
        path=project_path,
        project_hash=project_hash,
        project_source=ProjectSource.GITHUB,
        num_modules=len(parsing_results),
    )

    graph_data = index_controller.index_project(
        parsing_results=parsing_results,
        project_node=project_node,
    )

    nodes = graph_data["nodes"]
    relationships = graph_data["relationships"]

    await neo4j_model.create_project_node( nodes["project"])

    for module in nodes["modules"]:
        await neo4j_model.create_module_node(  module)

    for function in nodes["functions"]:
        await neo4j_model.create_function_node( function)

    for cls in nodes["classes"]:
        await neo4j_model.create_class_node( cls )

    for import_node in nodes["imports"]:
        await neo4j_model.create_import_node(import_node)

    for relationship in relationships["contains"]:
        await neo4j_model.create_contains_relationship( relationship)

    for relationship in relationships["defines"]:
        await neo4j_model.create_defines_relationship( relationship)

    for relationship in relationships["imports"]:
        await neo4j_model.create_imports_relationship( relationship)

    for relationship in relationships["calls"]:
        await neo4j_model.create_calls_relationship(
            relationship
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": ResponseStatus.SUCCESS.value,
            "project_hash": project_hash,
            "project_path": project_path,
            "message": "Project indexed successfully",
        }
    )
        

