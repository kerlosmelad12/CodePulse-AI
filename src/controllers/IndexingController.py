import hashlib
import importlib
import logging
from pathlib import Path
from typing import List
from git import Repo
from tree_sitter import Language, Parser

from .BaseController import BaseController
from utils.graphhiy import find_graph_json, run_graphify, get_nodes_and_links
from utils.Chunking import (
    get_nodes_by_file, load_single_file, get_file_langeauge, find_node_at_line,
)
from models.enums.CodeEnums import CodeLanguage
from models.db_schemas.ChunkDataNode import CodeChunk
from models.db_schemas.Neo4jNode import CodeNode


logger = logging.getLogger(__name__)

IGNORE_TYPES = frozenset({"comment", "line_comment", "block_comment"})


class IndexingController(BaseController):

    def __init__(self):
        super().__init__()
        self.parsers = self._build_parsers()

    @staticmethod
    def _build_parsers() -> dict:
        parsers = {}
        for lang in CodeLanguage:
            try:
                module = importlib.import_module(lang.grammar_module)
                parsers[lang] = Parser(Language(module.language()))
            except ImportError:
                logger.info(f"Grammar not installed, skipping: {lang.name}")
            except Exception:
                logger.exception(f"Failed to load grammar: {lang.name}")
        return parsers

    def clone_url(self, identifier: str, project_dir: str) -> bool:
        try:
            Repo.clone_from(identifier, project_dir)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to clone repository: {e}")

    def analyze_project(self, project_path: str | Path, graphify_path: str | None = None,
                        out_dir: str | Path | None = None,
                        project_hash: str = "default",
                        no_cluster: bool = False,
                        max_workers: int | None = None) -> tuple[list[dict], list[dict]]:

        project_path = Path(project_path).resolve()
        if not project_path.is_dir():
            raise FileNotFoundError(f"Project not found: {project_path}")

        out_dir = project_path / ".graphify" if out_dir is None else Path(out_dir)

        graph_path = find_graph_json(out_dir)
        if graph_path is None:
            graph_path = run_graphify(
                project_path=project_path,
                graphify_path=graphify_path,
                out_dir=out_dir,
                no_cluster=no_cluster,
                max_workers=max_workers,
            )

        return get_nodes_and_links(graph_path, project_hash)

    def chuncking_code(self, code_nodes: List[dict], project_path: str, project_hash: str) -> List[CodeChunk]:
        chunks = []

        for source_file, file_nodes in get_nodes_by_file(code_nodes).items():
            try:
                code_content = load_single_file(project_path, source_file)
                if code_content is None:
                    logger.warning(f"Could not read file: {source_file}")
                    continue

                language = get_file_langeauge(source_file)
                parser = self.parsers.get(language)
                if parser is None:
                    logger.debug(f"Skipping unsupported file: {source_file}")
                    continue

                source = code_content.encode("utf-8")
                tree = parser.parse(source)         
                file_hash = hashlib.sha256(source).hexdigest()
                file_path = f"{project_hash}/{source_file}"

                seen = set()
                for item in file_nodes:
                    ts_node = find_node_at_line(
                        tree.root_node,
                        item["start_line"],
                        types=language.chunk_node_types,
                        ignore_types=IGNORE_TYPES,
                    )
                    if ts_node is None:      
                        continue

                    start_line = ts_node.start_point[0] + 1
                    end_line = ts_node.end_point[0] + 1
                    key = (start_line, end_line, ts_node.type)
                    if key in seen:
                        continue
                    seen.add(key)

                    raw_id = f"{file_path}:{start_line}:{end_line}:{ts_node.type}"
                    chunks.append(CodeChunk(
                        project_hash=project_hash,
                        name=item["name"],
                        chunk_type=ts_node.type,
                        language=language.value,
                        file_path=file_path,
                        node_id=hashlib.sha256(raw_id.encode()).hexdigest(),
                        file_hash=file_hash,
                        text=source[ts_node.start_byte:ts_node.end_byte].decode("utf-8", errors="replace"),
                        start_line=start_line,
                        end_line=end_line,
                    ))
            except Exception:
                logger.exception(f"Error while chunking {source_file}")

        return chunks

    def create_chunks_links(self,code_nodes:CodeNode,chunk_nodes:CodeChunk):
        for code_node in code_nodes:
            pass
