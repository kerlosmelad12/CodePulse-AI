import asyncio
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from helper.config import get_settings
from models.enums.ResponsingEnums import ResponseStatus, ResponseMessage
from controllers.IndexingController import IndexingController
from models.Neo4jModel import Neo4jModel
from models.db_schemas.Neo4jNode import CodeNode
from models.db_schemas.Neo4jRelation import CodeLink
import logging
from utils.indexing import generate_project_hash
from models.db_schemas.ChunkDataNode import CodeChunk

review_router = APIRouter(
    prefix="/codepulse-ai",
    tags=['api_v1', 'review']
)
logger = logging.getLogger('uvicorn')
